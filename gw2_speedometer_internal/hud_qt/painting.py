"""Primitivas de pintado compartidas: panel translúcido con sombra suave, texto con sombra."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPen

from .theme import Theme, with_alpha


def setup(p: QPainter):
    p.setRenderHints(QPainter.RenderHint.Antialiasing
                     | QPainter.RenderHint.TextAntialiasing
                     | QPainter.RenderHint.SmoothPixmapTransform)


def draw_panel(p, r: QRectF, th: Theme, radius=None, tint=None, tint_strength=0.0, glow=None,
               glow_strength=0.0):
    radius = th.px(14) if radius is None else radius
    p.save()
    p.setPen(Qt.PenStyle.NoPen)
    # sombra suave (capas concéntricas, desplazada hacia abajo)
    layers = 7
    for i in range(layers, 0, -1):
        s = th.px(1.15) * i
        a = 16 * (layers + 1 - i) / layers
        p.setBrush(QColor(0, 0, 0, int(a)))
        p.drawRoundedRect(r.adjusted(-s, -s + th.px(2.5), s, s + th.px(2.5)), radius + s, radius + s)
    # halo de color (flash de checkpoint)
    if glow is not None and glow_strength > 0.01:
        for i in range(6, 0, -1):
            s = th.px(1.6) * i
            p.setBrush(with_alpha(glow, 30 * glow_strength * (7 - i) / 6))
            p.drawRoundedRect(r.adjusted(-s, -s, s, s), radius + s, radius + s)
    # relleno degradado translúcido
    a = 255 * th.bg_alpha
    g = QLinearGradient(r.topLeft(), r.bottomLeft())
    g.setColorAt(0.0, with_alpha(Theme.PANEL_TOP, a * 1.0))
    g.setColorAt(1.0, with_alpha(Theme.PANEL_BOTTOM, a * 1.06))
    p.setBrush(QBrush(g))
    p.drawRoundedRect(r, radius, radius)
    if tint is not None and tint_strength > 0.01:
        tg = QLinearGradient(r.topLeft(), r.bottomLeft())
        tg.setColorAt(0.0, with_alpha(tint, 120 * tint_strength))
        tg.setColorAt(1.0, with_alpha(tint, 40 * tint_strength))
        p.setBrush(QBrush(tg))
        p.drawRoundedRect(r, radius, radius)
    # borde fino con brillo superior
    bg = QLinearGradient(r.topLeft(), r.bottomLeft())
    bg.setColorAt(0.0, QColor(255, 255, 255, 58))
    bg.setColorAt(0.5, QColor(255, 255, 255, 16))
    bg.setColorAt(1.0, QColor(255, 255, 255, 26))
    pen = QPen(QBrush(bg), max(1.0, th.px(1.0)))
    if glow is not None and glow_strength > 0.01:
        pen = QPen(with_alpha(glow, 90 + 150 * glow_strength), th.px(1.5))
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    hw = pen.widthF() / 2
    p.drawRoundedRect(r.adjusted(hw, hw, -hw, -hw), radius - hw, radius - hw)
    p.restore()


def draw_text(p, rect, flags, text, font, color, shadow=0.7, th=None):
    p.setFont(font)
    if shadow > 0:
        k = th.scale if th else 1.0
        for dy, a in ((1.0, 150), (2.0, 60)):
            p.setPen(QColor(0, 0, 0, int(a * shadow)))
            p.drawText(QRectF(rect).translated(0, dy * k), flags, text)
    p.setPen(color)
    p.drawText(QRectF(rect), flags, text)


def label(p, x, y, w, h, text, th, size=10, color=None, align=Qt.AlignmentFlag.AlignLeft,
          weight=700, spacing=1.2):
    draw_text(p, QRectF(x, y, w, h), align | Qt.AlignmentFlag.AlignVCenter, text,
              th.font(size, weight, spacing=spacing), color or Theme.TEXT_DIM, shadow=0.5, th=th)


def pill(p, r: QRectF, color, fill_alpha=48, border_alpha=170):
    p.save()
    p.setPen(QPen(with_alpha(color, border_alpha), max(1.0, r.height() * 0.06)))
    p.setBrush(with_alpha(color, fill_alpha))
    p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
    p.restore()


def lerp(a, b, t):
    return a + (b - a) * t


def pt(x, y):
    return QPointF(x, y)
