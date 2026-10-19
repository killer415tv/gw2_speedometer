"""Fuente de datos SIMULADA para la maqueta del HUD (datos de ejemplo, no medición).

Reutiliza la geometría del circuito elíptico de ``mumblelink_linux`` (--simulate)
y los checkpoints de ``maps/SIM_CIRCUIT.csv``; si no están disponibles usa una
copia local de la misma elipse. Genera: jugador, ghost (mejor vuelta), 3 rivales
ficticios, splits, delta, trazas de velocidad vs distancia y ranking inventado.

No abre MumbleLink, no escribe logs y no toca speedometer.py.
"""

import csv
import math
import os
import random
from bisect import bisect_left
from itertools import pairwise

from .model import HudState, RankEntry, Rival, Split

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(HERE)

try:  # misma elipse que mumblelink_linux --simulate
    import sys

    if APP_DIR not in sys.path:
        sys.path.insert(0, APP_DIR)
    import mumblelink_linux as _ml

    _pos3 = _ml._pos
    CENTER, SEMI_A, SEMI_B = _ml.CENTER, _ml.SEMI_A, _ml.SEMI_B
except (ImportError, AttributeError):  # pragma: no cover - fallback autónomo
    CENTER, SEMI_A, SEMI_B = (0.0, 120.0, 0.0), 900.0, 500.0

    def _pos3(theta):
        return (CENTER[0] + SEMI_A * math.cos(theta),
                CENTER[1] + 25.0 * math.sin(2.0 * theta),
                CENTER[2] + SEMI_B * math.sin(theta))

MAP_NAME = "Gendarran Fields · SIM_CIRCUIT"
TWO_PI = 2.0 * math.pi


def _load_checkpoint_thetas():
    """Ángulos de los checkpoints intermedios ('*') de maps/SIM_CIRCUIT.csv."""
    path = os.path.join(APP_DIR, "maps", "SIM_CIRCUIT.csv")
    thetas = []
    try:
        with open(path, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if row["STEPNAME"].strip() != "*":
                    continue
                x, z = float(row["X"]), float(row["Z"])
                th = math.atan2((z - CENTER[2]) / SEMI_B, (x - CENTER[0]) / SEMI_A) % TWO_PI
                thetas.append(th)
    except (OSError, KeyError, ValueError):
        pass
    if not thetas:
        thetas = [TWO_PI * i / 7 for i in range(1, 7)]
    return sorted(thetas)


class Track:
    def __init__(self, samples=3600):
        self.thetas = [TWO_PI * i / samples for i in range(samples + 1)]
        pts = [_pos3(t) for t in self.thetas]
        self.s = [0.0]
        for a, b in pairwise(pts):
            self.s.append(self.s[-1] + math.dist(a, b))
        self.length = self.s[-1]
        self.points_xz = [(p[0], p[2]) for p in pts[::10]]
        cp_th = _load_checkpoint_thetas()
        self.cp_dist = [self.dist_at_theta(t) for t in cp_th] + [self.length]  # + META
        self.cp_labels = [f"CP{i + 1}" for i in range(len(cp_th))] + ["META"]
        self.cp_xz = [(_pos3(t)[0], _pos3(t)[2]) for t in cp_th] + [(_pos3(0)[0], _pos3(0)[2])]

    def dist_at_theta(self, th):
        i = min(int(th / TWO_PI * (len(self.thetas) - 1)), len(self.s) - 1)
        return self.s[i]

    def theta_at(self, d):
        d = d % self.length
        i = bisect_left(self.s, d)
        i = max(1, min(i, len(self.s) - 1))
        s0, s1 = self.s[i - 1], self.s[i]
        f = 0.0 if s1 == s0 else (d - s0) / (s1 - s0)
        return self.thetas[i - 1] + f * (self.thetas[i] - self.thetas[i - 1])

    def sample(self, d):
        th = self.theta_at(d)
        x, y, z = _pos3(th)
        dx, dz = -SEMI_A * math.sin(th), SEMI_B * math.cos(th)
        dy = 50.0 * math.cos(2 * th)
        slope = 100.0 * dy / math.hypot(dx, dz)
        return th, (x, z), y, math.atan2(dz, dx), slope


class Runner:
    """Un corredor que avanza por la pista con un perfil de velocidad propio."""

    def __init__(self, track, seed, pace=1.0, d0=0.0):
        self.track = track
        self.pace = pace
        self.d = d0
        self._set_seed(seed)
        self.v = self.speed_at(d0)

    def _set_seed(self, seed):
        rnd = random.Random(seed)
        self.ph = [rnd.uniform(0, TWO_PI) for _ in range(3)]
        self.amp = [rnd.uniform(1.5, 3.2), rnd.uniform(0.6, 1.6), rnd.uniform(0.3, 0.9)]

    def speed_at(self, d):
        th = self.track.theta_at(d)
        # curvas en los extremos de la elipse (~90), rectas con boost (~130)
        base = 88.0 + 44.0 * math.sin(th) ** 2
        var = (self.amp[0] * math.sin(3 * th + self.ph[0])
               + self.amp[1] * math.sin(7 * th + self.ph[1])
               + self.amp[2] * math.sin(13 * th + self.ph[2]))
        return max(0.0, (base + var) * self.pace)

    def step(self, dt):
        self.v = self.speed_at(self.d)
        self.d += self.v * dt  # 1 unidad/s ~ 1 m/s en la maqueta


def _record_lap(track, seed, pace, dt=1 / 120):
    r = Runner(track, seed, pace)
    t, ts, ds, vs = 0.0, [0.0], [0.0], [r.v]
    while r.d < track.length:
        r.step(dt)
        t += dt
        ts.append(t)
        ds.append(min(r.d, track.length))
        vs.append(r.v)
    return ts, ds, vs


def _interp(x, xs, ys):
    i = bisect_left(xs, x)
    if i <= 0:
        return ys[0]
    if i >= len(xs):
        return ys[-1]
    x0, x1 = xs[i - 1], xs[i]
    f = 0.0 if x1 == x0 else (x - x0) / (x1 - x0)
    return ys[i - 1] + f * (ys[i] - ys[i - 1])


class SimRace:
    """Carrera simulada a N vueltas. ``step(dt)`` avanza y devuelve un HudState."""

    RIVALS = (("Kasmeer", (255, 84, 190), 1.010, 70.0),
              ("Rytlock", (255, 150, 40), 0.996, -30.0),
              ("Taimi", (150, 120, 255), 0.986, -110.0))

    LAP_PACE = (0.997, 1.0095, 1.004)  # vuelta 2 más rápida que la mejor -> delta verde

    def __init__(self, laps=3, seed=7):
        self.track = Track()
        self.laps_total = laps
        self.seed = seed
        self.best_t, self.best_d, self.best_v = _record_lap(self.track, seed=100, pace=1.0)
        self.best_lap = self.best_t[-1]
        self.reset()

    # ------------------------------------------------------------------
    def reset(self):
        tr = self.track
        self.player = Runner(tr, seed=self.seed)
        self.rivals = [Runner(tr, seed=self.seed * 10 + i, pace=p, d0=d0)
                       for i, (_, _, p, d0) in enumerate(self.RIVALS)]
        self.race_time = 0.0
        self.lap_start = 0.0
        self.lap = 1
        self.prev_v = self.player.v
        self.accel = 0.0
        self.cp_index = 0
        self.cp_event = 0
        self.last_cp_diff = None
        self.splits = [Split(lbl) for lbl in tr.cp_labels]
        self.trace = [(0.0, self.player.v)]
        self.finished = False
        self.final_time = None
        self.lap_times = []
        self.state = HudState()
        self._fill()

    def best_time_at(self, d):
        return _interp(d, self.best_d, self.best_t)

    def step(self, dt):
        if self.finished or dt <= 0:
            return self.state
        tr = self.track
        p = self.player
        # semilla distinta por vuelta para que cada vuelta sea un poco distinta
        p._set_seed(self.seed + self.lap)
        p.pace = self.LAP_PACE[(self.lap - 1) % len(self.LAP_PACE)]
        p.step(dt)
        for r in self.rivals:
            r.step(dt)
        self.race_time += dt
        self.accel += ((p.v - self.prev_v) / dt - self.accel) * min(1.0, dt * 6)
        self.prev_v = p.v

        d_lap = p.d - (self.lap - 1) * tr.length
        lap_time = self.race_time - self.lap_start
        # cruces de checkpoint
        while self.cp_index < len(tr.cp_dist) and d_lap >= tr.cp_dist[self.cp_index]:
            cp_d = tr.cp_dist[self.cp_index]
            over = (d_lap - cp_d) / max(p.v, 1e-3)
            t_cross = lap_time - over
            diff = t_cross - self.best_time_at(cp_d)
            self.splits[self.cp_index].time = t_cross
            self.splits[self.cp_index].diff = diff
            self.last_cp_diff = diff
            self.cp_event += 1
            self.cp_index += 1
            if self.cp_index == len(tr.cp_dist):  # vuelta completada
                self.lap_times.append(t_cross)
                if self.lap >= self.laps_total:
                    self.finished = True
                    self.final_time = self.race_time - over
                    break
                self.lap += 1
                self.lap_start = self.race_time - over
                self.cp_index = 0
                self._last_splits = self.splits
                self.splits = [Split(lbl) for lbl in tr.cp_labels]
                self.trace = []
                d_lap -= tr.length
                lap_time = self.race_time - self.lap_start
        if not self.finished and (not self.trace or d_lap - self.trace[-1][0] >= 4.0):
            self.trace.append((max(0.0, d_lap), p.v))
        self._fill()
        return self.state

    # ------------------------------------------------------------------
    def _fill(self):
        tr, p, s = self.track, self.player, self.state
        d_lap = min(max(0.0, p.d - (self.lap - 1) * tr.length), tr.length)
        lap_time = (self.race_time - self.lap_start) if not self.finished else self.lap_times[-1]
        _th, pos, alt, heading, slope = tr.sample(p.d)
        s.speed, s.accel, s.boost = p.v, self.accel, p.v >= 99.0
        s.altitude, s.slope, s.distance = alt, slope, d_lap
        s.map_name = MAP_NAME
        s.lap, s.laps_total = self.lap, self.laps_total
        s.lap_time, s.race_time = lap_time, self.race_time
        s.best_lap = self.best_lap
        s.checkpoint, s.checkpoints_total = self.cp_index, len(tr.cp_dist)
        s.delta = (lap_time - self.best_time_at(d_lap)) if d_lap > 1.0 else 0.0
        s.last_cp_event, s.last_cp_diff = self.cp_event, self.last_cp_diff
        s.splits = self.splits
        nxt = min(self.cp_index, len(tr.cp_xz) - 1)
        s.next_cp_label = tr.cp_labels[nxt]
        cx, cz = tr.cp_xz[nxt]
        vx, vz = cx - pos[0], cz - pos[1]
        s.next_cp_distance = math.hypot(vx, vz)
        rel = math.degrees(math.atan2(vz, vx) - heading)
        rel = (rel + 180.0) % 360.0 - 180.0
        s.next_cp_bearing = -rel  # + = derecha (vista cenital, norte arriba)
        s.track = tr.points_xz
        s.checkpoints_xy = tr.cp_xz
        s.player_pos, s.player_heading = pos, heading
        g_d = _interp(lap_time, self.best_t, self.best_d)
        s.ghost_pos = tr.sample(g_d)[1]
        s.rivals = []
        for (name, col, _, _), r in zip(self.RIVALS, self.rivals):
            gap = (p.d - r.d) / max(p.v, 1.0)
            s.rivals.append(Rival(name, col, tr.sample(r.d)[1], gap))
        s.trace = self.trace
        s.best_trace = [(d, v) for d, v in zip(self.best_d[::40], self.best_v[::40])]
        s.lap_length = tr.length
        s.cp_distances = tr.cp_dist
        s.finished = self.finished
        s.final_time = self.final_time
        if self.lap_times:
            s.race_best_lap = min(self.lap_times)
            s.race_best_delta = s.race_best_lap - self.best_lap
        if self.finished:
            ft = self.final_time
            s.ranking = [RankEntry(1, "Zojja.4821", ft - 2.315),
                         RankEntry(2, "Braham.1180", ft - 0.874),
                         RankEntry(3, "Tú (Sim Racer)", ft, True),
                         RankEntry(4, "Marjory.9034", ft + 0.612),
                         RankEntry(5, "Canach.2277", ft + 1.958)]
            s.ranking_total = 128
