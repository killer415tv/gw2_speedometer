"""Golden-test harness for the measurement / CSV-log / checkpoint logic.

``speedometer.py`` cannot be imported on Linux (it creates a Tk root and uses
``windll`` at import time), but its measurement code does not need the real
Tk/Windows to run.  This harness therefore:

* parses ``speedometer.py`` with ``ast`` (keeping the original line numbers, so
  coverage works) and compiles ONLY the classes ``Meterv2``, ``Meter``,
  ``Racer`` and ``ThreadWithReturnValue`` (without their Tk ``__init__``);
* executes them in a namespace that plays the role of the module globals
  (literal defaults are taken from the source itself, so they cannot drift);
* replaces the outside world with deterministic fakes: ``time`` (a scripted
  clock), ``datetime.now``, MumbleLink (real ``mumblelink.Link`` ctypes
  structures filled from a synthetic position stream), Tk variables, HUD,
  keyboard, ``requests`` and the multiplayer ``racer``;
* feeds a synthetic, fully deterministic MumbleLink sequence to the REAL
  ``updateMeterTimer`` code and records everything observable: CSV bytes (and
  their size after every tick, which proves per-row durability), lap results,
  uploads, multiplayer messages, key presses, HUD texts...

The golden files in ``tests/golden/`` were generated from the code BEFORE any
optimisation (see ``tests/golden/README.md``) and must never be regenerated to
make a later commit pass.
"""

import ast
import base64
import copy
import ctypes
import datetime as _real_datetime
import hashlib
import importlib
import io
import itertools
import json
import pathlib
import sys
import threading

import mumblelink
import numpy as np
import pandas as pd

INTERNAL = pathlib.Path(__file__).resolve().parent.parent / "gw2_speedometer_internal"
SOURCE = INTERNAL / "speedometer.py"

# Real modules that are safe to import for real inside the namespace (pure
# Python / numeric libs and the project's own non-GUI helper modules).  Any
# top-level ``import`` of one of them in speedometer.py is executed for real,
# so new helper modules added by optimisation commits are picked up without
# touching the harness.
SAFE_IMPORT_ROOTS = {
    "math",
    "ctypes",
    "json",
    "logging",
    "queue",
    "numpy",
    "pandas",
    "pathlib",
    "threading",
    "io",
    "os",
    "sys",
    "atexit",
    "urllib",
    "scipy",
    "mumblelink",
    "pathutils",
    "telemetry_log",
    "loop_probe",
    "background",
    "checkpoint_cache",
}
# Names provided (faked) by the harness: their real imports are skipped.
FAKED_IMPORT_ROOTS = {"time", "datetime", "requests"}

# per-tick state of the measurement globals (full float precision), digested
TRACE_KEYS = (
    "velocity",
    "_lastVel",
    "_lastTime",
    "pressedQ",
    "next_step",
    "lap",
    "total_distance",
    "map_angle",
    "total_timer",
    "lap_timer",
    "filename",
)

HEADER = "X,Y,Z,SPEED,ANGLE_CAM,ANGLE_BEETLE,TIME,ACCELERATION,MAP_ANGLE"


# --------------------------------------------------------------------- fakes
class Recorder:
    """Ordered, per-channel record of everything observable."""

    def __init__(self):
        self.channels = {}
        self.lock = threading.Lock()

    def add(self, channel, item):
        with self.lock:
            self.channels.setdefault(channel, []).append(item)


class Var:
    """Tk variable stand-in (get/set) that records every ``set``."""

    def __init__(self, rec, name, value="", channel="hud"):
        self._rec = rec
        self._name = name
        self._channel = channel
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value
        self._rec.add(self._channel, [self._name, value])


class FakeCanvas:
    def find_withtag(self, tag):
        return (1,)

    def itemconfig(self, *a, **k):
        pass

    def coords(self, *a, **k):
        pass


class FakeRoot:
    def __init__(self, rec):
        self._rec = rec

    def after(self, ms, fn=None, *args):
        # the harness drives the ticks itself
        self._rec.add("after", [ms, getattr(fn, "__name__", str(fn))])

    def attributes(self, *a, **k):
        pass

    def focus_set(self):
        pass


class FakeSelf:
    """Stands in for a Meter/Meterv2 instance (no Tk)."""

    def __init__(self, rec):
        self.root = FakeRoot(rec)
        self.canvas = FakeCanvas()
        self.lastNonZero = 0
        self.lastNonZero_accel = 0
        self.lastNonZero_slope = 0
        self.drifting = False
        self.drift_time = 0
        for n in (
            "steps_txt",
            "step1_txt",
            "vartime",
            "distance",
            "var",
            "var100",
            "accelvar",
            "slopevar",
            "anglevar",
            "altitudevar",
            "max_speed",
            "drift_time_tk",
            "airdrift_angle_tk",
        ):
            ch = "steps" if n in ("steps_txt", "step1_txt") else "hud_stream"
            setattr(self, n, Var(rec, n, "", ch))


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.calls = 0

    def time(self):
        self.calls += 1
        return self.now

    def perf_counter(self):
        return self.now

    monotonic = perf_counter


class FakeDatetimeNow(_real_datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 10, 18, 15, 30, 45)


class FakeDatetimeModule:
    datetime = FakeDatetimeNow
    timedelta = _real_datetime.timedelta
    timezone = _real_datetime.timezone
    date = _real_datetime.date


class FakeKeyboard:
    def __init__(self, rec):
        self._rec = rec

    def press(self, key):
        self._rec.add("keys", ["press", key])

    def release(self, key):
        self._rec.add("keys", ["release", key])


class FakeRequests:
    """Records uploads exactly as ``requests.post`` would receive them."""

    class RequestException(Exception):
        pass

    def __init__(self, rec):
        self._rec = rec

    def post(self, url, **kw):
        f = kw["files"]["file"]
        content = f.read()
        self._rec.add(
            "uploads",
            {
                "url": url,
                "data": dict(kw.get("data", {})),
                "headers": dict(kw.get("headers", {})),
                "timeout": list(kw["timeout"]) if "timeout" in kw else None,
                "file_name": pathlib.Path(f.name).name,
                "bytes_b64": base64.b64encode(content).decode("ascii"),
            },
        )

        class R:
            text = "UPLOAD-OK:" + pathlib.Path(f.name).name

        return R()


class FakeMessage:
    def __init__(self, rec, channel):
        self._rec = rec
        self._channel = channel

    def write(self, text):
        self._rec.add(self._channel, text)


class FakeRacer:
    """The multiplayer/race panel (``racer`` global)."""

    def __init__(self, rec, session_id=""):
        self._rec = rec
        self.root = FakeRoot(rec)
        self.session_id = Var(rec, "session_id", session_id, "racer_vars")
        self.username = Var(rec, "username", "", "username_sets")

    def saveCheckpoint(self, value):
        self._rec.add("save_checkpoint", value)

    def saveGuildhall(self, value, **kw):
        self._rec.add("save_guildhall", value)

    def sendMQTT(self, data):
        self._rec.add("mqtt", json.loads(json.dumps(data)))


class FakeWebsocket:
    def __init__(self, rec):
        self._rec = rec

    def send(self, text):
        self._rec.add("websocket", text)


class FakeMumble:
    """``ml``: real ctypes structures, refilled on every read()."""

    def __init__(self, name="Beetle Boy"):
        self.data = mumblelink.Link()
        self.context = mumblelink.Context()
        self.sample = None
        self.name = name
        self.reads = 0

    def read(self):
        s = self.sample
        self.reads += 1
        d = mumblelink.Link()
        d.uiVersion = 2
        d.uiTick = s["tick"]
        for i in range(3):
            d.fAvatarPosition[i] = s["pos"][i]
            d.fAvatarFront[i] = s["avatar"][i]
            d.fCameraFront[i] = s["cam"][i]
        d.identity = json.dumps({"name": self.name, "fov": 1}) if self.name else ""
        c = mumblelink.Context()
        c.mapId = s.get("map_id", 1)
        c.uiState = 16  # bit 4 set: game has focus
        self.data = d
        self.context = c


# ------------------------------------------------------- namespace building
def _load_tree():
    src = SOURCE.read_text(encoding="utf-8")
    return ast.parse(src, filename=str(SOURCE))


def _is_literal(node):
    try:
        ast.literal_eval(node)
        return True
    except (ValueError, SyntaxError, TypeError):
        return False


def _compile_nodes(nodes, ns):
    mod = ast.Module(body=nodes, type_ignores=[])
    ast.fix_missing_locations(mod)
    exec(compile(mod, str(SOURCE), "exec"), ns)  # noqa: S102 - test harness


def build_namespace(tree=None):
    """Namespace acting as speedometer.py's module globals (no Tk, no Windows)."""
    tree = tree or _load_tree()
    ns = {"__name__": "speedometer_golden", "__file__": str(SOURCE)}
    imports, literals, classes = [], [], {}
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                roots = {a.name.split(".")[0] for a in node.names}
            else:
                roots = {(node.module or "").split(".")[0]}
            if roots <= SAFE_IMPORT_ROOTS and not (roots & FAKED_IMPORT_ROOTS):
                imports.append(node)
        elif isinstance(node, ast.Assign) and _is_literal(node.value):
            literals.append(node)
        elif isinstance(node, ast.ClassDef) and node.name in (
            "Meterv2",
            "Meter",
            "Racer",
            "ThreadWithReturnValue",
        ):
            classes[node.name] = node
    for node in imports:
        try:
            _compile_nodes([copy.deepcopy(node)], ns)
        except ImportError:  # optional libs not needed by the measured code
            pass
    ns.update(
        {
            "ctypes": ctypes,
            "np": np,
            "pd": pd,
            "math": __import__("math"),
            "json": json,
            "APP_DIR": None,  # set per run
        }
    )
    from scipy.spatial import distance

    ns["distance"] = distance
    ns["Thread"] = threading.Thread
    ns["logging"] = importlib.import_module("logging")
    _compile_nodes([copy.deepcopy(n) for n in literals], ns)
    for name in ("ThreadWithReturnValue", "Meterv2", "Meter", "Racer"):
        node = copy.deepcopy(classes[name])
        node.body = [
            n
            for n in node.body
            if not (isinstance(n, ast.FunctionDef) and n.name == "__init__")
        ]
        _compile_nodes([node], ns)
    return ns


# ------------------------------------------------------ synthetic input data
LCG_A, LCG_C, LCG_M = 1103515245, 12345, 2**31


def lcg(seed):
    state = seed
    while True:
        state = (state * LCG_A + LCG_C) % LCG_M
        yield state >> 8


BASE_EPOCH = 1760790123.0  # integer-valued, so fixed-point clocks stay exact

# Circuit (metres): S -> C1 -> C2 -> C3 -> E -> S ...
S = (0.0, 10.0, 0.0)
C1 = (150.0, 30.0, 20.0)
C2 = (150.0, 50.0, 220.0)
C3 = (-50.0, 70.0, 300.0)
E = (-50.0, 25.0, 60.0)
A = (-100.0, 10.0, -20.0)  # run-up before the start sphere


def _fmt(v):
    return repr(float(ctypes.c_float(v).value))


def map_csv(rows, with_angle=False):
    """Checkpoint CSV text like the checkpoint creators write it ('\\r' lines)."""
    cols = "STEP,STEPNAME,X,Y,Z,RADIUS" + (",ANGLE" if with_angle else "")
    lines = [cols]
    for step, name, pos, radius in rows:
        line = f"{step},{name},{_fmt(pos[0])},{_fmt(pos[1])},{_fmt(pos[2])},{radius}"
        if with_angle:
            line += ",0.0"
        lines.append(line)
    return "\r".join(lines) + "\r"


def load_map(text):
    """Same pandas calls as Racer.saveGuildhall."""
    checkpoints = pd.DataFrame()
    file_df = pd.read_csv(io.StringIO(text))
    return pd.concat([checkpoints, file_df], ignore_index=True)


MAP_STANDARD = map_csv(
    [
        (0, "start", S, 0),  # RADIUS 0 -> default 15 m
        (1, "*", C1, 20),
        (2, "*", C2, 0),
        (3, "*", C3, 12),
        (4, "end", E, 15),
    ]
)
MAP_WITH_RESET = map_csv(
    [
        (0, "start", S, 0),
        (1, "*", C1, 20),
        (2, "*", C2, 0),
        (3, "*", C3, 12),
        (4, "end", E, 15),
        (-1, "reset", A, 0),  # RADIUS 0 -> default 5 m
    ],
    with_angle=True,
)
# rows deliberately NOT sorted by STEP and without a RADIUS column
MAP_UNSORTED_NO_RADIUS = (
    "\r".join(
        ["STEP,STEPNAME,X,Y,Z"]
        + [
            f"{st},{nm},{_fmt(p[0])},{_fmt(p[1])},{_fmt(p[2])}"
            for st, nm, p in [
                (4, "end", E),
                (0, "start", S),
                (2, "*", C2),
                (1, "*", C1),
                (3, "*", C3),
            ]
        ]
    )
    + "\r"
)

# metres advanced per 40 ms game-position update, by game-step ranges
# (0.0 = standing still; 1.8288 m = 1800 in/s = SPEED 99; >=2.7 m -> SPEED>=150)
DEFAULT_STEP = 1.8288
SPEED_PROFILE = [
    (0, 20, 1.8288),
    (20, 40, 1.2),
    (40, 60, 0.0),  # standing still
    (60, 120, 1.8288),
    (120, 135, 2.9),  # SPEED >= 150: rows filtered out of the CSV
    (135, 200, 1.8288),
    (200, 230, 0.3),  # crawling
    (230, 100000, 1.8288),
]


def _dist_per_step(k, profile):
    for lo, hi, v in profile:
        if lo <= k < hi:
            return v
    return DEFAULT_STEP


class Path:
    """Polyline walked with a per-step speed profile (only + - * / sqrt)."""

    def __init__(self, waypoints, profile):
        self.pts = waypoints
        self.seg = []
        total = 0.0
        for p, q in itertools.pairwise(waypoints):
            d = ((q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2 + (q[2] - p[2]) ** 2) ** 0.5
            self.seg.append((total, d))
            total += d
        self.total = total
        self.profile = profile
        self._s = [0.0]

    def s_at(self, k):
        while len(self._s) <= k:
            self._s.append(self._s[-1] + _dist_per_step(len(self._s) - 1, self.profile))
        return min(self._s[k], self.total)

    def at(self, k):
        s = self.s_at(k)
        for i, (start, d) in enumerate(self.seg):
            if s <= start + d or i == len(self.seg) - 1:
                t = (s - start) / d if d else 0.0
                p, q = self.pts[i], self.pts[i + 1]
                pos = tuple(p[j] + (q[j] - p[j]) * t for j in range(3))
                dx, dz = q[0] - p[0], q[2] - p[2]
                n = (dx * dx + dz * dz) ** 0.5 or 1.0
                return pos, (dx / n, 0.0, dz / n)
        raise AssertionError


def make_ticks(
    waypoints,
    profile=SPEED_PROFILE,
    seed=1,
    clock="q64",
    jitter=True,
    stalls=((300, 6), (700, 4)),
    max_ticks=None,
    teleports=None,
):
    """Deterministic MumbleLink samples.

    Loop period ~15.625 ms (+ jitter), with ``stalls`` = (tick index, extra
    ticks of delay) emulating hiccups of the Tk loop.  The game position only
    changes every 40 ms (25 Hz), as in the real game.  ``clock``: ``"q64"`` =
    ``time.time()`` quantised to 1/64 s (Python 3.12 on Windows), ``"fine"`` =
    microsecond resolution.  ``teleports`` = {tick: position} overrides.
    """
    rnd = lcg(seed)
    path = Path(waypoints, profile)
    ticks = []
    us = 0
    i = 0
    stall = dict(stalls)
    end_k = None
    while True:
        k = (us + 17000) // 40000
        pos, front = path.at(k)
        if path.s_at(k) >= path.total and end_k is None:
            end_k = k
        if end_k is not None and k > end_k + 60:
            break
        if max_ticks and i >= max_ticks:
            break
        if teleports and i in teleports:
            pos = teleports[i]
        cam_off = ((k // 7) % 5 - 2) * 0.05
        cam = (front[0] - front[2] * cam_off, 0.0, front[2] + front[0] * cam_off)
        if clock == "q64":
            t = BASE_EPOCH + (us // 15625) * 0.015625
        else:
            t = BASE_EPOCH + us / 1e6
        ticks.append(
            {
                "i": i,
                "t": t,
                "tick": i,
                "pos": pos,
                "avatar": front,
                "cam": cam,
                "map_id": 1,
            }
        )
        step = 15625
        if jitter:
            step += (next(rnd) % 7000) - 3000
        if i in stall:
            step += stall[i] * 15625
        us += step
        i += 1
    return ticks


def circuit(laps):
    """Waypoints: run-up, then ``laps`` times S->C1->C2->C3->E->S, finishing in E."""
    pts = [A, S]
    for lap in range(laps):
        pts += [C1, C2, C3, E]
        if lap < laps - 1:
            pts.append(S)
    return pts


# ------------------------------------------------------------- scenario run
class Scenario:
    def __init__(
        self,
        name,
        meter="Meterv2",
        map_text=MAP_STANDARD,
        laps=1,
        settings=None,
        session_id="",
        upload=0,
        ticks=None,
        actions=None,
        websocket=False,
        map_name="Test Race",
        laps_label=None,
        identity="Beetle Boy",
        racer_factory=None,
        namespace_hook=None,
        meter_hook=None,
    ):
        self.name = name
        self.meter = meter
        self.map_text = map_text
        self.laps = laps
        self.settings = settings or {}
        self.session_id = session_id
        self.upload = upload
        self.ticks = ticks
        self.actions = actions or {}
        self.websocket = websocket
        self.map_name = map_name
        self.laps_label = laps_label or f"{laps} lap{'' if laps == 1 else 's'}"
        self.identity = identity
        # optional: build the racer / tweak the namespace (non-golden tests)
        self.racer_factory = racer_factory
        self.namespace_hook = namespace_hook
        # optional: wrap the meter after it is built (e.g. the --qt-hud adapter)
        self.meter_hook = meter_hook


def _settle(ns):
    """Wait for background work started by the code under test (uploads...).

    The original code starts plain ``Thread`` objects; optimised versions use
    the project's ``background`` workers, which expose ``drain_all()`` (wait
    until idle and run the pending UI callbacks on this, the "Tk", thread).
    """
    for t in list(threading.enumerate()):
        if (
            t is not threading.current_thread()
            and not t.name.startswith(("gw2-", "pytest"))
            and t.name != "MainThread"
        ):
            threading.Thread.join(t, 10)
    bg = sys.modules.get("background")
    if bg is not None and hasattr(bg, "drain_all"):
        bg.drain_all()


def _plain(value):
    """Deterministic text of a global (ctypes arrays would print their address)."""
    if isinstance(value, ctypes.Array):
        return repr(list(value))
    return repr(value)


def _digest(items):
    blob = json.dumps(items, sort_keys=True, separators=(",", ":"), default=repr)
    return hashlib.sha256(blob.encode()).hexdigest()


def run_scenario(sc, workdir):
    """Run ``sc`` against the current speedometer.py. Returns (result, files)."""
    workdir = pathlib.Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    rec = Recorder()
    clock = FakeClock()
    ns = build_namespace()
    ns["APP_DIR"] = workdir
    ns["time"] = clock
    ns["datetime"] = FakeDatetimeModule
    ns["requests"] = FakeRequests(rec)
    ns["keyboard_"] = FakeKeyboard(rec)
    ns["ml"] = ml = FakeMumble(sc.identity)
    ns["racer"] = (
        sc.racer_factory(ns, rec, workdir)
        if sc.racer_factory
        else FakeRacer(rec, sc.session_id)
    )
    ns["tmhud"] = FakeMessage(rec, "tmhud")
    ns["message"] = FakeMessage(rec, "message")
    ns["upload"] = Var(rec, "upload", sc.upload, "upload_var")
    ns["guildhall_name"] = Var(rec, "guildhall_name", sc.map_name, "guildhall_var")
    ns["guildhall_laps"] = Var(rec, "guildhall_laps", sc.laps_label, "laps_var")
    ns["cup_name"] = Var(rec, "cup_name", "TESTCUP", "cup_var")
    ns["WebSocketConnectionClosedException"] = type("WSClosed", (Exception,), {})
    ns["websocket_client"] = FakeWebsocket(rec) if sc.websocket else None
    ns["checkpoints_list"] = load_map(sc.map_text) if sc.map_text else []
    # per-scenario settings (config.txt would normally set these)
    ns["show_checkpoints_window"] = 1
    for k, v in sc.settings.items():
        ns[k] = v
    if ns["speed_in_3D"] == 1:
        ns["_pos"] = [0, 0, 0]
        ns["_lastPos"] = [0, 0, 0]
    else:
        ns["_pos"] = [0, 0]
        ns["_lastPos"] = [0, 0]
    ns["pressedQ"] = 0

    if sc.namespace_hook:
        sc.namespace_hook(ns, rec, workdir)
    meter = ns[sc.meter].__new__(ns[sc.meter])
    FakeSelf.__init__(meter, rec)
    # the methods come from the real class; only the Tk attributes are fake
    ns["meter"] = meter
    if sc.meter_hook:
        sc.meter_hook(ns, rec, workdir, meter)

    ticks = sc.ticks
    progress = []
    trace = []
    exceptions = []
    last_sizes = None
    with np.errstate(divide="ignore", invalid="ignore"):
        for tk in ticks:
            clock.now = tk["t"]
            ml.sample = tk
            action = sc.actions.get(tk["i"])
            if action:
                action(ns, rec)
            try:
                meter.updateMeterTimer()
            except Exception as exc:  # noqa: BLE001 - the real Tk loop would die here
                exceptions.append(
                    [
                        tk["i"],
                        type(exc).__name__,
                        str(exc).replace(str(workdir), "<APP>"),
                    ]
                )
            _settle(ns)
            trace.append([_plain(ns.get(k)) for k in TRACE_KEYS])
            logs = workdir / "logs"
            sizes = (
                sorted((p.name, p.stat().st_size) for p in logs.iterdir())
                if logs.exists()
                else []
            )
            if sizes != last_sizes:
                progress.append([tk["i"], sizes])
                last_sizes = sizes

    files = {}
    for p in sorted(workdir.rglob("*")):
        if p.is_file():
            files[str(p.relative_to(workdir))] = p.read_bytes()

    # all files were read exactly as they were on disk while the writer was
    # still alive; only now release any handle the code under test keeps open
    tl = sys.modules.get("telemetry_log")
    if tl is not None:
        tl.csv_log.close()

    rows_summary = {}
    for rel, data in files.items():
        if rel.startswith("logs/") and rel.endswith(".csv"):
            text = data.decode("utf-8")
            lines = text.split("\r")
            last = lines[-1].split(",") if len(lines) > 1 else None
            rows_summary[rel] = {
                "rows": len(lines) - 1,
                "header": lines[0],
                "last_TIME_col": last[6] if last else None,
                "ends_with_cr_or_lf": text[-1:] in ("\r", "\n"),
                "has_lf": "\n" in text,
            }

    ch = rec.channels

    def full_or_digest(name):
        items = ch.get(name, [])
        return {
            "count": len(items),
            "sha256": _digest(items),
            "head": items[:3],
            "tail": items[-3:],
        }

    low_volume = [
        "steps",
        "message",
        "uploads",
        "save_checkpoint",
        "save_guildhall",
        "keys",
    ]
    mqtt = ch.get("mqtt", [])
    result = {
        "scenario": sc.name,
        "meter": sc.meter,
        "n_ticks": len(ticks),
        "time_calls": clock.calls,
        "ml_reads": ml.reads,
        "exceptions": exceptions,
        "files": {
            rel: {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            for rel, data in files.items()
        },
        "csv_summary": rows_summary,
        "disk_progress": progress,
        "final_globals": {
            k: _plain(ns[k])
            for k in (
                "lap",
                "next_step",
                "pressedQ",
                "total_distance",
                "filename",
                "total_timer",
                "lap_timer",
                "map_angle",
                "_lastVel",
                "_lastTime",
                "velocity",
                "map_position_last_time_send",
                "last_checkpoint_position",
            )
            if k in ns
        },
        "channels_full": {name: ch.get(name, []) for name in low_volume},
        "mqtt_non_position": [m for m in mqtt if m.get("option") != "position"],
        "mqtt_position": full_or_digest_list(mqtt, "position"),
        "websocket": full_or_digest_ws(ch.get("websocket", [])),
        "state_trace": {
            "keys": list(TRACE_KEYS),
            "count": len(trace),
            "sha256": _digest(trace),
            "sample": trace[100:103],
        },
        "digests": {
            n: full_or_digest(n)
            for n in ("hud_stream", "tmhud", "username_sets", "racer_vars")
        },
    }
    return result, files


def full_or_digest_list(mqtt, option):
    items = [m for m in mqtt if m.get("option") == option]
    return {
        "count": len(items),
        "sha256": _digest(items),
        "head": items[:2],
        "tail": items[-2:],
    }


def full_or_digest_ws(items):
    return {
        "count": len(items),
        "sha256": _digest(items),
        "head": items[:1],
        "tail": items[-1:],
    }


# ----------------------------------------------------------------- golden IO
GOLDEN_DIR = pathlib.Path(__file__).resolve().parent / "golden"


def write_golden(sc_name, result, files):
    d = GOLDEN_DIR / sc_name
    if d.exists():
        for p in sorted(d.rglob("*"), reverse=True):
            p.unlink() if p.is_file() else p.rmdir()
    (d / "files").mkdir(parents=True)
    (d / "result.json").write_text(
        json.dumps(result, indent=1, sort_keys=True, default=repr) + "\n",
        encoding="utf-8",
    )
    for rel, data in files.items():
        out = d / "files" / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)


def read_golden(sc_name):
    d = GOLDEN_DIR / sc_name
    result = json.loads((d / "result.json").read_text(encoding="utf-8"))
    files = {}
    for p in sorted((d / "files").rglob("*")):
        if p.is_file():
            files[str(p.relative_to(d / "files"))] = p.read_bytes()
    return result, files


def normalise(result):
    """JSON round-trip so that tuples/lists compare equal."""
    return json.loads(json.dumps(result, sort_keys=True, default=repr))
