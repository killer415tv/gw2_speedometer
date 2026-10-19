"""Primitivas de pintado compartidas: panel translúcido con sombra suave, texto con sombra."""

import math
from collections import OrderedDict

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


def _outlined_text_paths(p, x, y, text, font, color, th, align="left", outline=1.0, glow=None, glow_strength=0.0,
                         _origin=None):
    """Texto sin fondo legible sobre cualquier escena: sombra suave + contorno fino + relleno.

    (x, y) = punto de anclaje; y es el centro visual (altura de mayúsculas). Devuelve el ancho.
    """
    from PySide6.QtGui import QFontMetricsF, QPainterPath

    fm = QFontMetricsF(font)
    w = fm.horizontalAdvance(text)
    x0 = x - w if align == "right" else x - w / 2 if align == "center" else x
    base = y + fm.capHeight() / 2
    if _origin is not None:  # sprite rendering: baseline origin given directly
        x0, base = _origin
    path = QPainterPath()
    path.addText(QPointF(x0, base), font, text)
    # Montserrat variable tiene contornos solapados: con OddEven quedarían "agujeros"
    path.setFillRule(Qt.FillRule.WindingFill)
    size = font.pixelSize() if font.pixelSize() > 0 else 12
    k = th.scale if th else 1.0
    p.save()
    p.setBrush(Qt.BrushStyle.NoBrush)
    if glow is not None and glow_strength > 0.01:
        for wmul, a in ((0.42, 40), (0.24, 70)):
            p.setPen(QPen(with_alpha(glow, a * glow_strength), size * wmul, Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.drawPath(path)
    # sombra difusa (dos pasadas) desplazada hacia abajo
    sh = path.translated(0, max(1.0, size * 0.035))
    for wmul, a in ((0.16, 26), (0.09, 50)):
        p.setPen(QPen(QColor(0, 0, 0, int(a * outline)), max(2.0 * k, size * wmul), Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawPath(sh)
    # contorno fino
    p.setPen(QPen(QColor(4, 8, 14, int(175 * outline)), max(1.3 * k, size * 0.055), Qt.PenStyle.SolidLine,
                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.drawPath(path)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    p.drawPath(path)
    p.restore()
    return w


# Rendered-text cache: outlined_text() strokes the glyph outlines 4-6 times with
# wide pens, the most expensive part of an overlay frame. Labels, split rows and
# most numbers repeat from frame to frame, so each (text, font, colour, outline,
# sub-pixel offset) is rendered once into an ARGB sprite and then blitted.
_SPRITES = OrderedDict()
_SPRITE_MAX = 768
_SUBPX = 4  # sub-pixel positions kept (1/4 px), so cached text does not jitter


def clear_text_cache():
    _SPRITES.clear()


def outlined_text(p, x, y, text, font, color, th, align="left", outline=1.0, glow=None, glow_strength=0.0):
    """Texto sin fondo legible sobre cualquier escena: sombra suave + contorno fino + relleno.

    (x, y) = punto de anclaje; y es el centro visual (altura de mayúsculas). Devuelve el ancho.
    Sin glow y con transformación de sólo traslación usa una caché de sprites (mismo resultado;
    con opacidad < 1 el texto se funde como una capa, sin que el contorno se transparente bajo el relleno).
    """
    from PySide6.QtGui import QFontMetricsF, QImage, QTransform

    tr = p.transform()
    if (glow is not None and glow_strength > 0.01) or tr.type().value > QTransform.TransformationType.TxTranslate.value:
        return _outlined_text_paths(p, x, y, text, font, color, th, align, outline, glow, glow_strength)
    fm = QFontMetricsF(font)
    w = fm.horizontalAdvance(text)
    x0 = x - w if align == "right" else x - w / 2 if align == "center" else x
    base = y + fm.capHeight() / 2
    dev = p.device()
    dpr = dev.devicePixelRatioF() if dev is not None and hasattr(dev, "devicePixelRatioF") else 1.0
    # position in device pixels: integer part blitted, fraction baked into the sprite
    dx, dy = (x0 + tr.dx()) * dpr, (base + tr.dy()) * dpr
    ix, iy = math.floor(dx), math.floor(dy)
    fx, fy = round((dx - ix) * _SUBPX), round((dy - iy) * _SUBPX)
    if fx == _SUBPX:
        ix, fx = ix + 1, 0
    if fy == _SUBPX:
        iy, fy = iy + 1, 0
    k = th.scale if th else 1.0
    key = (text, font.key(), color.rgba(), round(outline, 3), round(k, 3), fx, fy, round(dpr, 3))
    hit = _SPRITES.get(key)
    if hit is None:
        size = font.pixelSize() if font.pixelSize() > 0 else 12
        pad = math.ceil(size * 0.35 + 4 * k) + 2
        asc = math.ceil(fm.ascent()) + pad
        wpx = math.ceil((w + 2 * pad) * dpr) + 2
        hpx = math.ceil((fm.height() + 2 * pad) * dpr) + 2
        img = QImage(max(1, wpx), max(1, hpx), QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent)
        q = QPainter(img)
        try:
            setup(q)
            q.scale(dpr, dpr)
            ox, oy = pad + fx / _SUBPX / dpr, asc + fy / _SUBPX / dpr
            _outlined_text_paths(q, 0.0, 0.0, text, font, color, th, "left", outline,
                                 _origin=(ox, oy))
        finally:
            q.end()
        img.setDevicePixelRatio(dpr)
        hit = (img, pad, asc)
        _SPRITES[key] = hit
        if len(_SPRITES) > _SPRITE_MAX:
            _SPRITES.popitem(last=False)
    else:
        _SPRITES.move_to_end(key)
    img, pad, asc = hit
    p.save()
    p.resetTransform()
    p.drawImage(QPointF((ix / dpr) - pad, (iy / dpr) - asc), img)
    p.restore()
    return w


def outlined_line(p, a, b, color, width, th, outline=1.0, cap=Qt.PenCapStyle.RoundCap):
    p.setPen(QPen(QColor(4, 8, 14, int(120 * outline)), width + th.px(2.4), Qt.PenStyle.SolidLine, cap))
    p.drawLine(a, b)
    p.setPen(QPen(color, width, Qt.PenStyle.SolidLine, cap))
    p.drawLine(a, b)
