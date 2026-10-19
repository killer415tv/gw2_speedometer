"""Optional Qt HUD (``--qt-hud``): READ-ONLY adapter + local bridge to a Qt process.

Nothing in here takes part in the measurement.  ``speedometer.py`` keeps
computing speed, checkpoints, lap times, CSV logs, uploads and multiplayer
messages exactly as before; this module only *looks* at the module globals it
already maintains, after every tick of ``updateMeterTimer``, and publishes a
small JSON snapshot to the new HUD.

Design
------
* ``StateAdapter``   reads the globals (``velocity``, ``lap``, ``next_step``,
  ``lap_timer``, ``total_timer``, ``_time``, ``guildhall_name``...) and derives
  what the HUD shows: speed in the HUD units (99 = beetle boost), acceleration,
  lap/race time, checkpoint x/y, split times at every checkpoint crossing,
  delta vs the best lap of this session (per map) and the record of
  ``<map>_records.csv``.  Never writes a global, a file or a Tk variable, never
  calls the patched ``time`` of the tests (it uses the tick's ``_time``).
* ``UdpLink``        127.0.0.1 UDP socket on an ephemeral port, non-blocking:
  a datagram that cannot be sent right away is simply dropped (the next one
  carries the complete state again), so the Tk loop can never block on it.
* ``QtHudPublisher`` called after every tick: updates the adapter, sends at
  most ``rate_hz`` state messages per second (plus one immediately on every
  checkpoint crossing), the static map geometry every 2 s, and reads commands
  coming back from the HUD (map choice) without blocking.
* ``QtHudBridge``    starts ``hud_qt_live.py`` as a separate process
  (``sys.executable``, path relative to this file), hides the Tk HUD once the
  Qt HUD says hello, shows it again if the Qt process dies, and runs the map
  choice through the SAME Tk code path as the "Choose map to race" menus
  (``racer.changeCup`` + ``racer.saveGuildhall``) on the Tk thread.

Without ``--qt-hud`` this module is not even imported.
"""

import atexit
import contextlib
import functools
import json
import math
import os
import secrets
import socket
import subprocess
import sys
import time

PROTOCOL = 1
LOCALHOST = "127.0.0.1"
ENV_TOKEN = "GW2_QT_HUD_TOKEN"
MAX_DATAGRAM = 60000
LOCAL_CUP = "OWN MAPS FOLDER"
HERE = os.path.dirname(os.path.abspath(__file__))
CLIENT_SCRIPT = os.path.join(HERE, "hud_qt_live.py")
# Tk HUD rule (Meter/Meterv2): speeds >= 140 (velocity/100) are spikes and not shown
_SPIKE_RAW = 140
# Tk HUD rule: a 0 velocity is only shown after 50 ms without a non-zero one
# (MumbleLink positions change at ~25 Hz while the loop runs at ~64 Hz)
_ZERO_HOLD = 0.05


def requested(argv=None, environ=None):
    """``--qt-hud`` on the command line or ``GW2_QT_HUD=1``."""
    argv = sys.argv[1:] if argv is None else argv
    environ = os.environ if environ is None else environ
    if "--qt-hud" in argv:
        return True
    return environ.get("GW2_QT_HUD", "").strip().lower() in ("1", "true", "yes", "on")


def speed_units(velocity):
    """Speed as the Tk HUD big number shows it (99 = boost), unrounded."""
    return (velocity * 100 / 10000) * 99 / 72


def parse_laps(text):
    """Same parsing as ``checkpoint()``: ``int(guildhall_laps.get()[:1])``."""
    try:
        return max(1, int(str(text)[:1]))
    except (TypeError, ValueError):
        return 1


def parse_record_time(text):
    """``"MM:SS:fff"`` (as written to ``<map>_records.csv``) -> seconds."""
    try:
        m, s, ms = str(text).strip().split(":")
        return int(m) * 60 + int(s) + int(ms) / 1000.0
    except (TypeError, ValueError):
        return None


def read_best_record(path):
    """Best (lowest) time in a ``<map>_records.csv`` file, or None."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return None
    best = None
    for line in text.replace("\n", "\r").split("\r"):
        if not line.strip():
            continue
        t = parse_record_time(line.split(",", 1)[0])
        if t is not None and t > 0 and (best is None or t < best):
            best = t
    return best


def _tk_get(var, default=""):
    try:
        return var.get()
    except Exception:  # noqa: BLE001 - Tk var not created yet / destroyed
        return default


def _num(v, default=0.0):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    return f if math.isfinite(f) else default


def _r(v, nd=3):
    return None if v is None else round(float(v), nd)


class CheckpointLayout:
    """Static per-map data derived from ``checkpoints_list`` (read-only)."""

    def __init__(self, rows):
        self.rows = rows  # (STEP, STEPNAME, (X, Y, Z), RADIUS), see checkpoint_cache
        steps = sorted({int(r[0]) for r in rows if _num(r[0], -1) >= 1})
        names = {int(r[0]): str(r[1]) for r in rows}
        self.steps = steps
        self.index = {s: i for i, s in enumerate(steps)}
        self.labels = ["META" if names.get(s) == "end" else f"CP{s}" for s in steps]
        self.coords = {int(r[0]): tuple(_num(c) for c in r[2]) for r in rows}

    @property
    def total(self):
        return len(self.steps)

    @classmethod
    def from_frame(cls, frame):
        if frame is None or not hasattr(frame, "iterrows") or len(frame) == 0:
            return cls(())
        try:
            from checkpoint_cache import build_rows  # pure function, no shared cache

            return cls(build_rows(frame))
        except Exception:  # noqa: BLE001 - malformed CSV: HUD shows no checkpoints
            return cls(())

    def geometry(self):
        """(track polyline, checkpoint points) in the (x, z) plane, step order."""
        order = [s for s in sorted(self.coords) if s >= 0]
        pts = [(self.coords[s][0], self.coords[s][2]) for s in order]
        cps = [(self.coords[s][0], self.coords[s][2]) for s in self.steps]
        if len(pts) >= 3:
            xs = [p[0] for p in pts]
            zs = [p[1] for p in pts]
            if max(xs) - min(xs) > 1e-6 and max(zs) - min(zs) > 1e-6:
                return pts, cps
        return [], cps


class RaceTracker:
    """Detects checkpoint crossings from the globals ``checkpoint()`` updates.

    ``checkpoint()`` (unchanged) does, on a crossing of
      * start:      ``next_step = 1`` and ``lap_timer = _time`` (+ ``total_timer``
                    on lap 1)
      * "*" step k: ``next_step = k + 1``
      * end:        ``next_step = 0``; ``lap`` + 1, or ``lap = 1`` on the last lap
      * reset (-1): ``next_step = 0``, ``lap = 1``, ``lap_timer = total_timer = _time``
    so comparing those globals before/after each tick tells which gate was
    crossed and ``_time - lap_timer`` is the very split time the Tk HUD shows.
    """

    def __init__(self):
        self.prev = None
        self.layout = CheckpointLayout(())
        self.best_by_map = {}  # map -> (lap time, [split times])
        self.map_name = ""
        self.record = None  # best time in <map>_records.csv (last-lap time, see observe)
        self.reset_map("", CheckpointLayout(()), None)

    def reset_map(self, name, layout, record):
        self.map_name = name
        self.layout = layout
        self.record = record
        self.prev = None
        self.in_lap = False
        self.finished = False
        self.splits = [None] * layout.total
        self.diffs = [None] * layout.total
        self.frozen_lap_time = 0.0
        self.frozen_race_time = 0.0
        self.final_time = None
        self.race_best_lap = None
        self.race_best_delta = None
        self.last_lap_time = None
        self.events = 0
        self.last_cp_diff = None
        self.delta = None
        self.finished_lap = None
        self.pending = False

    @property
    def session_best(self):
        return self.best_by_map.get(self.map_name)

    def reference(self, laps_total):
        """(lap time, splits) to compare with: session best lap, else the record."""
        best = self.session_best
        if best is not None:
            return best
        if self.record is not None and laps_total == 1:
            return (self.record, [None] * (self.layout.total - 1) + [self.record])
        return None

    def _new_lap(self):
        self.splits = [None] * self.layout.total
        self.diffs = [None] * self.layout.total
        self.in_lap = True
        self.delta = None

    def _cross(self, step, t, laps_total):
        i = self.layout.index.get(step)
        if i is None:
            return None
        self.splits[i] = t
        ref = self.reference(laps_total)
        diff = None
        if ref is not None and i < len(ref[1]) and ref[1][i] is not None:
            diff = t - ref[1][i]
        self.diffs[i] = diff
        self.last_cp_diff = diff
        self.delta = diff
        self.events += 1
        self.pending = True
        return i

    def observe(self, lap, next_step, lap_timer, total_timer, now, laps_total):
        cur = (lap, next_step, lap_timer, total_timer)
        prev, self.prev = self.prev, cur
        if prev is None:
            self.in_lap = next_step >= 1
            return
        plap, pstep, plt, _ptt = prev
        if lap_timer != plt and next_step == 1:
            # start gate (lap 1: also total_timer = _time -> a new race)
            if lap == 1 and total_timer == lap_timer:
                self.finished = False
                self.final_time = None
                self.race_best_lap = None
                self.race_best_delta = None
                self.finished_lap = None
            self._new_lap()
            self.events += 1
            self.last_cp_diff = None
            self.pending = True
        elif lap_timer != plt and next_step == 0:
            # reset sphere / manual reset: the run is abandoned
            self.in_lap = False
            self.finished = False
            self.frozen_lap_time = 0.0
            self.frozen_race_time = 0.0
            self.splits = [None] * self.layout.total
            self.diffs = [None] * self.layout.total
            self.delta = None
            self.pending = True
        elif pstep >= 1 and next_step == pstep + 1:
            self._cross(pstep, now - lap_timer, laps_total)
        elif pstep >= 1 and next_step == 0 and lap_timer == plt:
            # end gate: lap finished
            t = now - lap_timer
            self._cross(pstep, t, laps_total)
            self.in_lap = False
            self.frozen_lap_time = t
            self.frozen_race_time = now - total_timer
            self.last_lap_time = t
            best = self.session_best
            if best is None or t < best[0]:
                self.best_by_map[self.map_name] = (t, list(self.splits))
            if self.race_best_lap is None or t < self.race_best_lap:
                self.race_best_lap = t
            if plap >= laps_total:
                self.finished = True
                self.finished_lap = plap
                self.final_time = now - total_timer
                # <map>_records.csv stores the TIME of the last log row, i.e. the
                # time of the LAST LAP: comparable with the race only on 1 lap
                if self.record is not None and laps_total == 1:
                    self.race_best_delta = self.final_time - self.record


class StateAdapter:
    """Builds the HUD snapshot from speedometer.py's globals (READ-ONLY)."""

    def __init__(self, app_dir=HERE):
        self.app_dir = app_dir
        self.tracker = RaceTracker()
        self._frame = None
        self._frame_len = -1
        self._map_key = None
        self.map_seq = 0
        self._records_path = None
        self._records_mtime = None
        self._records_checked = 0.0
        self.speed = 0.0
        self._last_nonzero = None
        self.accel = 0.0
        self._acc_speed = None
        self._acc_time = None

    # -- static map data --------------------------------------------------
    def _records_file(self, name):
        try:
            from pathutils import sanitize_map_name

            safe = sanitize_map_name(name)
        except Exception:  # noqa: BLE001
            safe = name
        return os.path.join(str(self.app_dir), safe + "_records.csv")

    def _refresh_record(self, now, force=False):
        if self._records_path is None:
            return
        if not force and now - self._records_checked < 2.0:
            return
        self._records_checked = now
        try:
            mtime = os.stat(self._records_path).st_mtime
        except OSError:
            mtime = None
        if force or mtime != self._records_mtime:
            self._records_mtime = mtime
            self.tracker.record = read_best_record(self._records_path) if mtime else None

    def _check_map(self, g, name):
        frame = g.get("checkpoints_list")
        try:
            flen = len(frame)
        except TypeError:
            flen = -1
        key = (name, id(frame), flen)
        if key == self._map_key and frame is self._frame:
            return False
        self._map_key = key
        self._frame = frame
        self._frame_len = flen
        layout = CheckpointLayout.from_frame(frame)
        named = name not in ("", "-", "SELECT MAP")
        self._records_path = self._records_file(name) if named else None
        self.tracker.reset_map(name, layout, None)
        self._refresh_record(0.0, force=True)
        self.map_seq += 1
        return True

    def map_payload(self, g=None):
        track, cps = self.tracker.layout.geometry()
        cup = _tk_get(g.get("cup_name")) if g is not None else ""
        return {
            "map_seq": self.map_seq,
            "map_name": self.tracker.map_name,
            "cup": cup,
            "track": [[_r(x, 2), _r(z, 2)] for x, z in track],
            "checkpoints_xy": [[_r(x, 2), _r(z, 2)] for x, z in cps],
            "labels": list(self.tracker.layout.labels),
        }

    # -- per tick -----------------------------------------------------------
    def _update_speed(self, velocity, now):
        raw = velocity * 100 / 10000
        if velocity > 0:
            self._last_nonzero = now
            if round(raw) < _SPIKE_RAW:
                self._set_speed(speed_units(velocity), now)
        elif self._last_nonzero is None or now > self._last_nonzero + _ZERO_HOLD:
            self._set_speed(0.0, now)

    def _set_speed(self, v, now):
        if self._acc_time is not None and now - self._acc_time >= 0.02:
            a = (v - self._acc_speed) / (now - self._acc_time)
            self.accel += (a - self.accel) * 0.35
            self._acc_speed, self._acc_time = v, now
        elif self._acc_time is None:
            self._acc_speed, self._acc_time = v, now
        self.speed = v

    def update(self, g):
        """Observe one tick. Returns the snapshot dict (JSON-serialisable)."""
        now = _num(g.get("_time"))
        name = str(_tk_get(g.get("guildhall_name"), ""))
        self._check_map(g, name)
        self._refresh_record(now)
        laps_total = parse_laps(_tk_get(g.get("guildhall_laps"), "1 lap"))
        lap = int(_num(g.get("lap"), 1))
        next_step = int(_num(g.get("next_step"), 0))
        lap_timer = _num(g.get("lap_timer"))
        total_timer = _num(g.get("total_timer"))
        tr = self.tracker
        tr.observe(lap, next_step, lap_timer, total_timer, now, laps_total)
        self._update_speed(_num(g.get("velocity")), now)
        return self.snapshot(g, now, lap, next_step, lap_timer, total_timer, laps_total, name)

    def snapshot(self, g, now, lap, next_step, lap_timer, total_timer, laps_total, name):
        tr = self.tracker
        lay = tr.layout
        if tr.in_lap and next_step >= 1:
            lap_time = max(0.0, now - lap_timer)
            race_time = max(0.0, now - total_timer)
            checkpoint = max(0, lay.index.get(next_step, next_step - 1))
        else:
            lap_time = tr.frozen_lap_time
            race_time = tr.frozen_race_time
            checkpoint = 0
        shown_lap = tr.finished_lap if tr.finished and tr.finished_lap else lap
        ref = tr.reference(laps_total)
        best = tr.session_best
        best_lap = best[0] if best else (tr.record if laps_total == 1 else None)

        pos = g.get("_3Dpos")
        ml = g.get("ml")
        x = y = z = 0.0
        heading = 0.0
        fx = fz = 0.0
        with contextlib.suppress(Exception):  # no MumbleLink data yet
            if pos is not None:
                x, y, z = _num(pos[0]), _num(pos[1]), _num(pos[2])
            front = ml.data.fAvatarFront
            fx, fz = _num(front[0]), _num(front[2])
            heading = math.atan2(fz, fx) if (fx or fz) else 0.0
        nc_label, nc_dist, nc_bear = "", 0.0, 0.0
        target_step = next_step if next_step in lay.coords else None
        if target_step is not None:
            tx, _ty, tz = lay.coords[target_step]
            dx, dz = tx - x, tz - z
            nc_dist = math.hypot(dx, dz)
            if nc_dist > 1e-6 and (fx or fz):
                rel = math.degrees(heading - math.atan2(dz, dx))
                nc_bear = (rel + 180.0) % 360.0 - 180.0
            if target_step == 0:
                nc_label = "SALIDA"
            else:
                i = lay.index.get(target_step)
                nc_label = lay.labels[i] if i is not None else f"CP{target_step}"

        splits = [
            [lay.labels[i], _r(tr.splits[i]), _r(tr.diffs[i])] for i in range(lay.total)
        ]
        return {
            "speed": _r(self.speed, 2),
            "accel": _r(self.accel, 2),
            "boost": self.speed >= 98.5,
            "altitude": _r(y, 1),
            "distance": _r(_num(g.get("total_distance")), 1),
            "map_name": name,
            "cup": str(_tk_get(g.get("cup_name"), "")),
            "map_seq": self.map_seq,
            "lap": int(shown_lap),
            "laps_total": laps_total,
            "lap_time": _r(lap_time),
            "race_time": _r(race_time),
            "best_lap": _r(best_lap),
            "record": _r(tr.record),
            "has_reference": ref is not None,
            "checkpoint": int(checkpoint),
            "checkpoints_total": lay.total,
            "racing": bool(tr.in_lap and next_step >= 1),
            "delta": _r(tr.delta),
            "last_cp_event": tr.events,
            "last_cp_diff": _r(tr.last_cp_diff),
            "splits": splits,
            "next_cp_label": nc_label,
            "next_cp_distance": _r(nc_dist, 1),
            "next_cp_bearing": _r(nc_bear, 1),
            "player_pos": [_r(x, 2), _r(z, 2)],
            "player_heading": _r(heading, 4),
            "ghost_pos": None,  # the ghost runs in ghost_online.py (another process)
            "finished": tr.finished,
            "final_time": _r(tr.final_time),
            "race_best_lap": _r(tr.race_best_lap),
            "race_best_delta": _r(tr.race_best_delta),
        }


def encode(msg_type, token, payload=None, seq=0):
    msg = {"v": PROTOCOL, "type": msg_type, "token": token, "seq": seq}
    if payload is not None:
        msg["data"] = payload
    return json.dumps(msg, separators=(",", ":"), allow_nan=False).encode("utf-8")


def decode(data, token):
    """Parsed message dict, or None if invalid / wrong token / wrong protocol."""
    try:
        msg = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None
    if not isinstance(msg, dict) or msg.get("v") != PROTOCOL:
        return None
    if not token or not secrets.compare_digest(str(msg.get("token", "")), token):
        return None
    return msg


def _disable_udp_connreset(sock):
    """Windows: an ICMP 'port unreachable' would make the next recvfrom() raise."""
    if sys.platform == "win32" and hasattr(socket, "SIO_UDP_CONNRESET"):
        try:
            sock.ioctl(socket.SIO_UDP_CONNRESET, False)
        except (OSError, ValueError):
            pass


class UdpLink:
    """Non-blocking UDP endpoint on 127.0.0.1 (ephemeral port)."""

    def __init__(self, token, sock=None):
        self.token = token
        if sock is None:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind((LOCALHOST, 0))
        sock.setblocking(False)
        _disable_udp_connreset(sock)
        self.sock = sock
        self.port = sock.getsockname()[1]
        self.peer = None
        self.seq = 0
        self.sent = 0
        self.dropped = 0

    def send(self, msg_type, payload=None):
        if self.peer is None:
            self.dropped += 1
            return False
        self.seq += 1
        try:
            data = encode(msg_type, self.token, payload, self.seq)
        except (TypeError, ValueError):
            self.dropped += 1
            return False
        if len(data) > MAX_DATAGRAM:
            self.dropped += 1
            return False
        try:
            self.sock.sendto(data, self.peer)
        except (BlockingIOError, InterruptedError, OSError):
            self.dropped += 1  # full buffer / HUD gone: drop, never wait
            return False
        self.sent += 1
        return True

    def poll(self, max_msgs=16):
        out = []
        for _ in range(max_msgs):
            try:
                data, addr = self.sock.recvfrom(65535)
            except (BlockingIOError, InterruptedError):
                break
            except ConnectionResetError:
                continue
            except OSError:
                break
            if addr[0] != LOCALHOST:
                continue
            msg = decode(data, self.token)
            if msg is None:
                continue
            if msg.get("type") == "hello":
                self.peer = (LOCALHOST, int(addr[1]))
            out.append(msg)
        return out

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


class QtHudPublisher:
    """Per-tick glue: adapter -> link (throttled), link -> command handler."""

    MAP_EVERY = 2.0

    def __init__(self, adapter, link, rate_hz=50.0, on_message=None, clock=time.monotonic):
        self.adapter = adapter
        self.link = link
        self.min_interval = 1.0 / max(1.0, float(rate_hz))
        self.on_message = on_message
        self.clock = clock
        self._last_state = -1e9
        self._last_map = -1e9
        self._last_map_seq = None
        self.last_snapshot = None

    def tick(self, g):
        snap = self.adapter.update(g)
        self.last_snapshot = snap
        now = self.clock()
        for msg in self.link.poll():
            if self.on_message is not None:
                self.on_message(msg)
        if self.link.peer is None:
            return snap
        map_due = snap["map_seq"] != self._last_map_seq or now - self._last_map >= self.MAP_EVERY
        if map_due and self.link.send("map", self.adapter.map_payload(g)):
            self._last_map_seq = snap["map_seq"]
            self._last_map = now
        pending = self.adapter.tracker.pending
        if pending or now - self._last_state >= self.min_interval:
            self.link.send("state", snap)
            self._last_state = now
            self.adapter.tracker.pending = False
        return snap


def apply_map_choice(g, cup, name):
    """Select ``cup`` + ``name`` exactly like the Tk "Choose map to race" menus.

    Cup menu  -> ``racer.changeCup(cup)`` (only if it is a different cup, as a
    menu click on the current cup would do nothing useful), then map menu ->
    ``racer.saveGuildhall(name)``: same checkpoint loading, cup.txt/guildhall.txt,
    ranking and ghost hotkey as a click.  Must run on the Tk thread.
    """
    racer = g.get("racer")
    if racer is None or not name:
        print("[qt-hud] map choice ignored: the race panel (show_checkpoints_window) is off")
        return False
    cup_var = g.get("cup_name")
    if cup and _tk_get(cup_var, None) != cup:
        racer.changeCup(cup)
    racer.saveGuildhall(name)
    return True


class QtHudBridge:
    """Owns the Qt HUD process and hooks the publisher into the Tk loop."""

    WATCH_EVERY = 1.0
    MAX_ERRORS = 50

    def __init__(self, g, meter, tk_windows=(), schedule=None, rate_hz=50.0,
                 client_args=(), popen=subprocess.Popen, link=None, clock=time.monotonic):
        self.g = g
        self.meter = meter
        self.tk_windows = [w for w in tk_windows if w is not None]
        self.schedule = schedule or (lambda fn: fn())
        self.token = secrets.token_hex(16)
        self.link = link or UdpLink(self.token)
        self.adapter = StateAdapter(g.get("APP_DIR") or HERE)
        self.publisher = QtHudPublisher(self.adapter, self.link, rate_hz, self._on_message, clock)
        self.client_args = list(client_args)
        self.popen = popen
        self.clock = clock
        self.proc = None
        self.active = False  # publishing to a live Qt HUD
        self.tk_hidden = False
        self.errors = 0
        self._last_watch = 0.0
        self.chosen = []

    # -- process ------------------------------------------------------------
    def command(self):
        return [sys.executable, CLIENT_SCRIPT, "--port", str(self.link.port),
                "--parent-pid", str(os.getpid())] + self.client_args

    def start(self):
        env = dict(os.environ)
        env[ENV_TOKEN] = self.token
        env.pop("GW2_QT_HUD", None)
        try:
            self.proc = self.popen(self.command(), cwd=HERE, env=env)
        except OSError as exc:
            print("[qt-hud] could not start the Qt HUD, keeping the classic HUD:", exc)
            self.proc = None
            return False
        self.active = True
        atexit.register(self.stop)
        print(f"[qt-hud] Qt HUD process started (pid {self.proc.pid}, udp 127.0.0.1:{self.link.port})")
        return True

    def stop(self):
        if self.proc is not None and self.proc.poll() is None:
            with contextlib.suppress(Exception):
                self.link.send("quit")
            with contextlib.suppress(OSError):
                self.proc.terminate()

    def install(self):
        """Run the publisher after every tick of the (unchanged) measurement loop.

        ``updateMeterTimer`` reschedules itself with ``self.root.after(10,
        self.updateMeterTimer)``; setting the attribute on the instance makes that
        lookup return the wrapper, so the class code is not modified at all.
        """
        original = self.meter.updateMeterTimer

        @functools.wraps(original)
        def updateMeterTimer():
            original()  # measurement, logs, network: exactly as before
            self.after_tick()

        self.meter.updateMeterTimer = updateMeterTimer
        return updateMeterTimer

    # -- per tick -----------------------------------------------------------
    def after_tick(self):
        if not self.active:
            return
        try:
            self.publisher.tick(self.g)
            self.errors = 0
        except Exception as exc:  # noqa: BLE001 - the HUD must never stop the loop
            self.errors += 1
            if self.errors == 1:
                print("[qt-hud] adapter error (ignored):", repr(exc))
            if self.errors >= self.MAX_ERRORS:
                print("[qt-hud] too many adapter errors: back to the classic HUD")
                self._fallback()
                return
        now = self.clock()
        if now - self._last_watch >= self.WATCH_EVERY:
            self._last_watch = now
            if self.proc is not None and self.proc.poll() is not None:
                print(f"[qt-hud] Qt HUD exited (code {self.proc.returncode}): showing the classic HUD")
                self._fallback()

    def _fallback(self):
        self.active = False
        self._show_tk()

    def _hide_tk(self):
        if self.tk_hidden:
            return
        for w in self.tk_windows:
            with contextlib.suppress(Exception):  # window already destroyed
                w.withdraw()
        self.tk_hidden = True

    def _show_tk(self):
        if not self.tk_hidden:
            return
        for w in self.tk_windows:
            with contextlib.suppress(Exception):  # window already destroyed
                w.deiconify()
        self.tk_hidden = False

    def _on_message(self, msg):
        kind = msg.get("type")
        data = msg.get("data") or {}
        if kind == "hello":
            self._hide_tk()
        elif kind == "bye":
            self._fallback()
        elif kind == "choose_map":
            cup, name = str(data.get("cup", "")), str(data.get("name", ""))
            self.chosen.append((cup, name))
            print(f"[qt-hud] map chosen in the Qt HUD: {name!r} ({cup})")
            # same Tk code path as the menus, as its own Tk event
            self.schedule(lambda: apply_map_choice(self.g, cup, name))


def start(g, meter, tk_windows=(), tk_root=None, client_args=()):
    """Entry point used by speedometer.py's ``__main__`` with ``--qt-hud``."""
    schedule = None
    if tk_root is not None:
        def schedule(fn):
            tk_root.after(0, fn)
    bridge = QtHudBridge(g, meter, tk_windows, schedule=schedule, client_args=client_args)
    if bridge.start():
        bridge.install()
    return bridge
