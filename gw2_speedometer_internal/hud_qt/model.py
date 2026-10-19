"""Contrato de datos del HUD.

El HUD sólo lee un ``HudState``. Cualquier fuente (simulada, o en el futuro un
adaptador sobre la medición real de speedometer.py) sólo tiene que rellenarlo.
"""

from dataclasses import dataclass, field

Point = tuple[float, float]  # (x, z) en metros, plano horizontal de GW2


@dataclass
class Split:
    label: str                      # "CP1".."CP6", "META"
    time: float | None = None    # tiempo acumulado de vuelta al cruzar (s)
    diff: float | None = None    # diferencia vs mejor vuelta en ese CP (s)


@dataclass
class Rival:
    name: str
    color: tuple[int, int, int]
    pos: Point
    gap: float = 0.0                # segundos (+ detrás de ti, - delante)


@dataclass
class RankEntry:
    pos: int
    name: str
    time: float
    is_player: bool = False


@dataclass
class HudState:
    # --- telemetría instantánea ---
    speed: float = 0.0              # unidades del speedometer (99 = boost beetle)
    accel: float = 0.0              # unidades/s^2
    boost: bool = False
    altitude: float = 0.0           # m
    slope: float = 0.0              # %
    distance: float = 0.0           # m recorridos en la vuelta
    # --- carrera ---
    map_name: str = ""
    lap: int = 1
    laps_total: int = 3
    lap_time: float = 0.0
    best_lap: float | None = None
    race_time: float = 0.0
    checkpoint: int = 0             # checkpoints ya cruzados en la vuelta
    checkpoints_total: int = 7      # incluida la meta
    delta: float | None = None   # s vs mejor vuelta/ghost (neg = más rápido)
    last_cp_event: int = 0          # contador que sube en cada cruce de CP
    last_cp_diff: float | None = None
    splits: list[Split] = field(default_factory=list)
    # --- siguiente checkpoint ---
    next_cp_label: str = ""
    next_cp_distance: float = 0.0   # m (línea recta)
    next_cp_bearing: float = 0.0    # grados relativos al rumbo (+ = derecha)
    # --- minimapa ---
    track: list[Point] = field(default_factory=list)
    checkpoints_xy: list[Point] = field(default_factory=list)
    player_pos: Point = (0.0, 0.0)
    player_heading: float = 0.0     # rad, atan2(dz, dx)
    ghost_pos: Point | None = None
    rivals: list[Rival] = field(default_factory=list)
    # --- trazas velocidad vs distancia ---
    trace: list[tuple[float, float]] = field(default_factory=list)       # vuelta actual
    best_trace: list[tuple[float, float]] = field(default_factory=list)  # mejor vuelta
    lap_length: float = 1.0
    cp_distances: list[float] = field(default_factory=list)  # m desde la salida
    # --- fin de carrera ---
    finished: bool = False
    final_time: float | None = None
    race_best_lap: float | None = None    # mejor vuelta de esta carrera
    race_best_delta: float | None = None  # vs récord previo (ghost)
    ranking: list[RankEntry] = field(default_factory=list)
    ranking_total: int = 0


def fmt_time(t: float | None, placeholder: str = "--:--.---") -> str:
    """mm:ss.mmm"""
    if t is None:
        return placeholder
    t = max(0.0, t)
    m = int(t // 60)
    s = t - 60 * m
    ms = round((s - int(s)) * 1000)
    si = int(s)
    if ms == 1000:
        ms = 0
        si += 1
    if si == 60:
        si = 0
        m += 1
    return f"{m:02d}:{si:02d}.{ms:03d}"


def fmt_delta(d: float | None, digits: int = 2) -> str:
    if d is None:
        return "--.--" if digits == 2 else "--.---"
    sign = "-" if d < 0 else "+"
    return f"{sign}{abs(d):.{digits}f}"
