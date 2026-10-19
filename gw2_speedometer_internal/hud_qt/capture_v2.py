"""Capturas del HUD v2 minimalista + selector de mapas (composición sobre fondo simulado)."""

import os
import shutil
import subprocess
import tempfile

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

from .capture import Driver, compose, game_background, render_argb
from .map_catalog import load_catalog
from .map_selector import MapSelector
from .minimal import MinimalOverlay, OverlayOptions
from .sim_source import SimRace
from .theme import Theme

W, H = 1920, 1080


def skill_bar(img, scale=1.0):
    """Barra de habilidades centrada (como en GW2) para ver que el medidor no la tapa."""
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QBrush, QLinearGradient, QPen

    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    w, h = img.width(), img.height()
    s, gap, n = 50 * scale, 5 * scale, 10
    x0 = w / 2 - (n * (s + gap) + 24 * scale) / 2
    for i in range(n):
        x = x0 + i * (s + gap) + (24 * scale if i >= 5 else 0)
        r = QRectF(x, h - s - 22 * scale, s, s)
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0, QColor(78, 66, 96, 235))
        g.setColorAt(1, QColor(30, 26, 40, 235))
        p.setPen(QPen(QColor(205, 175, 115, 190), 2 * scale))
        p.setBrush(QBrush(g))
        p.drawRoundedRect(r, 5 * scale, 5 * scale)
    # orbe de vida
    c = img.rect().center()
    p.setPen(QPen(QColor(205, 175, 115, 200), 2 * scale))
    p.setBrush(QColor(170, 30, 40, 230))
    p.drawEllipse(QRectF(c.x() - 34 * scale, h - 92 * scale, 68 * scale, 68 * scale))
    p.end()
    return img


def _bg(scale=1.0):
    bg = game_background(W, H)
    if scale != 1.0:
        bg = bg.scaled(int(W * scale), int(H * scale), Qt.AspectRatioMode.IgnoreAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)
    return skill_bar(bg.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied), scale)


def _overlay(scale, opts=None):
    ov = MinimalOverlay(Theme(scale=scale), opts or OverlayOptions())
    ov.resize(int(W * scale), int(H * scale))
    return ov


def run_capture_v2(outdir, online=True):
    os.makedirs(outdir, exist_ok=True)
    app = QApplication.instance()
    bg1, bg2 = _bg(1.0), _bg(2.0)
    sim = SimRace(laps=3)
    ov1, ov2 = _overlay(1.0), _overlay(2.0)
    ov_x = _overlay(1.0, OverlayOptions(show_splits=True, show_minimap=True, show_nextcp=True))
    drv = Driver(sim, [ov1, ov2, ov_x])
    saved = []

    def save(img, name):
        path = os.path.join(outdir, name)
        img.save(path)
        saved.append(path)
        print("guardado", path)

    def detail(ov, bg):
        img = compose(bg, [(render_argb(ov), (0, 0))])
        c = ov.center()
        cw, ch = 1760, 640
        return img.copy(QRect(int(c.x() - cw / 2), int(c.y() - ch / 2 - 40), cw, ch))

    drv.until(lambda s: s.lap == 2 and s.checkpoint == 4 and 106 < s.speed < 116 and s.accel > 2
              and ov1.flash == 0)
    save(compose(bg1, [(render_argb(ov1), (0, 0))]), "01_minimal_centrado.png")
    save(detail(ov2, bg2), "02_minimal_detalle.png")
    save(compose(bg1, [(render_argb(ov_x), (0, 0))]), "07_opcionales_splits_minimapa_cp.png")
    ev = sim.state.last_cp_event
    drv.until(lambda s: s.last_cp_event != ev and s.checkpoint == 5)
    drv.step(int(0.22 / drv.dt))
    save(detail(ov2, bg2), "03_flash_checkpoint.png")
    # variante: ancla "center" + offset (medidor sobre el cielo/horizonte claro), sin velo
    ov_c = _overlay(1.0, OverlayOptions(anchor="center", offset_y=150, scrim=0.0))
    ov_c.update_state(sim.state)
    for _ in range(90):
        ov_c.tick(1 / 60)
    save(compose(bg1, [(render_argb(ov_c), (0, 0))]), "08_ancla_centro_sin_velo.png")
    drv.step(int(1.6 / drv.dt))  # que termine el flash antes del selector

    # selector de mapas sobre el juego (con el HUD debajo)
    sel = MapSelector(Theme(scale=1.0))
    sel.set_catalog(load_catalog(online=online))
    sel.move(W - 40, H - 40)  # fuera del puntero: sin estado hover en la captura
    sel.show()
    from PySide6.QtGui import QCursor
    QCursor.setPos(0, 0)
    app.processEvents()
    sel_pos = ((W - sel.width()) // 2, int(H * 0.06))
    base = compose(bg1, [(render_argb(ov1), (0, 0))])
    p = QPainter(base)
    p.fillRect(base.rect(), QColor(4, 8, 14, 70))
    p.end()
    app.processEvents()
    save(compose(base, [(render_argb(sel), sel_pos)]), "04_selector_mapas.png")
    sel.search.setText("drft")
    sel._move(1)
    sel._move(1)
    app.processEvents()
    save(compose(base, [(render_argb(sel), sel_pos)]), "05_selector_mapas_busqueda.png")
    sel.close()

    # GIF
    gif = os.path.join(outdir, "06_animado.gif")
    drv.until(lambda s: s.lap == 3 and s.checkpoint == 0 and s.lap_time > 2.6)
    _gif(drv, ov1, bg1, gif)
    saved.append(gif)
    return saved


def _gif(drv, ov, bg, path, seconds=6.5, fps=12):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("ffmpeg no disponible: se omite el GIF")
        return
    app = QApplication.instance()
    c = ov.center()
    cw, ch = 940, 330
    rect = QRect(int(c.x() - cw / 2), int(c.y() - ch / 2 - 20), cw, ch)
    tmp = tempfile.mkdtemp(prefix="hudgif2_")
    sub = max(1, round(1 / (fps * drv.dt)))
    for i in range(int(seconds * fps)):
        drv.step(sub)
        app.processEvents()
        compose(bg, [(render_argb(ov), (0, 0))]).copy(rect).save(os.path.join(tmp, f"f{i:04d}.png"))
    vf = ("fps=12,split[a][b];[a]palettegen=max_colors=160:stats_mode=diff[p];"
          "[b][p]paletteuse=dither=sierra2_4a:diff_mode=rectangle")
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-framerate", str(fps), "-i",
                    os.path.join(tmp, "f%04d.png"), "-vf", vf, "-loop", "0", path], check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    print("guardado", path, f"{os.path.getsize(path) / 1e6:.2f} MB")


__all__ = ["QPoint", "run_capture_v2"]
