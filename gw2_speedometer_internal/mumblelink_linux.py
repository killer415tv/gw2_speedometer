"""MumbleLink backends for non-Windows systems and for offline demos.

* ``open_shm_memfile``  reads the real MumbleLink block from /dev/shm (Wine/Proton
  bridge that mirrors GW2's "MumbleLink" mapping into /dev/shm/MumbleLink.<uid>).
* ``SimulatedMemfile``  generates a synthetic car driving around a circuit with
  checkpoints, written in the exact MumbleLink binary layout (so the unmodified
  parsing code in mumblelink.py is exercised).

Utility (run from this folder)::

    python mumblelink_linux.py --write-circuit   # writes maps/SIM_CIRCUIT.csv
    python mumblelink_linux.py --dump            # prints a few simulated samples
"""

import json
import math
import mmap
import os
import struct
import sys
import time

# ---------------------------------------------------------------- real shm ----


def open_shm_memfile(path, length):
    """mmap ``path`` (read/write), creating/growing it to ``length`` if needed."""
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        if os.fstat(fd).st_size < length:
            os.ftruncate(fd, length)
        return mmap.mmap(fd, length)
    finally:
        os.close(fd)  # the mapping keeps its own reference


# --------------------------------------------------------------- simulator ----

# Circuit: ellipse (metres, GW2 axes: x east, y up, z north).
CENTER = (0.0, 120.0, 0.0)
SEMI_A = 900.0
SEMI_B = 500.0
OMEGA = 0.19  # rad/s -> lap ~33 s, speed between ~95 and ~171 m/s
CHECKPOINTS = 6  # steps 1..6 between start (0) and end (7)
CHECKPOINT_RADIUS = 40
MAP_ID = 24  # Gendarran Fields
CHARACTER = "Sim Racer"


def _pos(theta):
    return (
        CENTER[0] + SEMI_A * math.cos(theta),
        CENTER[1] + 25.0 * math.sin(2.0 * theta),
        CENTER[2] + SEMI_B * math.sin(theta),
    )


def circuit_rows():
    """Checkpoint rows (STEP, STEPNAME, X, Y, Z, RADIUS) for maps/SIM_CIRCUIT.csv.

    start at theta=0, intermediate '*' gates, 'end' just before the start gate.
    """
    rows = [(0, "start") + tuple(round(v, 1) for v in _pos(0.0)) + (CHECKPOINT_RADIUS,)]
    for i in range(1, CHECKPOINTS + 1):
        th = 2 * math.pi * i / (CHECKPOINTS + 1)
        rows.append((i, "*") + tuple(round(v, 1) for v in _pos(th)) + (CHECKPOINT_RADIUS,))
    th_end = 2 * math.pi - 0.12
    rows.append((CHECKPOINTS + 1, "end") + tuple(round(v, 1) for v in _pos(th_end)) + (CHECKPOINT_RADIUS,))
    return rows


def write_circuit_csv(path):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write("STEP,STEPNAME,X,Y,Z,RADIUS\n")
        for r in circuit_rows():
            fh.write(",".join(str(v) for v in r) + "\n")


def _wide(text, units=256):
    raw = text.encode("utf-16-le")[: (units - 1) * 2]
    return raw.ljust(units * 2, b"\x00")


class SimulatedMemfile:
    """Minimal mmap-like object: ``seek``/``read``/``close``/``write``."""

    def __init__(self, length):
        self.length = length
        self._buf = b"\x00" * length
        self._off = 0
        self._closed = False

    # -- mmap-like API ----------------------------------------------------
    def seek(self, pos, whence=0):
        if self._closed:
            raise ValueError("mmap closed or invalid")
        if pos == 0 and whence == 0:
            self._buf = self._snapshot()  # fresh sample on every read cycle
        self._off = pos if whence == 0 else self._off + pos

    def read(self, n=-1):
        if self._closed:
            raise ValueError("mmap closed or invalid")
        end = self.length if n is None or n < 0 else self._off + n
        data = self._buf[self._off:end]
        self._off = min(end, self.length)
        return data

    def write(self, data):  # accepted and ignored (nobody writes in simulation)
        return len(data)

    def close(self):
        self._closed = True

    # -- data -------------------------------------------------------------
    def _snapshot(self):
        # Absolute clock: every process (HUD, maps, ghost...) sees the same car position.
        t = time.time()
        theta = OMEGA * t
        x, y, z = _pos(theta)
        # velocity from analytic derivative -> unit tangent (front vector)
        dx = -SEMI_A * math.sin(theta)
        dz = SEMI_B * math.cos(theta)
        dy = 50.0 * math.cos(2.0 * theta)
        norm = math.sqrt(dx * dx + dz * dz) or 1.0
        fx, fz = dx / norm, dz / norm
        # Camera sways around the car heading -> non-zero "angle bubbles"
        sway = 0.35 * math.sin(t * 0.9)
        cfx = fx * math.cos(sway) - fz * math.sin(sway)
        cfz = fx * math.sin(sway) + fz * math.cos(sway)
        cam = (x - cfx * 9.0, y + 3.5, z - cfz * 9.0)
        tick = int(t * 60) & 0x7FFFFFFF

        link = struct.pack(
            "<II3f3f3f512s3f3f3f512sI",
            2, tick,
            x, y, z,
            fx, dy / norm * 0.05, fz,
            0.0, 1.0, 0.0,
            _wide("Guild Wars 2"),
            *cam,
            cfx, -0.12, cfz,
            0.0, 1.0, 0.0,
            _wide(json.dumps({
                "name": CHARACTER, "profession": 2, "spec": 0, "race": 1,
                "map_id": MAP_ID, "world_id": 0x1001, "team_color_id": 0,
                "commander": False, "fov": 0.873, "uisz": 1,
            })),
            256,
        )
        ctx = struct.pack(
            "<28s6IHH6f",
            b"\x00" * 28, MAP_ID, 0, 0x1001, 0, 123456, 8,  # uiState bit 3: game has focus
            1000, 500,
            0.0,  # compassRotation
            x * 39.37, z * 39.37, 0.0, 0.0, 1.0,  # playerX/Y, mapCenterX/Y, mapScale
        )
        buf = link + ctx
        return buf.ljust(self.length, b"\x00")


def _main(argv):
    here = os.path.dirname(os.path.abspath(__file__))
    if "--write-circuit" in argv:
        out = os.path.join(here, "maps", "SIM_CIRCUIT.csv")
        write_circuit_csv(out)
        print("written", out)
        return 0
    if "--dump" in argv:
        sys.path.insert(0, here)
        os.environ["GW2_SIMULATE"] = "1"
        from mumblelink import MumbleLink, get_identity_name
        ml = MumbleLink()
        for _ in range(5):
            ml.read()
            print(list(ml.data.fAvatarPosition), ml.data.uiTick, get_identity_name(ml), ml.context.mapId)
            time.sleep(0.5)
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
