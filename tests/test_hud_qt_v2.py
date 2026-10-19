"""Tests de la maqueta v2: overlay minimal centrado + catálogo/selector de mapas (sin red)."""
import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from hud_qt import map_catalog
from hud_qt.capture import render_argb
from hud_qt.map_catalog import MapEntry, load_catalog, normalize
from hud_qt.map_selector import MapSelector
from hud_qt.minimal import MinimalOverlay, OverlayOptions
from hud_qt.sim_source import SimRace
from hud_qt.theme import Theme
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_catalog_offline_uses_snapshot_and_local():
    cat = load_catalog(online=False)
    assert cat.origin == "snapshot"
    titles = [g.title for g in cat.groups]
    assert "TYRIA CUP" in titles and "ALL MAPS" not in titles
    assert any(g.source == "local" and g.title == map_catalog.LOCAL_CUP for g in cat.groups)
    local = next(g for g in cat.groups if g.source == "local")
    assert "SIM_CIRCUIT" in [m.name for m in local.maps]


def test_checkpoints_ref_matches_app_logic():
    on = MapEntry("TYRIA GENDARRAN", "TYRIA CUP", "online")
    assert on.checkpoints_ref == "https://www.beetlerank.com/uploads/checkpoints/TYRIA%20GENDARRAN.csv"
    lo = MapEntry("SIM_CIRCUIT", map_catalog.LOCAL_CUP, "local")
    assert lo.checkpoints_ref.endswith(os.path.join("maps", "SIM_CIRCUIT.csv"))


def test_normalize_accents():
    assert normalize("Küstenwald") == "kustenwald"


def test_selector_filters_and_chooses(app):
    sel = MapSelector(Theme())
    sel.set_catalog(load_catalog(online=False))
    total = sel._visible_count
    sel.search.setText("drft hard")
    assert 0 < sel._visible_count < total
    got = []
    sel.mapChosen.connect(got.append)
    sel._on_click(sel.list.currentItem())
    assert got and "DRFT" in got[0].name.upper() and not sel.isVisible()
    sel.search.setText("")
    sel._set_source("local")
    assert sel._visible_count == sum(len(g.maps) for g in sel.catalog.groups if g.source == "local")


@pytest.mark.parametrize("anchor", ["bottom", "center"])
def test_minimal_overlay_centered_and_transparent(app, anchor):
    ov = MinimalOverlay(Theme(), OverlayOptions(anchor=anchor, offset_y=0 if anchor == "center" else 250))
    ov.resize(1920, 1080)
    sim = SimRace(laps=1)
    for _ in range(120):
        ov.update_state(sim.step(1 / 60))
        ov.tick(1 / 60)
    c = ov.center()
    assert c.x() == 960
    assert c.y() == (540 if anchor == "center" else 830)
    img = render_argb(ov)
    assert img.pixelColor(10, 10).alpha() == 0
    assert img.pixelColor(1910, 540).alpha() == 0
    assert img.pixelColor(int(c.x()), int(c.y())).alpha() > 0
