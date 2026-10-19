"""Smoke tests de la maqueta hud_qt (se saltan si PySide6 no está instalado)."""
import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from hud_qt.capture import render_argb
from hud_qt.finish_screen import FinishScreen
from hud_qt.hud_window import HudWindow
from hud_qt.model import fmt_delta, fmt_time
from hud_qt.sim_source import SimRace
from hud_qt.theme import Theme
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_formatters():
    assert fmt_time(65.4321) == "01:05.432"
    assert fmt_time(None) == "--:--.---"
    assert fmt_delta(-0.421) == "-0.42"
    assert fmt_delta(0.3) == "+0.30"


def test_sim_race_runs_to_finish():
    sim = SimRace(laps=2)
    events = 0
    last = sim.state.last_cp_event
    while not sim.finished:
        s = sim.step(1 / 30)
        if s.last_cp_event != last:
            events += 1
            last = s.last_cp_event
    assert events == 2 * len(sim.track.cp_dist)
    assert len(sim.lap_times) == 2
    assert sim.state.ranking and any(e.is_player for e in sim.state.ranking)


def _opaque_pixels(img):
    w, h = img.width(), img.height()
    return sum(1 for x in range(0, w, 7) for y in range(0, h, 7) if img.pixelColor(x, y).alpha() > 0)


@pytest.mark.parametrize("compact", [False, True])
def test_hud_renders_with_transparency(app, compact):
    sim = SimRace(laps=1)
    hud = HudWindow(Theme(compact=compact))
    for _ in range(240):
        hud.update_state(sim.step(1 / 60))
        hud.tick(1 / 60)
    img = render_argb(hud)
    assert img.pixelColor(0, 0).alpha() == 0          # esquina transparente
    assert _opaque_pixels(img) > 500                  # hay contenido pintado
    assert hud.splits.isHidden() == compact


def test_finish_screen_renders(app):
    sim = SimRace(laps=1)
    while not sim.finished:
        sim.step(1 / 30)
    fin = FinishScreen(Theme())
    fin.set_state(sim.state)
    assert _opaque_pixels(render_argb(fin)) > 500
