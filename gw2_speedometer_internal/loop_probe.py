"""Optional, OFF-by-default diagnostics of the measurement loop.

The speedometer samples MumbleLink from a Tk ``after(10)`` callback (see
docs/TELEMETRY.md section 3).  Whether a log is "clean" depends on that loop not
having gaps longer than the 40 ms period of the game's position updates, but
until now there was no way to *see* the loop's behaviour on a real machine.

Enable it with the environment variable ``GW2_SPEEDOMETER_PROBE=1`` (nothing
else changes: no config key, no UI).  For every call of ``updateMeterTimer`` it
measures, with ``time.perf_counter`` (it never touches ``time.time`` and never
changes any value used by the measurement):

* ``interval_ms``  - time since the previous call started (loop jitter);
* ``duration_ms``  - time the call itself took (cost per tick);
* ``missed_updates_est`` - ``max(0, ceil(interval / 40 ms) - 1)``: an upper
  bound of the 25 Hz position updates this gap could have hidden (a hidden
  update shows up as a doubled SPEED, filtered at >= 150, and a missing row).

Output goes to ``diagnostics/loop_probe_<epoch>.csv`` (+ ``.summary.txt`` on
exit) next to the application, NEVER to ``logs/`` (the competition CSVs) and
never into a CSV that is uploaded.  Rows are buffered in memory and written by
a background thread, so the probe adds no file I/O to the Tk loop.

With the probe disabled ``begin``/``end`` are two trivial function calls.
"""

import atexit
import math
import os
import pathlib
import threading
import time

ENV_ENABLE = "GW2_SPEEDOMETER_PROBE"
ENV_DIR = "GW2_SPEEDOMETER_PROBE_DIR"
POSITION_UPDATE_PERIOD = 0.040  # the game updates fAvatarPosition at 25 Hz
HEADER = "tick,t_s,interval_ms,duration_ms,missed_updates_est\n"
_TRUE = {"1", "true", "yes", "on"}


def default_dir():
    return pathlib.Path(__file__).resolve().parent / "diagnostics"


def _percentile(sorted_values, q):
    if not sorted_values:
        return 0.0
    idx = min(len(sorted_values) - 1, max(0, math.ceil(q * len(sorted_values)) - 1))
    return sorted_values[idx]


class LoopProbe:
    def __init__(
        self,
        out_dir=None,
        clock=time.perf_counter,
        flush_interval=2.0,
        start_thread=True,
        epoch=None,
    ):
        self._clock = clock
        self._lock = threading.Lock()
        self._pending = []
        self._last_begin = None
        self._tick = 0
        self._t_origin = None
        self._intervals = []
        self._durations = []
        self._missed = 0
        self._gaps = 0
        out_dir = pathlib.Path(out_dir) if out_dir else default_dir()
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = int(epoch if epoch is not None else time.time())
        self.path = out_dir / f"loop_probe_{stamp}.csv"
        self.summary_path = out_dir / f"loop_probe_{stamp}.summary.txt"
        with open(self.path, "w", newline="", encoding="utf-8") as fh:
            fh.write(HEADER)
        self._closed = False
        self._stop = threading.Event()
        self._thread = None
        if start_thread:
            self._thread = threading.Thread(
                target=self._writer_loop,
                args=(flush_interval,),
                name="gw2-loop-probe-writer",
                daemon=True,
            )
            self._thread.start()

    # -- hot path ---------------------------------------------------------
    def begin(self):
        now = self._clock()
        if self._t_origin is None:
            self._t_origin = now
        self._cur_interval = (
            (now - self._last_begin) if self._last_begin is not None else None
        )
        self._last_begin = now
        return now

    def end(self, t0):
        now = self._clock()
        duration = now - t0
        interval = self._cur_interval
        self._tick += 1
        missed = 0
        if interval is not None:
            self._intervals.append(interval)
            missed = max(0, math.ceil(interval / POSITION_UPDATE_PERIOD) - 1)
            if interval > POSITION_UPDATE_PERIOD:
                self._gaps += 1
            self._missed += missed
        self._durations.append(duration)
        row = "{},{:.6f},{},{:.3f},{}\n".format(
            self._tick,
            t0 - self._t_origin,
            "" if interval is None else f"{interval * 1000:.3f}",
            duration * 1000,
            missed,
        )
        with self._lock:
            self._pending.append(row)

    # -- background -------------------------------------------------------
    def _writer_loop(self, interval):
        while not self._stop.wait(interval):
            self.flush()

    def flush(self):
        with self._lock:
            rows, self._pending = self._pending, []
        if rows:
            with open(self.path, "a", newline="", encoding="utf-8") as fh:
                fh.write("".join(rows))

    def summary(self):
        iv = sorted(self._intervals)
        du = sorted(self._durations)
        median = _percentile(iv, 0.5)
        lost_ticks = sum(max(0, round(x / median) - 1) for x in iv) if median > 0 else 0
        p50, p95, p99 = (_percentile(iv, q) * 1000 for q in (0.5, 0.95, 0.99))
        iv_max = (iv[-1] if iv else 0) * 1000
        du_mean = (sum(du) / len(du) if du else 0) * 1000
        du_p95 = _percentile(du, 0.95) * 1000
        du_max = (du[-1] if du else 0) * 1000
        lines = [
            f"ticks: {self._tick}",
            f"interval_ms p50/p95/p99/max: {p50:.3f} / {p95:.3f} / {p99:.3f} / {iv_max:.3f}",
            f"duration_ms mean/p95/max: {du_mean:.3f} / {du_p95:.3f} / {du_max:.3f}",
            f"gaps_over_40ms: {self._gaps}",
            f"missed_updates_est (sum of ceil(interval/40ms)-1): {self._missed}",
            f"lost_ticks_est (vs median interval {median * 1000:.3f} ms): {lost_ticks}",
        ]
        return "\n".join(lines) + "\n"

    def close(self):
        if self._closed:
            return
        self._closed = True
        self._stop.set()
        self.flush()
        self.summary_path.write_text(self.summary(), encoding="utf-8")


_probe = None


def enabled():
    return _probe is not None


def enable(out_dir=None, **kwargs):
    """Turn the probe on (used by the env switch and by tests)."""
    global _probe
    if _probe is None:
        _probe = LoopProbe(out_dir=out_dir, **kwargs)
        atexit.register(_probe.close)
    return _probe


def disable():
    global _probe
    if _probe is not None:
        _probe.close()
        _probe = None


def begin():
    p = _probe
    return p.begin() if p is not None else 0.0


def end(t0):
    p = _probe
    if p is not None:
        p.end(t0)


if os.environ.get(ENV_ENABLE, "").strip().lower() in _TRUE:
    enable(os.environ.get(ENV_DIR) or None)
