"""Tests of the optional --qt-hud adapter/bridge (qt_hud_bridge.py) with mocks.

* the adapter is read-only: with it installed every golden scenario still
  produces the very same CSV bytes and observable channels (uploads, MQTT,
  websocket, keys, HUD texts...);
* state serialisation, crossing detection, delta/splits, records;
* sending never blocks (datagrams are dropped instead);
* a map chosen in the Qt HUD reaches racer.changeCup/saveGuildhall on the Tk
  thread (scheduled), and the classic HUD comes back if the Qt process dies.
"""

import copy
import json
import socket
import time

import golden_harness as gh
import pandas as pd
import pytest
import qt_hud_bridge as qb
from golden_scenarios import SCENARIOS

pytestmark = pytest.mark.filterwarnings(
    "ignore:datetime.datetime.utcfromtimestamp:DeprecationWarning"
)


# ------------------------------------------------------------------ helpers --
class Var:
    def __init__(self, value):
        self.value = value
        self.sets = 0

    def get(self):
        return self.value

    def set(self, v):
        self.sets += 1
        self.value = v


class FakeLink:
    """Records what would be sent (after a real JSON encode)."""

    def __init__(self, inbox=()):
        self.peer = ("127.0.0.1", 9)
        self.sent = []
        self.inbox = list(inbox)
        self.token = "t"
        self.port = 9

    def send(self, msg_type, payload=None):
        qb.encode(msg_type, self.token, payload)  # must be serialisable (no NaN...)
        self.sent.append((msg_type, copy.deepcopy(payload)))
        return True

    def poll(self):
        out, self.inbox = self.inbox, []
        return out


MAP = pd.DataFrame(
    {
        "STEP": [0, 1, 2, 3],
        "STEPNAME": ["start", "*", "*", "end"],
        "X": [0.0, 100.0, 100.0, 0.0],
        "Y": [0.0, 0.0, 0.0, 0.0],
        "Z": [0.0, 0.0, 100.0, 100.0],
        "RADIUS": [15, 15, 15, 15],
    }
)


def globals_for(name="Test Map", laps="1 lap", frame=MAP, app_dir="."):
    return {
        "APP_DIR": app_dir,
        "_time": 1000.0,
        "velocity": 0.0,
        "lap": 1,
        "next_step": 0,
        "lap_timer": 0,
        "total_timer": 0,
        "total_distance": 0,
        "guildhall_name": Var(name),
        "guildhall_laps": Var(laps),
        "cup_name": Var("OWN MAPS FOLDER"),
        "checkpoints_list": frame,
        "_3Dpos": [1.0, 2.0, 3.0],
    }


def drive(ad, g, events):
    """events: list of (time, {global: value}) applied in order, one tick each."""
    out = []
    for t, changes in events:
        g["_time"] = t
        g.update(changes)
        out.append(ad.update(g))
    return out


def lap_events(t0, lap_no, cps=(10.0, 20.0, 30.0), last=True, first=True):
    """start at t0, CP1 at t0+cps[0], CP2 at t0+cps[1], end at t0+cps[2]."""
    ev = [(t0 - 1, {})]
    start = {"next_step": 1, "lap_timer": t0}
    if first:
        start["total_timer"] = t0
    ev.append((t0, start))
    ev.append((t0 + cps[0], {"next_step": 2}))
    ev.append((t0 + cps[1], {"next_step": 3}))
    ev.append((t0 + cps[2], {"next_step": 0, "lap": 1 if last else lap_no + 1}))
    return ev


# ---------------------------------------------------------- golden + adapter --
def _hook_with_adapter(captured):
    def hook(ns, rec, workdir, meter):
        link = FakeLink()
        bridge = qb.QtHudBridge(ns, meter, link=link, popen=None, clock=time.monotonic)
        bridge.active = True  # as after a successful start(), without a process
        bridge.install()
        captured.append(bridge)

    return hook


@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_golden_unchanged_with_qt_hud_adapter(name, tmp_path):
    captured = []
    sc = copy.copy(SCENARIOS[name])
    sc.meter_hook = _hook_with_adapter(captured)
    result, files = gh.run_scenario(sc, tmp_path / "app")
    exp_result, exp_files = gh.read_golden(name)
    assert sorted(files) == sorted(exp_files)
    for rel in exp_files:
        assert files[rel] == exp_files[rel], "bytes differ in " + rel
    got = gh.normalise(result)
    for key in sorted(exp_result):
        assert got[key] == exp_result[key], f"golden mismatch in section {key!r}"
    (bridge,) = captured
    if not result["exceptions"]:
        assert bridge.errors == 0
        assert bridge.publisher.last_snapshot is not None


def test_adapter_sees_the_real_crossings_of_a_golden_race(tmp_path):
    captured = []
    sc = copy.copy(SCENARIOS["v2_3laps_upload_session_ws"])
    sc.meter_hook = _hook_with_adapter(captured)
    result, _files = gh.run_scenario(sc, tmp_path / "app")
    tr = captured[0].adapter.tracker
    finishes = [m for m in result["mqtt_non_position"] if m["option"] == "f"]
    assert tr.finished and tr.final_time == pytest.approx(finishes[-1]["time"])
    # every lap-end MQTT time is a race time; the tracker's lap times add up to it
    best = tr.session_best
    assert best is not None and best[1][-1] == best[0]
    snaps = [p for k, p in captured[0].link.sent if k == "state"]
    assert snaps and snaps[-1]["finished"] and snaps[-1]["lap"] == 3
    assert {s["checkpoints_total"] for s in snaps} == {4}
    labels = next(s for k, s in captured[0].link.sent if k == "map")["labels"]
    assert labels == ["CP1", "CP2", "CP3", "META"]


# ------------------------------------------------------------- serialisation --
def test_encode_decode_roundtrip_and_token():
    data = qb.encode("state", "secret", {"speed": 99.5, "splits": [["CP1", 1.0, None]]}, 7)
    msg = qb.decode(data, "secret")
    assert msg["type"] == "state" and msg["seq"] == 7 and msg["data"]["splits"][0][2] is None
    assert qb.decode(data, "other") is None
    assert qb.decode(b"\xff\x00", "secret") is None
    assert qb.decode(json.dumps({"v": 99, "token": "secret"}).encode(), "secret") is None
    with pytest.raises(ValueError):
        qb.encode("state", "s", {"x": float("nan")})


def test_snapshot_is_json_and_fills_hudstate():
    from hud_qt.model import HudState

    ad = qb.StateAdapter()
    g = globals_for()
    snap = ad.update(g)
    json.dumps(snap, allow_nan=False)
    import hud_qt_live

    s = hud_qt_live.state_from_dict(snap, ad.map_payload(g))
    assert isinstance(s, HudState)
    assert s.map_name == "Test Map" and s.checkpoints_total == 3 and len(s.splits) == 3
    assert s.delta is None and s.best_lap is None  # no reference -> HUD shows "--"
    assert len(s.checkpoints_xy) == 3 and len(s.track) == 4


def test_speed_units_and_tk_filters():
    ad = qb.StateAdapter()
    g = globals_for()
    # 7200 in/s -> 72 -> 99 on the Tk HUD big number
    drive(ad, g, [(1.0, {"velocity": 7200.0})])
    assert ad.speed == pytest.approx(99.0)
    # spikes >= 140 (velocity/100) are ignored like the Tk HUD does
    drive(ad, g, [(1.01, {"velocity": 15000.0})])
    assert ad.speed == pytest.approx(99.0)
    # a single 0 between two 25 Hz MumbleLink updates is held for 50 ms
    drive(ad, g, [(1.03, {"velocity": 0.0})])
    assert ad.speed == pytest.approx(99.0)
    drive(ad, g, [(1.2, {"velocity": 0.0})])
    assert ad.speed == 0.0


# ------------------------------------------------------- delta / splits ------
def test_splits_and_delta_against_session_best():
    ad = qb.StateAdapter()
    g = globals_for(laps="2 laps")
    drive(ad, g, lap_events(100.0, 1, (10.0, 20.0, 30.0), last=False))
    tr = ad.tracker
    assert tr.splits == [10.0, 20.0, 30.0] and tr.diffs == [None, None, None]
    assert tr.session_best[0] == 30.0 and not tr.finished
    snaps = drive(ad, g, lap_events(140.0, 2, (9.0, 21.0, 29.5), last=True, first=False))
    assert tr.diffs == [pytest.approx(-1.0), pytest.approx(1.0), pytest.approx(-0.5)]
    after_cp1 = snaps[2]
    assert after_cp1["delta"] == pytest.approx(-1.0) and after_cp1["checkpoint"] == 1
    assert after_cp1["splits"][0] == ["CP1", 9.0, -1.0] and after_cp1["splits"][1][1] is None
    final = snaps[-1]
    assert final["finished"] and final["lap"] == 2 and final["final_time"] == pytest.approx(69.5)
    assert final["best_lap"] == pytest.approx(29.5)
    assert final["last_cp_event"] > after_cp1["last_cp_event"]


def test_lap_time_runs_then_freezes():
    ad = qb.StateAdapter()
    g = globals_for()
    snaps = drive(ad, g, lap_events(100.0, 1)[:3])
    assert snaps[-1]["racing"] and snaps[-1]["lap_time"] == pytest.approx(10.0)
    snaps = drive(ad, g, [(115.0, {})])
    assert snaps[-1]["lap_time"] == pytest.approx(15.0)
    snaps = drive(ad, g, [(130.0, {"next_step": 3}), (140.0, {"next_step": 0}), (150.0, {})])
    assert not snaps[-1]["racing"] and snaps[-1]["lap_time"] == pytest.approx(40.0)


def test_reset_abandons_the_lap():
    ad = qb.StateAdapter()
    g = globals_for()
    drive(ad, g, lap_events(100.0, 1)[:3])
    snaps = drive(ad, g, [(112.0, {"next_step": 0, "lap": 1, "lap_timer": 112.0, "total_timer": 112.0})])
    assert not snaps[-1]["racing"] and snaps[-1]["lap_time"] == 0.0
    assert ad.tracker.session_best is None  # an abandoned lap is never a reference


def test_records_csv_is_the_reference_for_one_lap_races(tmp_path):
    (tmp_path / "Test Map_records.csv").write_text(
        "\r00:31:500,18/10/2026 10:00:00,a\r00:29:250,18/10/2026 11:00:00,b", encoding="utf-8"
    )
    ad = qb.StateAdapter(tmp_path)
    g = globals_for(app_dir=tmp_path)
    snaps = drive(ad, g, lap_events(100.0, 1, (10.0, 20.0, 30.0)))
    assert ad.tracker.record == pytest.approx(29.25)
    assert snaps[0]["best_lap"] == pytest.approx(29.25) and snaps[0]["has_reference"]
    assert snaps[2]["delta"] is None  # the record has no checkpoint splits -> "--"
    final = snaps[-1]
    assert final["last_cp_diff"] == pytest.approx(0.75)
    assert final["race_best_delta"] == pytest.approx(0.75)
    assert qb.parse_record_time("01:02:003") == pytest.approx(62.003)
    assert qb.read_best_record(tmp_path / "missing.csv") is None


def test_adapter_never_writes_globals_or_tk_vars():
    ad = qb.StateAdapter()
    g = globals_for()
    before = {k: (v if not isinstance(v, (Var, pd.DataFrame)) else id(v)) for k, v in g.items()}
    for _ in range(3):
        ad.update(g)
    after = {k: (v if not isinstance(v, (Var, pd.DataFrame)) else id(v)) for k, v in g.items()}
    assert before == after
    assert all(v.sets == 0 for v in g.values() if isinstance(v, Var))


def test_map_change_resets_tracker_and_bumps_map_seq():
    ad = qb.StateAdapter()
    g = globals_for()
    s1 = ad.update(g)
    g["guildhall_name"] = Var("Other")
    g["checkpoints_list"] = MAP.copy()
    s2 = ad.update(g)
    assert s2["map_seq"] == s1["map_seq"] + 1 and s2["map_name"] == "Other"


# --------------------------------------------------------- non-blocking send --
def test_send_drops_instead_of_blocking():
    class FullSock:
        def __init__(self):
            self.calls = 0

        def setblocking(self, flag):
            assert flag is False

        def getsockname(self):
            return ("127.0.0.1", 5555)

        def sendto(self, data, addr):
            self.calls += 1
            raise BlockingIOError

    sock = FullSock()
    link = qb.UdpLink("tok", sock=sock)
    assert link.send("state", {"a": 1}) is False  # no peer yet: dropped, not queued
    link.peer = ("127.0.0.1", 1)
    t0 = time.perf_counter()
    for _ in range(200):
        assert link.send("state", {"a": 1}) is False
    assert time.perf_counter() - t0 < 0.5
    assert link.dropped == 201 and sock.calls == 200


def test_real_udp_link_roundtrip_and_unread_peer():
    server = qb.UdpLink("tok")
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client.bind(("127.0.0.1", 0))
    try:
        client.sendto(qb.encode("hello", "tok"), ("127.0.0.1", server.port))
        client.sendto(qb.encode("hello", "bad"), ("127.0.0.1", server.port))
        time.sleep(0.05)
        msgs = server.poll()
        assert [m["type"] for m in msgs] == ["hello"]
        assert server.peer == client.getsockname()
        # nobody reads the client socket: the sender must never block
        big = {"blob": "x" * 30000}
        t0 = time.perf_counter()
        for _ in range(500):
            server.send("state", big)
        assert time.perf_counter() - t0 < 2.0
        assert server.sent + server.dropped == 500
        assert server.send("state", {"blob": "x" * 70000}) is False  # > MAX_DATAGRAM
    finally:
        client.close()
        server.close()


def test_publisher_throttles_but_sends_crossings_immediately():
    clock = [0.0]
    ad = qb.StateAdapter()
    link = FakeLink()
    pub = qb.QtHudPublisher(ad, link, rate_hz=50, clock=lambda: clock[0])
    g = globals_for()
    for i in range(10):  # 10 ticks within 5 ms -> 1 state message
        clock[0] = i * 0.0005
        g["_time"] = 50 + i * 0.0005
        pub.tick(g)
    assert [k for k, _ in link.sent].count("state") == 1
    g["next_step"], g["lap_timer"], g["total_timer"] = 1, g["_time"], g["_time"]  # start crossed
    clock[0] += 0.0005
    pub.tick(g)
    assert [k for k, _ in link.sent].count("state") == 2
    clock[0] += 0.05
    pub.tick(g)
    assert [k for k, _ in link.sent].count("state") == 3
    assert [k for k, _ in link.sent].count("map") == 1


# ---------------------------------------------------------------- map choice --
class FakeRacer:
    def __init__(self, g):
        self.g = g
        self.calls = []

    def changeCup(self, value):
        self.calls.append(("changeCup", value))
        self.g["cup_name"].set(value)

    def saveGuildhall(self, value, in_background=False):
        self.calls.append(("saveGuildhall", value, in_background))
        self.g["guildhall_name"].set(value)


def _bridge_with_inbox(inbox, g):
    scheduled = []
    link = FakeLink(inbox)
    meter = type("M", (), {"updateMeterTimer": lambda self: None})()
    br = qb.QtHudBridge(g, meter, schedule=scheduled.append, link=link, popen=None)
    br.active = True
    return br, scheduled


def _msg(kind, data=None):
    return {"v": qb.PROTOCOL, "type": kind, "token": "t", "data": data or {}}


def test_map_choice_reaches_change_cup_and_save_guildhall_on_tk_thread():
    g = globals_for()
    g["cup_name"] = Var("CUP")
    racer = g["racer"] = FakeRacer(g)
    br, scheduled = _bridge_with_inbox(
        [_msg("choose_map", {"cup": "TYRIA CUP", "name": "TYRIA GENDARRAN", "source": "online"})], g
    )
    br.after_tick()
    assert racer.calls == []  # not run inside the measurement tick...
    assert len(scheduled) == 1  # ...but queued as its own Tk event (root.after(0, ...))
    scheduled[0]()
    assert racer.calls == [("changeCup", "TYRIA CUP"), ("saveGuildhall", "TYRIA GENDARRAN", False)]


def test_map_choice_same_cup_only_selects_the_map():
    g = globals_for()
    racer = g["racer"] = FakeRacer(g)
    assert qb.apply_map_choice(g, "OWN MAPS FOLDER", "SIM_CIRCUIT")
    assert racer.calls == [("saveGuildhall", "SIM_CIRCUIT", False)]
    g.pop("racer")
    assert not qb.apply_map_choice(g, "OWN MAPS FOLDER", "SIM_CIRCUIT")


def test_speedometer_main_routes_map_choice_like_the_tk_menus():
    """speedometer.py builds its map menus with tk._setit(guildhall_name, choice,
    self.saveGuildhall) and the cup menu with command=self.changeCup: the Qt
    choice must use those two methods (no duplicated loading logic)."""
    src = (gh.INTERNAL / "speedometer.py").read_text(encoding="utf-8")
    assert "command=self.changeCup" in src and "self.saveGuildhall)" in src
    assert "qt_hud_bridge.start(" in src
    import inspect

    body = inspect.getsource(qb.apply_map_choice)
    assert "racer.changeCup(cup)" in body and "racer.saveGuildhall(name)" in body


# ------------------------------------------------------------ process / Tk ----
class FakeWin:
    def __init__(self):
        self.log = []

    def withdraw(self):
        self.log.append("withdraw")

    def deiconify(self):
        self.log.append("deiconify")


class FakeProc:
    pid = 4242

    def __init__(self):
        self.returncode = None
        self.terminated = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True


def test_tk_hud_hidden_on_hello_and_back_when_qt_dies():
    g = globals_for()
    win = FakeWin()
    proc = FakeProc()
    clock = [0.0]
    link = FakeLink([_msg("hello")])
    meter = type("M", (), {"updateMeterTimer": lambda self: None})()
    br = qb.QtHudBridge(g, meter, [win], link=link, popen=lambda *a, **k: proc, clock=lambda: clock[0])
    assert br.start() and br.proc is proc
    cmd = br.command()
    assert cmd[1].endswith("hud_qt_live.py") and "--port" in cmd
    br.after_tick()
    assert win.log == ["withdraw"]
    proc.returncode = 1  # Qt HUD crashed / was closed
    clock[0] = 5.0
    br.after_tick()
    assert win.log == ["withdraw", "deiconify"] and not br.active
    n = len(link.sent)
    br.after_tick()  # no more publishing, nothing raised
    assert len(link.sent) == n


def test_start_failure_keeps_classic_hud():
    def boom(*a, **k):
        raise OSError("no python")

    g = globals_for()
    win = FakeWin()
    meter = type("M", (), {"updateMeterTimer": lambda self: None})()
    br = qb.QtHudBridge(g, meter, [win], link=FakeLink(), popen=boom)
    assert br.start() is False and not br.active and win.log == []


def test_install_wraps_instance_and_isolates_errors():
    calls = []

    class Meter:
        def updateMeterTimer(self):
            calls.append("measure")

    m = Meter()
    g = globals_for()
    br, _ = _bridge_with_inbox([], g)
    br.meter = m
    br.install()
    assert m.updateMeterTimer.__name__ == "updateMeterTimer"
    br.publisher.tick = lambda g: (_ for _ in ()).throw(RuntimeError("bad"))
    m.updateMeterTimer()  # adapter error is swallowed, measurement ran
    assert calls == ["measure"] and br.errors == 1
    for _ in range(qb.QtHudBridge.MAX_ERRORS):
        m.updateMeterTimer()
    assert not br.active  # gave up publishing, back to the classic HUD

    class Broken:
        def updateMeterTimer(self):
            raise ZeroDivisionError

    b = Broken()
    br2, _ = _bridge_with_inbox([], g)
    br2.meter = b
    br2.install()
    with pytest.raises(ZeroDivisionError):  # measurement errors are NOT hidden
        b.updateMeterTimer()


def test_requested_flag():
    assert qb.requested(["--qt-hud"], {}) and not qb.requested([], {})
    assert qb.requested([], {"GW2_QT_HUD": "1"})


# ------------------------------------------------------------- client parts ---
def test_client_hotkey_letter_matching():
    import hud_qt_live

    K = type("K", (), {})

    def key(vk=None, char=None, name=None):
        k = K()
        k.vk, k.char, k.name = vk, char, name
        return k

    hit = []
    hk = hud_qt_live.Hotkeys({"m": lambda: hit.append("m"), "o": lambda: hit.append("o")})
    hk.on_press(key(name="ctrl_l"))
    hk.on_press(key(vk=0x4D, char="\r"))  # Windows: Ctrl+M arrives as '\r'
    assert hit == []  # shift not held
    hk.on_press(key(name="shift"))
    hk.on_press(key(vk=0x4D, char="\r"))
    hk.on_press(key(char="O"))
    hk.on_press(key(char="x"))
    hk.on_release(key(name="shift"))
    hk.on_press(key(char="m"))
    assert hit == ["m", "o"]


def test_parent_alive_posix_self():
    import os

    import hud_qt_live

    assert hud_qt_live.parent_alive(os.getpid())
    assert hud_qt_live.parent_alive(0)


# ------------------------------------------------------------ overlay paint ---
def test_live_overlay_paints_splits_without_reference_and_survives_errors():
    """First lap: splits have a time but no diff (no reference). The mockup's
    _splits did round(None) inside paintEvent, which left the QPainter active:
    the translucent window stopped being cleared and then froze."""
    import os

    pytest.importorskip("PySide6")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    QApplication.instance() or QApplication([])
    import hud_qt_live
    from hud_qt.minimal import OverlayOptions
    from hud_qt.theme import Theme

    ad = qb.StateAdapter()
    g = globals_for()
    snaps = drive(ad, g, lap_events(100.0, 1)[:3])  # CP1 crossed, no reference yet
    assert snaps[-1]["splits"][0][1] == 10.0 and snaps[-1]["splits"][0][2] is None
    cls = hud_qt_live.build_overlay_class()
    ov = cls(Theme(), OverlayOptions(show_splits=True, show_minimap=True, show_nextcp=True))
    ov.resize(1200, 520)
    ov.extra = snaps[-1]
    ov.update_state(hud_qt_live.state_from_dict(snaps[-1], ad.map_payload(g)))
    ov.tick(0.016)
    ov.grab()
    assert ov.paint_errors == 0

    def boom(*a):
        raise RuntimeError("layer failed")

    ov._minimap = boom
    ov.grab()
    ov.grab()  # the painter was ended: painting still works after an error
    assert ov.paint_errors == 2


def test_outlined_text_sprite_cache_matches_path_rendering():
    """The sprite cache must draw the same pixels as stroking the text paths."""
    import os

    pytest.importorskip("PySide6")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QColor, QFont, QImage, QPainter
    from PySide6.QtWidgets import QApplication

    QApplication.instance() or QApplication([])
    from hud_qt import painting
    from hud_qt.theme import Theme

    th = Theme()
    font = QFont()
    font.setPixelSize(28)

    def render(fn, translate=(0.0, 0.0), opacity=1.0):
        img = QImage(400, 120, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(0)
        p = QPainter(img)
        painting.setup(p)
        p.translate(*translate)
        p.setOpacity(opacity)
        fn(p, 30.3, 50.6, "CP3 00:12.345", font, QColor(240, 240, 240), th)
        fn(p, 380.0, 90.25, "-0.42", font, QColor(80, 220, 120), th, align="right")
        p.end()
        return img

    def group_opacity(img, opacity):
        # the sprite applies opacity to the finished text (like a layer), not per stroke
        out = QImage(img.size(), img.format())
        out.fill(0)
        p = QPainter(out)
        p.setOpacity(opacity)
        p.drawImage(0, 0, img)
        p.end()
        return out

    painting.clear_text_cache()
    for kw in ({}, {"translate": (7.5, 3.25)}, {"opacity": 0.5}):
        if "opacity" in kw:
            ref = group_opacity(render(painting._outlined_text_paths), kw["opacity"])
        else:
            ref = render(painting._outlined_text_paths, **kw)
        for _ in range(2):  # miss, then hit
            got = render(painting.outlined_text, **kw)
            bad = 0
            for y in range(0, 120, 2):
                for x in range(0, 400, 2):
                    a, b = QColor.fromRgba(ref.pixel(x, y)), QColor.fromRgba(got.pixel(x, y))
                    if max(abs(a.red() - b.red()), abs(a.green() - b.green()), abs(a.alpha() - b.alpha())) > 40:
                        bad += 1
            assert bad <= 6, (kw, bad)
    assert 0 < len(painting._SPRITES) <= painting._SPRITE_MAX
