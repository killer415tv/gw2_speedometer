"""Capturas de la maqueta: renderiza los widgets en QImage ARGB (transparencia real) y
los compone sobre un fondo de "juego" generado, para ver cómo quedaría sobre GW2.

Uso: python hud_qt_demo.py --capture /workspace/capturas/hud_qt
"""

import math
import os
import random
import shutil
import subprocess
import tempfile

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
    QRadialGradient,
    QRegion,
)
from PySide6.QtWidgets import QApplication, QWidget

from .finish_screen import FinishScreen
from .hud_window import HudWindow
from .sim_source import SimRace
from .theme import Theme
from .widgets import MiniMap

W, H = 1920, 1080


# ------------------------------------------------------------------ fondo simulado
def game_background(w=W, h=H, seed=3):
    """Paisaje estilo Tyria al atardecer con un camino (fondo de ejemplo, no del juego)."""
    rnd = random.Random(seed)
    img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    hz = h * 0.52
    sky = QLinearGradient(0, 0, 0, hz)
    sky.setColorAt(0.0, QColor(28, 52, 98))
    sky.setColorAt(0.55, QColor(96, 112, 160))
    sky.setColorAt(0.85, QColor(232, 158, 120))
    sky.setColorAt(1.0, QColor(255, 196, 140))
    p.fillRect(0, 0, w, int(hz) + 2, QBrush(sky))
    sun = QPointF(w * 0.66, hz * 0.86)
    rg = QRadialGradient(sun, h * 0.45)
    rg.setColorAt(0, QColor(255, 236, 190, 230))
    rg.setColorAt(0.08, QColor(255, 214, 150, 160))
    rg.setColorAt(1, QColor(255, 180, 120, 0))
    p.fillRect(0, 0, w, int(hz) + 2, QBrush(rg))
    # nubes
    for _ in range(14):
        cx, cy = rnd.uniform(0, w), rnd.uniform(h * 0.05, hz * 0.6)
        for _ in range(6):
            r = rnd.uniform(40, 120)
            g = QRadialGradient(QPointF(cx + rnd.uniform(-120, 120), cy + rnd.uniform(-20, 20)), r)
            g.setColorAt(0, QColor(255, 225, 215, 60))
            g.setColorAt(1, QColor(255, 225, 215, 0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(g))
            p.drawEllipse(g.center(), r * 2.2, r * 0.7)

    def ridge(base, amp, color, rough, step=12):
        poly = QPolygonF()
        poly.append(QPointF(0, h))
        ph = [rnd.uniform(0, 6.28) for _ in range(4)]
        for x in range(0, w + step, step):
            y = base - amp * (0.55 * math.sin(x / (w * 0.13) + ph[0]) + 0.3 * math.sin(x / (w * 0.05) + ph[1])
                              + rough * 0.15 * math.sin(x / 23.0 + ph[2]) + 0.25 * math.sin(x / (w * 0.31) + ph[3]))
            poly.append(QPointF(x, y))
        poly.append(QPointF(w, h))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawPolygon(poly)

    ridge(hz - 40, 140, QColor(122, 112, 160), 1.0)
    ridge(hz - 10, 90, QColor(92, 92, 138), 1.2)
    ridge(hz + 20, 60, QColor(64, 82, 104), 0.8)
    # suelo
    gr = QLinearGradient(0, hz, 0, h)
    gr.setColorAt(0, QColor(78, 108, 74))
    gr.setColorAt(0.4, QColor(56, 92, 52))
    gr.setColorAt(1, QColor(30, 56, 32))
    p.fillRect(QRectF(0, hz + 30, w, h), QBrush(gr))
    ridge(hz + 70, 25, QColor(60, 96, 58), 0.6)
    # camino en perspectiva con curva
    vp = QPointF(w * 0.56, hz + 64)
    road = QPainterPath(QPointF(w * 0.12, h))
    road.cubicTo(QPointF(w * 0.35, h * 0.80), QPointF(w * 0.52, h * 0.70), QPointF(vp.x() - 6, vp.y()))
    road.lineTo(QPointF(vp.x() + 6, vp.y()))
    road.cubicTo(QPointF(w * 0.60, h * 0.72), QPointF(w * 0.78, h * 0.82), QPointF(w * 0.98, h))
    road.closeSubpath()
    rgd = QLinearGradient(0, vp.y(), 0, h)
    rgd.setColorAt(0, QColor(170, 150, 120))
    rgd.setColorAt(1, QColor(120, 100, 76))
    p.setBrush(QBrush(rgd))
    p.drawPath(road)
    # línea central (adoquines de luz)
    for i in range(16):
        t0, t1 = i / 16, (i + 0.5) / 16
        def at(t):
            return QPointF(vp.x() + (w * 0.55 - vp.x()) * t ** 1.6 - 40 * math.sin(t * 3.0) * t,
                           vp.y() + (h - vp.y()) * t ** 1.6)
        p.setPen(QPen(QColor(240, 230, 200, 120), 1 + 7 * t0))
        p.drawLine(at(t0), at(t1))
    # árboles
    for _ in range(70):
        x = rnd.uniform(0, w)
        depth = rnd.uniform(0, 1)
        y = hz + 50 + depth * (h * 0.35)
        if abs(x - (w * 0.55)) < 140 + depth * 520:
            continue
        s = 18 + depth * 90
        col = QColor(int(28 + 20 * (1 - depth)), int(54 + 26 * (1 - depth)), int(36 + 18 * (1 - depth)))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        for k in range(3):
            tri = QPolygonF([QPointF(x, y - s * (1.6 - k * 0.35)), QPointF(x - s * (0.35 + k * 0.12), y - s * (0.6 - k * 0.3)),
                             QPointF(x + s * (0.35 + k * 0.12), y - s * (0.6 - k * 0.3))])
            p.drawPolygon(tri)
        p.setBrush(QColor(40, 30, 22))
        p.drawRect(QRectF(x - s * 0.05, y - s * 0.32, s * 0.1, s * 0.32))
    # bruma y viñeta
    hg = QLinearGradient(0, hz - 60, 0, hz + 140)
    hg.setColorAt(0, QColor(255, 200, 160, 0))
    hg.setColorAt(0.5, QColor(255, 205, 170, 70))
    hg.setColorAt(1, QColor(255, 200, 160, 0))
    p.fillRect(QRectF(0, hz - 60, w, 200), QBrush(hg))
    vg = QRadialGradient(QPointF(w / 2, h * 0.45), w * 0.75)
    vg.setColorAt(0.55, QColor(0, 0, 0, 0))
    vg.setColorAt(1.0, QColor(0, 0, 0, 150))
    p.fillRect(0, 0, w, h, QBrush(vg))
    p.end()
    # suavizado ligero (aspecto de render de juego)
    img = img.scaled(w // 2, h // 2, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
    img = img.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
    return img.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)


def fake_game_ui(img):
    """Pequeños elementos de UI del 'juego' (barra de habilidades) para dar contexto."""
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    w, h = img.width(), img.height()
    n, s = 10, 52
    x0 = w / 2 - n * (s + 6) / 2 + 260
    for i in range(n):
        r = QRectF(x0 + i * (s + 6), h - s - 26, s, s)
        p.setPen(QPen(QColor(200, 170, 110, 180), 2))
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0, QColor(70, 60, 90, 220))
        g.setColorAt(1, QColor(30, 26, 40, 220))
        p.setBrush(QBrush(g))
        p.drawRoundedRect(r, 6, 6)
    p.end()
    return img


# ------------------------------------------------------------------ render
def render_argb(widget: QWidget) -> QImage:
    img = QImage(widget.size(), QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    widget.render(img, QPoint(0, 0), QRegion(), QWidget.RenderFlag.DrawChildren)
    return img


def compose(bg: QImage, layers):
    out = bg.copy()
    p = QPainter(out)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    for img, pos in layers:
        p.drawImage(QPoint(int(pos[0]), int(pos[1])), img)
    p.end()
    return out


def dim_blur(img, factor=0.35, darken=120):
    small = img.scaled(int(img.width() * factor / 3), int(img.height() * factor / 3),
                       Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
    out = small.scaled(img.width(), img.height(), Qt.AspectRatioMode.IgnoreAspectRatio,
                       Qt.TransformationMode.SmoothTransformation).convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    p = QPainter(out)
    p.fillRect(out.rect(), QColor(5, 8, 14, darken))
    p.end()
    return out


# ------------------------------------------------------------------ escenarios
class Driver:
    """Avanza simulación + animaciones a paso fijo (determinista)."""

    def __init__(self, sim, huds, dt=1 / 60):
        self.sim, self.huds, self.dt = sim, list(huds), dt

    def step(self, n=1):
        for _ in range(n):
            s = self.sim.step(self.dt)
            for h in self.huds:
                h.update_state(s)
                h.tick(self.dt)
        return self.sim.state

    def until(self, cond, limit=200000):
        for _ in range(limit):
            s = self.step()
            if cond(s):
                return s
        raise RuntimeError("condición de captura no alcanzada")


def run_capture(outdir, scale=1.0):
    os.makedirs(outdir, exist_ok=True)
    app = QApplication.instance()
    bg = fake_game_ui(game_background())
    th_full = Theme(scale=scale)
    th_comp = Theme(scale=scale, compact=True)
    sim = SimRace(laps=3)
    full = HudWindow(th_full)
    comp = HudWindow(th_comp)
    th_map = Theme(scale=2.0 * scale)
    big_map = MiniMap(th_map)
    big_map.resize(int(th_map.px(300)), int(th_map.px(220)))
    for w in (full, comp):
        w.show()
    big_map.show()
    app.processEvents()
    drv = Driver(sim, [full, comp, big_map])
    margin = 48
    pos_full = (margin, H - full.height() - margin - 70)
    pos_comp = (margin, H - comp.height() - margin - 70)
    saved = []

    def save(img, name):
        path = os.path.join(outdir, name)
        img.save(path)
        saved.append(path)
        print("guardado", path)

    # 01 HUD completo: vuelta 2, tras CP4, con algo de boost, sin flash activo
    drv.until(lambda s: s.lap == 2 and s.checkpoint == 4 and 106 < s.speed < 116 and s.accel > 2
              and full.delta.flash == 0)
    app.processEvents()
    save(compose(bg, [(render_argb(full), pos_full)]), "01_hud_completo.png")
    # 02 compacto (mismo instante)
    save(compose(bg, [(render_argb(comp), pos_comp)]), "02_hud_compacto.png")
    # 03 flash de checkpoint: 0.25 s después de cruzar CP5 en la vuelta 2
    ev = sim.state.last_cp_event
    drv.until(lambda s: s.last_cp_event != ev and s.checkpoint == 5)
    drv.step(int(0.25 / drv.dt))
    app.processEvents()
    hud = render_argb(full)
    shot = compose(bg, [(hud, pos_full)])
    save(shot, "03_delta_flash_checkpoint.png")
    # 04 minimapa con rivales (escala 2x, recorte con fondo)
    drv.step(int(1.5 / drv.dt))
    mm = render_argb(big_map)
    crop = bg.copy(W - mm.width() - 140, 60, mm.width() + 80, mm.height() + 80)
    save(compose(crop, [(mm, (40, 40))]), "04_minimapa_rivales.png")

    # 06 GIF animado (antes de terminar): 6.5 s cruzando CP1 de la vuelta 3
    gif = os.path.join(outdir, "06_hud_animado.gif")
    drv.until(lambda s: s.lap == 3 and s.checkpoint == 0 and s.lap_time > 2.0)
    make_gif(drv, full, bg, pos_full, gif, seconds=6.5, fps=12)
    if os.path.exists(gif):
        saved.append(gif)

    # 05 fin de carrera
    drv.until(lambda s: s.finished)
    fin = FinishScreen(Theme(scale=scale))
    fin.set_state(sim.state)
    fin.show()
    app.processEvents()
    fimg = render_argb(fin)
    save(compose(dim_blur(bg), [(fimg, ((W - fimg.width()) / 2, (H - fimg.height()) / 2))]),
         "05_fin_de_carrera.png")
    for w in (full, comp, big_map, fin):
        w.close()
    return saved


def make_gif(drv, hud, bg, pos, path, seconds=6.5, fps=15):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("ffmpeg no disponible: se omite el GIF")
        return
    app = QApplication.instance()
    pad = 28
    cx, cy = int(pos[0] - pad), int(pos[1] - pad)
    cw, ch = hud.width() + 2 * pad, hud.height() + 2 * pad
    cw, ch = cw - cw % 2, ch - ch % 2
    crop = bg.copy(cx, cy, cw, ch)
    tmp = tempfile.mkdtemp(prefix="hudgif_")
    frames = int(seconds * fps)
    sub = max(1, round(1 / (fps * drv.dt)))
    for i in range(frames):
        drv.step(sub)
        app.processEvents()
        img = compose(crop, [(render_argb(hud), (pad, pad))])
        img.save(os.path.join(tmp, f"f{i:04d}.png"))
    out_w = min(cw, 760)
    vf = (f"fps={fps},scale={out_w}:-1:flags=lanczos,split[a][b];"
          "[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=sierra2_4a:diff_mode=rectangle")
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-framerate", str(fps), "-i",
                    os.path.join(tmp, "f%04d.png"), "-vf", vf, "-loop", "0", path], check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    print("guardado", path, f"{os.path.getsize(path) / 1e6:.2f} MB")
