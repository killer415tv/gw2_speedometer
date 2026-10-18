"""Scenario catalogue for the golden tests (see golden_harness.py)."""

from golden_harness import (
    MAP_UNSORTED_NO_RADIUS,
    MAP_WITH_RESET,
    A,
    Path,
    S,
    Scenario,
    circuit,
    make_ticks,
    map_csv,
)

ACCEL_3D = {"speed_in_3D": 1, "hud_acceleration": 1, "hud_distance": 1}
PLAIN_2D = {"speed_in_3D": 0, "hud_acceleration": 0}


def _chain(*runs, gap=0.5):
    out = []
    next_start = None
    for run in runs:
        shift = 0.0 if next_start is None else next_start - run[0]["t"]
        for tk in run:
            tk = dict(tk)
            tk["t"] = tk["t"] + shift
            tk["i"] = len(out)
            tk["tick"] = len(out)
            out.append(tk)
        next_start = out[-1]["t"] + gap
    return out


def _slow_zone_profile(waypoints, s_center, half, v):
    """Default speed, but ``v`` m/step while within ``half`` m of ``s_center`` metres."""
    base = Path(waypoints, [(0, 10**6, 1.8288)])
    lo = hi = None
    k = 0
    while base.s_at(k) < base.total:
        s = base.s_at(k)
        if lo is None and s >= s_center - half:
            lo = k
        if hi is None and s >= s_center + half:
            hi = k
        k += 1
    return [(0, lo, 1.8288), (lo, hi, v), (hi, 10**6, 1.8288)]


def build():
    sc = {}

    def add(s):
        assert s.name not in sc
        sc[s.name] = s

    add(
        Scenario(
            "v2_1lap_3d_accel_q64",
            settings=ACCEL_3D,
            ticks=make_ticks(circuit(1), seed=1, clock="q64"),
        )
    )
    add(
        Scenario(
            "v2_1lap_2d_noaccel_fine",
            settings=PLAIN_2D,
            ticks=make_ticks(
                circuit(1), seed=2, clock="fine", stalls=((250, 10), (500, 3))
            ),
        )
    )
    add(
        Scenario(
            "v2_3laps_upload_session_ws",
            laps=3,
            upload=1,
            session_id="ROOM1",
            websocket=True,
            settings=ACCEL_3D,
            ticks=make_ticks(circuit(3), seed=3, clock="q64"),
        )
    )
    add(
        Scenario(
            "v2_1lap_upload_message",
            laps=1,
            upload=1,
            session_id="ROOM2",
            settings=PLAIN_2D,
            ticks=make_ticks(circuit(1), seed=4, clock="fine"),
        )
    )
    add(
        Scenario(
            "v2_2laps_no_upload_session",
            laps=2,
            upload=0,
            session_id="ROOM3",
            settings=ACCEL_3D,
            ticks=make_ticks(circuit(2), seed=5, clock="q64", jitter=False, stalls=()),
        )
    )
    # reset sphere: teleport back to A in the middle of a race, then a 2nd race
    run1 = make_ticks(circuit(1), seed=6, clock="q64", max_ticks=420)
    run2 = make_ticks(circuit(1), seed=7, clock="q64")
    add(
        Scenario(
            "v2_reset_sphere_then_new_race",
            map_text=MAP_WITH_RESET,
            settings=ACCEL_3D,
            ticks=_chain(run1, run2),
        )
    )
    # manual reset from the UI (Racer.reset) in the middle of a race
    run1 = make_ticks(circuit(1), seed=8, clock="q64", max_ticks=450)
    run2 = make_ticks(circuit(1), seed=9, clock="q64")

    def manual_reset(ns, rec):
        ns["Racer"].reset(ns["racer"])

    add(
        Scenario(
            "v2_manual_reset_then_new_race",
            settings=PLAIN_2D,
            ticks=_chain(run1, run2),
            actions={451: manual_reset},
        )
    )
    add(
        Scenario(
            "v2_log_disabled",
            settings=dict(ACCEL_3D, log=0),
            upload=1,
            ticks=make_ticks(circuit(1), seed=10, clock="q64"),
        )
    )
    add(
        Scenario(
            "v1_1lap_3d_accel",
            meter="Meter",
            settings=ACCEL_3D,
            ticks=make_ticks(circuit(1), seed=11, clock="q64"),
        )
    )
    add(
        Scenario(
            "v1_2laps_upload_2d",
            meter="Meter",
            laps=2,
            upload=1,
            settings=PLAIN_2D,
            ticks=make_ticks(circuit(2), seed=12, clock="fine"),
        )
    )
    # Meter (v1) + multiplayer session: documents the UnboundLocalError
    add(
        Scenario(
            "v1_session_unbound_map_angle",
            meter="Meter",
            session_id="ROOM4",
            settings=ACCEL_3D,
            ticks=make_ticks(circuit(1), seed=13, clock="q64", max_ticks=600),
        )
    )
    add(
        Scenario(
            "v2_unsorted_map_no_radius_col",
            map_text=MAP_UNSORTED_NO_RADIUS,
            settings=ACCEL_3D,
            ticks=make_ticks(circuit(1), seed=14, clock="fine"),
        )
    )

    def change_map(ns, rec):
        ns["guildhall_name"].set("Another Map")

    ticks = make_ticks(circuit(1), seed=15, clock="q64")
    for tk in ticks:
        if tk["i"] >= 300:
            tk["map_id"] = 2
    add(
        Scenario(
            "v2_map_change_during_race",
            settings=ACCEL_3D,
            ticks=ticks,
            actions={300: change_map},
        )
    )
    add(
        Scenario(
            "v2_no_checkpoints_loaded",
            map_text=None,
            settings=ACCEL_3D,
            ticks=make_ticks(circuit(1), seed=16, clock="q64", max_ticks=500),
        )
    )
    add(
        Scenario(
            "v2_checkpoints_window_off",
            settings=dict(ACCEL_3D, show_checkpoints_window=0),
            ticks=make_ticks(circuit(1), seed=17, clock="q64", max_ticks=500),
        )
    )
    # end sphere at the same place as the start sphere, 2 laps, slow near S
    wp = [
        A,
        S,
        (150.0, 30.0, 20.0),
        (150.0, 50.0, 220.0),
        (-50.0, 70.0, 300.0),
        S,
        (150.0, 30.0, 20.0),
        (150.0, 50.0, 220.0),
        (-50.0, 70.0, 300.0),
        S,
    ]
    lap1_end_s = Path(wp, [(0, 10**6, 1.0)]).seg[4][0]  # arrival at S after lap 1
    prof = _slow_zone_profile(wp, lap1_end_s, 25.0, 0.45)
    same_map = map_csv(
        [
            (0, "start", S, 0),
            (1, "*", (150.0, 30.0, 20.0), 20),
            (2, "*", (150.0, 50.0, 220.0), 0),
            (3, "*", (-50.0, 70.0, 300.0), 12),
            (4, "end", S, 15),
        ]
    )
    add(
        Scenario(
            "v2_end_equals_start_2laps_debounce",
            map_text=same_map,
            laps=2,
            settings=ACCEL_3D,
            ticks=make_ticks(wp, profile=prof, seed=18, clock="q64"),
        )
    )

    # same circuit, but slow while crossing S at the end of lap 1 (arrival at the
    # LAST waypoint of segment 4): the debounce (pressedQ) expires inside the sphere
    arrive_s = Path(wp, [(0, 10**6, 1.0)]).seg[4][0] + Path(wp, [(0, 10**6, 1.0)]).seg[4][1]
    prof2 = _slow_zone_profile(wp, arrive_s, 25.0, 0.45)
    add(
        Scenario(
            "v2_end_equals_start_2laps_slow_at_start",
            map_text=same_map,
            laps=2,
            settings=ACCEL_3D,
            ticks=make_ticks(wp, profile=prof2, seed=22, clock="q64"),
        )
    )
    # livesplit keys + every HUD-only feature on + speed_in_3D flipped while racing
    def flip_2d(ns, rec):
        ns["speed_in_3D"] = 0

    add(
        Scenario(
            "v2_livesplit_all_hud_flags_hot_switch",
            laps=2,
            settings=dict(
                ACCEL_3D,
                enable_livesplit_hotkey=1,
                hud_angles=1,
                hud_max_speed=1,
                hud_altitude=1,
                hud_angles_bubbles=1,
                hud_angles_airboost=1,
                hud_slope=1,
                hud_drift_hold=1,
            ),
            ticks=make_ticks(circuit(2), seed=20, clock="q64", max_ticks=2400),
            actions={300: flip_2d},
        )
    )
    add(
        Scenario(
            "v1_livesplit_all_hud_flags",
            meter="Meter",
            settings=dict(
                PLAIN_2D,
                enable_livesplit_hotkey=1,
                hud_angles=1,
                hud_max_speed=1,
                hud_angles_bubbles=1,
                hud_angles_airboost=1,
                hud_slope=1,
                hud_drift_hold=1,
            ),
            ticks=make_ticks(circuit(1), seed=21, clock="fine", max_ticks=1800),
        )
    )
    # standing still / crawling / boosts only (no checkpoints crossed)
    add(
        Scenario(
            "v2_speed_edge_cases_no_race",
            map_text=None,
            settings=ACCEL_3D,
            session_id="ROOM5",
            websocket=True,
            ticks=make_ticks(
                [A, (A[0] + 400, A[1], A[2] + 300)],
                seed=19,
                clock="fine",
                stalls=((100, 5),),
            ),
        )
    )
    return sc


SCENARIOS = build()
