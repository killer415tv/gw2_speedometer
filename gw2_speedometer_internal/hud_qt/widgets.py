"""Widgets del HUD pintados con QPainter (sin estilos Qt nativos)."""

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QFontMetricsF,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
    QRadialGradient,
)
from PySide6.QtWidgets import QWidget

from .model import HudState, fmt_delta, fmt_time
from .painting import draw_panel, draw_text, label, pill, setup
from .theme import Theme, lerp_color, with_alpha

AL, AR, AC = Qt.AlignmentFlag.AlignLeft, Qt.AlignmentFlag.AlignRight, Qt.AlignmentFlag.AlignHCenter
AV, AT, AB = Qt.AlignmentFlag.AlignVCenter, Qt.AlignmentFlag.AlignTop, Qt.AlignmentFlag.AlignBottom
MINUS = "\u2212"


def nice_delta(d, digits=2):
    return fmt_delta(d, digits).replace("-", MINUS)


class HudPanel(QWidget):
    """Base: guarda tema/estado, margen para la sombra y pintado antialias."""

    MARGIN = 9

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.th = theme
        self.state = HudState()
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)

    # fuente en píxeles reales (ya escalados)
    def f(self, px, weight=600, spacing=0.0, tnum=False):
        s = self.th.scale
        return self.th.font(px / s, weight, spacing=spacing, tnum=tnum)

    def inner(self):
        m = self.th.px(self.MARGIN)
        return QRectF(self.rect()).adjusted(m, m, -m, -m)

    def set_state(self, s: HudState):
        self.state = s

    def update_state(self, s: HudState):  # misma API que HudWindow
        self.set_state(s)

    def tick(self, dt):
        pass

    def paintEvent(self, _ev):
        p = QPainter(self)
        setup(p)
        p.setOpacity(self.th.opacity)
        self.paint(p, self.inner())
        p.end()

    def paint(self, p, r):
        draw_panel(p, r, self.th)


# ----------------------------------------------------------------------------- velocímetro
class Speedometer(HudPanel):
    VMAX = 150.0
    START, SWEEP = 210.0, 240.0  # grados Qt (antihorario desde las 3), recorrido horario

    def __init__(self, theme, parent=None):
        super().__init__(theme, parent)
        self.x = 0.0      # valor de la aguja (muelle críticamente amortiguado)
        self.vel = 0.0
        self.acc_disp = 0.0
        self.boost_glow = 0.0
        self.initialized = False

    @classmethod
    def height_for_width(cls, w, th, compact=False):
        m = th.px(cls.MARGIN)
        iw = w - 2 * m
        pad = th.px(12 if compact else 16)
        r = (iw - 2 * pad) / 2
        return 2 * m + 2 * pad + r * (2.0 if compact else 2.30)

    def tick(self, dt):
        target = max(0.0, min(self.VMAX + 8, self.state.speed))
        if not self.initialized:
            self.x, self.initialized = target, True
        k = 90.0
        c = 2 * math.sqrt(k)
        n = max(1, int(dt / 0.004))
        h = dt / n
        for _ in range(n):
            a = k * (target - self.x) - c * self.vel
            self.vel += a * h
            self.x += self.vel * h
        self.acc_disp += (self.state.accel - self.acc_disp) * min(1.0, dt * 8)
        tb = 1.0 if self.state.boost else 0.0
        self.boost_glow += (tb - self.boost_glow) * min(1.0, dt * 6)

    def ang(self, v):
        return self.START - self.SWEEP * max(0.0, min(1.0, v / self.VMAX))

    def paint(self, p, R):
        th = self.th
        compact = th.compact
        draw_panel(p, R, th, radius=th.px(18))
        pad = th.px(12 if compact else 16)
        r = (R.width() - 2 * pad) / 2
        cx, cy = R.center().x(), R.top() + pad + r
        C = QPointF(cx, cy)
        v = max(0.0, self.x)
        col = Theme.speed_color(v)

        ring_r, ring_w = r * 0.90, r * 0.085
        arc_rect = QRectF(cx - ring_r, cy - ring_r, 2 * ring_r, 2 * ring_r)
        # pista del arco
        p.setPen(QPen(QColor(255, 255, 255, 22), ring_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
        p.drawArc(arc_rect, int(self.ang(self.VMAX) * 16), int(self.SWEEP * 16))
        # aro fino de zonas (verde / naranja / rojo)
        zr = r * 0.995
        zrect = QRectF(cx - zr, cy - zr, 2 * zr, 2 * zr)
        for a, b, c in ((0, 99, Theme.GREEN), (99, 120, Theme.ORANGE), (120, 150, Theme.RED)):
            p.setPen(QPen(with_alpha(c, 150), max(1.5, r * 0.018), Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
            a0 = self.ang(b)
            p.drawArc(zrect, int(a0 * 16), int((self.ang(a) - a0) * 16) - 8)
        # arco activo con degradado cónico
        gpos = lambda val: (self.ang(val) - (self.START - self.SWEEP)) / 360.0
        g = QConicalGradient(C, self.START - self.SWEEP)
        for val, c in ((150, QColor(255, 40, 70)), (126, Theme.RED), (120, Theme.ORANGE),
                       (103, QColor(255, 190, 50)), (99, QColor(190, 235, 70)),
                       (88, Theme.GREEN), (0, QColor(0, 200, 170))):
            g.setColorAt(max(0.0, min(1.0, gpos(val))), c)
        g.setColorAt(1.0, QColor(0, 200, 170))
        span = self.SWEEP * min(1.0, v / self.VMAX)
        if span > 0.3:
            for wmul, alpha in ((2.6, 40), (1.7, 70)):  # glow
                pen = QPen(with_alpha(col, alpha), ring_w * wmul, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap)
                p.setPen(pen)
                p.drawArc(arc_rect, int(self.ang(v) * 16), int(span * 16))
            p.setPen(QPen(QBrush(g), ring_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
            p.drawArc(arc_rect, int(self.ang(v) * 16), int(span * 16))
        # marcas
        for val in range(0, 151, 5):
            a = math.radians(self.ang(val))
            major = val % 10 == 0
            r0 = r * (0.74 if major else 0.775)
            r1 = r * 0.81
            ca, sa = math.cos(a), -math.sin(a)
            lit = val <= v
            c = QColor(255, 255, 255, 220 if (major and lit) else 150 if major else 70)
            p.setPen(QPen(c, r * (0.016 if major else 0.009), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(cx + ca * r0, cy + sa * r0), QPointF(cx + ca * r1, cy + sa * r1))
        # marca de boost (99)
        a = math.radians(self.ang(99))
        ca, sa = math.cos(a), -math.sin(a)
        tri = QPolygonF([QPointF(cx + ca * r * 1.0, cy + sa * r * 1.0),
                         QPointF(cx + ca * r * 0.93 - sa * r * 0.035, cy + sa * r * 0.93 + ca * r * 0.035),
                         QPointF(cx + ca * r * 0.93 + sa * r * 0.035, cy + sa * r * 0.93 - ca * r * 0.035)])
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(Theme.GOLD)
        p.drawPolygon(tri)
        # números de escala
        fnt = self.f(r * (0.085 if not compact else 0.095), 600, tnum=True)
        for val in range(0, 151, 30):
            a = math.radians(self.ang(val))
            lr = r * 0.63
            tx, ty = cx + math.cos(a) * lr, cy - math.sin(a) * lr
            c = Theme.TEXT if val <= v else Theme.TEXT_MUTED
            draw_text(p, QRectF(tx - r * 0.2, ty - r * 0.08, r * 0.4, r * 0.16), AC | AV, str(val), fnt, c,
                      shadow=0.4, th=th)
        # aguja (puntero exterior, no tapa la cifra central)
        a = math.radians(self.ang(v))
        ca, sa = math.cos(a), -math.sin(a)
        nx, ny = -sa, ca
        r0, r1, wb = r * 0.70, r * 0.985, r * 0.032
        needle = QPolygonF([QPointF(cx + ca * r1, cy + sa * r1),
                            QPointF(cx + ca * r0 + nx * wb, cy + sa * r0 + ny * wb),
                            QPointF(cx + ca * (r0 - r * 0.03), cy + sa * (r0 - r * 0.03)),
                            QPointF(cx + ca * r0 - nx * wb, cy + sa * r0 - ny * wb)])
        p.setBrush(Qt.BrushStyle.NoBrush)
        for w, al in ((r * 0.06, 50), (r * 0.035, 90)):
            p.setPen(QPen(with_alpha(col, al), w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(cx + ca * r0, cy + sa * r0), QPointF(cx + ca * r1, cy + sa * r1))
        p.setPen(QPen(QColor(255, 255, 255, 230), r * 0.006))
        p.setBrush(QColor(255, 255, 255))
        p.drawPolygon(needle)
        # disco central sutil
        rg = QRadialGradient(C, r * 0.56)
        rg.setColorAt(0.0, with_alpha(col, 34))
        rg.setColorAt(1.0, with_alpha(col, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(rg))
        p.drawEllipse(C, r * 0.56, r * 0.56)
        # cifra grande + unidades
        draw_text(p, QRectF(cx - r * 0.6, cy - r * 0.47, r * 1.2, r * 0.14), AC | AV, "VELOCIDAD",
                  self.f(r * 0.068, 700, spacing=r * 0.012), Theme.TEXT_DIM, shadow=0.4, th=th)
        draw_text(p, QRectF(cx - r * 0.7, cy - r * 0.34, r * 1.4, r * 0.52), AC | AV, f"{round(v)}",
                  self.f(r * 0.46, 800, tnum=True), Theme.TEXT, shadow=1.0, th=th)
        draw_text(p, QRectF(cx - r * 0.5, cy + r * 0.17, r, r * 0.13), AC | AV, "u/s",
                  self.f(r * 0.075, 600, spacing=r * 0.01), with_alpha(col, 230), shadow=0.4, th=th)

        # barra de aceleración / boost (bajo la velocidad)
        bw, bh = r * 1.06, max(th.px(3), r * 0.034)
        by = cy + r * 0.58
        bx = cx - bw / 2
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 26))
        p.drawRoundedRect(QRectF(bx, by, bw, bh), bh / 2, bh / 2)
        acc = max(-1.0, min(1.0, self.acc_disp / 30.0))
        if abs(acc) > 0.005:
            ln = bw / 2 * abs(acc)
            x0 = cx if acc > 0 else cx - ln
            gc = Theme.ACCENT if acc > 0 else Theme.RED
            lg = QLinearGradient(QPointF(cx, 0), QPointF(cx + (bw / 2 if acc > 0 else -bw / 2), 0))
            lg.setColorAt(0, with_alpha(gc, 120))
            lg.setColorAt(1, gc)
            p.setBrush(with_alpha(gc, 60))
            p.drawRoundedRect(QRectF(x0, by - bh * 0.8, ln, bh * 2.6), bh, bh)
            p.setBrush(QBrush(lg))
            p.drawRoundedRect(QRectF(x0, by, ln, bh), bh / 2, bh / 2)
        p.setBrush(QColor(255, 255, 255, 200))
        p.drawRect(QRectF(cx - th.px(0.75), by - bh * 0.7, th.px(1.5), bh * 2.4))
        ty = by + bh + r * 0.05
        fs = self.f(r * 0.068, 700, spacing=r * 0.008, tnum=True)
        draw_text(p, QRectF(bx, ty, bw / 2, r * 0.13), AL | AV, f"ACEL {self.acc_disp:+.1f}", fs,
                  Theme.TEXT_DIM, shadow=0.4, th=th)
        bg = self.boost_glow
        bc = lerp_color(Theme.TEXT_MUTED, Theme.GOLD, bg)
        tw = r * 0.42
        pill(p, QRectF(bx + bw - tw, ty + r * 0.005, tw, r * 0.12), bc, fill_alpha=20 + 60 * bg,
             border_alpha=80 + 160 * bg)
        draw_text(p, QRectF(bx + bw - tw, ty, tw, r * 0.13), AC | AV, "BOOST", fs, bc, shadow=0.3, th=th)

        if compact:
            return
        # tira inferior: altitud / pendiente / distancia
        s = self.state
        sy = cy + r * 0.86
        sh = R.bottom() - pad * 0.6 - sy
        cw = (R.width() - 2 * pad) / 3
        p.setPen(QPen(QColor(255, 255, 255, 22), th.px(1)))
        p.drawLine(QPointF(R.left() + pad, sy - r * 0.02), QPointF(R.right() - pad, sy - r * 0.02))
        items = (("ALTITUD", f"{s.altitude:.0f} m"), ("PENDIENTE", f"{s.slope:+.1f}%"),
                 ("DISTANCIA", f"{s.distance / 1000:.2f} km"))
        for i, (k, val) in enumerate(items):
            x = R.left() + pad + i * cw
            draw_text(p, QRectF(x, sy, cw, sh * 0.42), AC | AV, k, self.f(r * 0.058, 700, spacing=r * 0.01),
                      Theme.TEXT_MUTED, shadow=0.3, th=th)
            draw_text(p, QRectF(x, sy + sh * 0.38, cw, sh * 0.6), AC | AV, val, self.f(r * 0.095, 700, tnum=True),
                      Theme.TEXT, shadow=0.6, th=th)
            if i:
                p.setPen(QPen(QColor(255, 255, 255, 22), th.px(1)))
                p.drawLine(QPointF(x, sy + sh * 0.15), QPointF(x, sy + sh * 0.85))


# ----------------------------------------------------------------------------- cronómetro
class LapTimer(HudPanel):
    def paint(self, p, R):
        th, s = self.th, self.state
        draw_panel(p, R, th)
        pad = th.px(14)
        h = R.height()
        x, w = R.left() + pad, R.width() - 2 * pad
        top = R.top() + pad * 0.7
        lh = h * 0.2
        # "VUELTA 2/3"   ·   mapa
        label(p, x, top, w, lh, "VUELTA", th, size=10)
        fw = self.f(min(h * 0.15, th.px(16)), 800, tnum=True)
        draw_text(p, QRectF(x + th.px(52), top, w, lh), AL | AV, f"{s.lap}/{s.laps_total}", fw, Theme.ACCENT,
                  shadow=0.5, th=th)
        if th.compact:  # compacto: mejor vuelta arriba a la derecha, sin fila inferior
            draw_text(p, QRectF(x, top, w, lh), AR | AV, f"MEJOR {fmt_time(s.best_lap)}",
                      self.f(th.px(10), 700, tnum=True), Theme.GOLD, shadow=0.4, th=th)
            draw_text(p, QRectF(x, top + lh, w, R.bottom() - pad * 0.5 - top - lh), AL | AV,
                      fmt_time(s.lap_time), self.f(h * 0.40, 800, tnum=True), Theme.TEXT, shadow=1.0, th=th)
            return
        fm = self.f(h * 0.1, 600)
        el = QFontMetricsF(fm).elidedText(s.map_name.upper(), Qt.TextElideMode.ElideRight, w * 0.64)
        draw_text(p, QRectF(x, top, w, lh), AR | AV, el, fm, Theme.TEXT_DIM, shadow=0.4, th=th)
        # cronómetro grande
        big = self.f(h * 0.36, 800, tnum=True)
        draw_text(p, QRectF(x, top + lh, w, h * 0.44), AL | AV, fmt_time(s.lap_time), big, Theme.TEXT,
                  shadow=1.0, th=th)
        # mejor / total
        by = R.bottom() - pad * 0.6 - h * 0.17
        fs = self.f(h * 0.105, 700, tnum=True)
        draw_text(p, QRectF(x, by, w, h * 0.17), AL | AV, f"MEJOR  {fmt_time(s.best_lap)}", fs, Theme.GOLD,
                  shadow=0.4, th=th)
        draw_text(p, QRectF(x, by, w, h * 0.17), AR | AV, f"TOTAL  {fmt_time(s.race_time)}", fs,
                      Theme.TEXT_DIM, shadow=0.4, th=th)


# ----------------------------------------------------------------------------- delta
class DeltaPanel(HudPanel):
    FLASH_TIME = 1.4

    def __init__(self, theme, parent=None):
        super().__init__(theme, parent)
        self.disp = 0.0
        self.flash = 0.0
        self.flash_diff = None
        self.flash_label = ""
        self._last_event = None

    def set_state(self, s):
        super().set_state(s)
        if self._last_event is None:
            self._last_event = s.last_cp_event
        elif s.last_cp_event != self._last_event:
            self._last_event = s.last_cp_event
            self.flash = 1.0
            self.flash_diff = s.last_cp_diff
            idx = (s.checkpoint - 1) if s.checkpoint > 0 else len(s.splits) - 1
            self.flash_label = s.splits[idx].label if 0 <= idx < len(s.splits) else "CP"
            if s.checkpoint == 0:
                self.flash_label = "META"

    def tick(self, dt):
        tgt = self.state.delta or 0.0
        self.disp += (tgt - self.disp) * min(1.0, dt * 10)
        self.flash = max(0.0, self.flash - dt / self.FLASH_TIME)

    def paint(self, p, R):
        th, s = self.th, self.state
        fl = self.flash
        fe = fl * fl * (3 - 2 * fl)  # smoothstep
        showing_split = fl > 0.0 and self.flash_diff is not None
        val = self.flash_diff if showing_split else self.disp
        col = Theme.delta_color(round(val, 2))
        draw_panel(p, R, th, tint=col if showing_split else None, tint_strength=fe * 0.9,
                   glow=col if showing_split else None, glow_strength=fe)
        pad = th.px(14)
        h = R.height()
        x, w = R.left() + pad, R.width() - 2 * pad
        top = R.top() + pad * 0.7
        lh = h * 0.2
        label(p, x, top, w, lh, "DELTA · MEJOR VUELTA" if not th.compact else "DELTA", th, size=10)
        # badge CP
        bw = th.px(64)
        br = QRectF(x + w - bw, top + lh * 0.1, bw, lh * 0.8)
        cp_txt = self.flash_label if showing_split else f"CP {min(s.checkpoint + 1, s.checkpoints_total)}/{s.checkpoints_total}"
        bc = col if showing_split else Theme.ACCENT
        pill(p, br, bc, fill_alpha=40 + 120 * fe, border_alpha=150)
        draw_text(p, br, AC | AV, cp_txt, self.f(lh * 0.52, 800, tnum=True),
                  Theme.TEXT if showing_split else Theme.ACCENT, shadow=0.3, th=th)
        # número grande (pulso al cruzar)
        size = h * 0.42 * (1.0 + 0.10 * fe)
        txt = nice_delta(val, 2)
        draw_text(p, QRectF(x, top + lh * 0.9, w - th.px(20), h * 0.5), AL | AV, txt,
                  self.f(size, 800, tnum=True), col, shadow=1.0, th=th)
        sub = "SPLIT" if showing_split else "s"
        draw_text(p, QRectF(x, top + lh * 0.9, w, h * 0.5), AR | AV, sub,
                  self.f(h * 0.11, 700, spacing=th.px(1)), with_alpha(col, 220), shadow=0.4, th=th)
        # barra de tendencia ±1 s
        yb = R.bottom() - pad * 0.75 - th.px(4)
        bh = th.px(4)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 24))
        p.drawRoundedRect(QRectF(x, yb, w, bh), bh / 2, bh / 2)
        k = max(-1.0, min(1.0, val / 1.0))
        cx = x + w / 2
        ln = w / 2 * abs(k)
        p.setBrush(col)
        # negativo (más rápido) crece a la izquierda en verde
        p.drawRoundedRect(QRectF(cx - ln if k < 0 else cx, yb, ln, bh), bh / 2, bh / 2)
        p.setBrush(QColor(255, 255, 255, 190))
        p.drawRect(QRectF(cx - th.px(0.75), yb - bh * 0.6, th.px(1.5), bh * 2.2))


# ----------------------------------------------------------------------------- siguiente CP
class NextCheckpoint(HudPanel):
    def __init__(self, theme, parent=None):
        super().__init__(theme, parent)
        self.ang = 0.0
        self.dist = 0.0

    def tick(self, dt):
        tgt = self.state.next_cp_bearing
        d = (tgt - self.ang + 180) % 360 - 180
        self.ang += d * min(1.0, dt * 9)
        self.dist += (self.state.next_cp_distance - self.dist) * min(1.0, dt * 12)

    def paint(self, p, R):
        th, s = self.th, self.state
        draw_panel(p, R, th)
        pad = th.px(14)
        h = R.height()
        d = h - 2 * pad * 0.9
        d = min(d, R.width() * 0.4)
        cx = R.left() + pad + d / 2
        cy = R.center().y()
        C = QPointF(cx, cy)
        # aro
        rg = QRadialGradient(C, d / 2)
        rg.setColorAt(0, with_alpha(Theme.ACCENT, 50))
        rg.setColorAt(1, with_alpha(Theme.ACCENT, 6))
        p.setBrush(QBrush(rg))
        p.setPen(QPen(with_alpha(Theme.ACCENT, 120), th.px(1.5)))
        p.drawEllipse(C, d / 2, d / 2)
        # ticks cardinales relativos
        p.setPen(QPen(QColor(255, 255, 255, 60), th.px(1.2)))
        for k in range(8):
            a = math.radians(k * 45)
            r0 = d / 2 * (0.80 if k % 2 == 0 else 0.86)
            p.drawLine(QPointF(cx + math.sin(a) * r0, cy - math.cos(a) * r0),
                       QPointF(cx + math.sin(a) * d / 2 * 0.94, cy - math.cos(a) * d / 2 * 0.94))
        # flecha
        p.save()
        p.translate(C)
        p.rotate(self.ang)
        u = d / 2
        arrow = QPolygonF([QPointF(0, -u * 0.66), QPointF(u * 0.42, u * 0.30), QPointF(0, u * 0.10),
                           QPointF(-u * 0.42, u * 0.30)])
        p.setPen(QPen(with_alpha(Theme.ACCENT, 70), u * 0.16, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPolygon(arrow)
        g = QLinearGradient(QPointF(0, -u * 0.66), QPointF(0, u * 0.3))
        g.setColorAt(0, QColor(255, 255, 255))
        g.setColorAt(1, Theme.ACCENT)
        p.setBrush(QBrush(g))
        p.setPen(QPen(QColor(255, 255, 255, 200), th.px(1)))
        p.drawPolygon(arrow)
        p.restore()
        # textos
        x = cx + d / 2 + pad
        w = R.right() - pad - x
        top = R.top() + pad * 0.6
        if th.compact:
            label(p, x, top, w, h * 0.3, f"SIGUIENTE · {s.next_cp_label}", th, size=9)
            draw_text(p, QRectF(x, top + h * 0.25, w, h * 0.45), AL | AV, f"{self.dist:.0f} m",
                      self.f(h * 0.34, 800, tnum=True), Theme.TEXT, shadow=1.0, th=th)
            return
        label(p, x, top, w, h * 0.2, "SIGUIENTE CP", th, size=10)
        draw_text(p, QRectF(x, top + h * 0.17, w, h * 0.22), AL | AV, s.next_cp_label,
                  self.f(h * 0.15, 800, spacing=th.px(1)), Theme.ACCENT, shadow=0.5, th=th)
        draw_text(p, QRectF(x, top + h * 0.37, w, h * 0.36), AL | AV, f"{self.dist:.0f}",
                  self.f(h * 0.31, 800, tnum=True), Theme.TEXT, shadow=1.0, th=th)
        fm_big = self.f(h * 0.31, 800, tnum=True)
        nw = QFontMetricsF(fm_big).horizontalAdvance(f"{self.dist:.0f}")
        draw_text(p, QRectF(x + nw + th.px(5), top + h * 0.43, w, h * 0.28), AL | AV, "m",
                  self.f(h * 0.13, 700), Theme.TEXT_DIM, shadow=0.4, th=th)
        eta = self.dist / max(s.speed, 1.0)
        side = "DER" if self.ang > 4 else "IZQ" if self.ang < -4 else "RECTO"
        draw_text(p, QRectF(x, R.bottom() - pad * 0.6 - h * 0.18, w, h * 0.18), AL | AV,
                  f"ETA {eta:.1f} s   ·   {abs(self.ang):.0f}° {side}", self.f(h * 0.095, 700, tnum=True),
                  Theme.TEXT_DIM, shadow=0.4, th=th)


# ----------------------------------------------------------------------------- splits
class SplitsTable(HudPanel):
    def paint(self, p, R):
        th, s = self.th, self.state
        draw_panel(p, R, th)
        pad = th.px(12)
        x, w = R.left() + pad, R.width() - 2 * pad
        top = R.top() + pad * 0.6
        hh = th.px(22)
        label(p, x, top, w, hh, "SPLITS", th, size=10, color=Theme.TEXT)
        label(p, x, top, w, hh, "VS MEJOR", th, size=8.5, align=AR, color=Theme.TEXT_MUTED, spacing=1.0)
        rows = s.splits or []
        n = max(1, len(rows))
        y0 = top + hh + th.px(2)
        rh = (R.bottom() - pad * 0.6 - y0) / n
        c1, c2 = x + th.px(4), x + w * 0.27
        ft = self.f(min(rh * 0.56, th.px(13)), 700, tnum=True)
        fl = self.f(min(rh * 0.5, th.px(11.5)), 800, spacing=th.px(0.6))
        for i, sp in enumerate(rows):
            y = y0 + i * rh
            rr = QRectF(x - th.px(4), y + rh * 0.06, w + th.px(8), rh * 0.88)
            current = i == s.checkpoint and not s.finished
            if current:
                g = QLinearGradient(rr.topLeft(), rr.topRight())
                g.setColorAt(0, with_alpha(Theme.ACCENT, 70))
                g.setColorAt(1, with_alpha(Theme.ACCENT, 10))
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(g))
                p.drawRoundedRect(rr, th.px(5), th.px(5))
                p.setBrush(Theme.ACCENT)
                p.drawRoundedRect(QRectF(rr.left(), rr.top() + rh * 0.15, th.px(3), rr.height() - rh * 0.3),
                                  th.px(1.5), th.px(1.5))
            elif i % 2 == 0:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(255, 255, 255, 9))
                p.drawRoundedRect(rr, th.px(5), th.px(5))
            done = sp.time is not None
            lc = Theme.ACCENT if current else Theme.TEXT if done else Theme.TEXT_MUTED
            draw_text(p, QRectF(c1 + th.px(4), y, w * 0.25, rh), AL | AV, sp.label, fl, lc, shadow=0.3, th=th)
            if done:
                draw_text(p, QRectF(c2, y, w * 0.45, rh), AL | AV, fmt_time(sp.time), ft, Theme.TEXT,
                          shadow=0.4, th=th)
                dc = Theme.delta_color(round(sp.diff, 3))
                pr = QRectF(x + w - th.px(62), y + rh * 0.16, th.px(62), rh * 0.68)
                pill(p, pr, dc, fill_alpha=40, border_alpha=0)
                draw_text(p, pr, AC | AV, nice_delta(sp.diff, 3), ft, dc, shadow=0.3, th=th)
            else:
                t = fmt_time(s.lap_time) if current else "--:--.---"
                draw_text(p, QRectF(c2, y, w * 0.45, rh), AL | AV, t, ft,
                          with_alpha(Theme.ACCENT, 200) if current else Theme.TEXT_MUTED, shadow=0.3, th=th)
                draw_text(p, QRectF(x + w - th.px(62), y, th.px(62), rh), AC | AV, "·" if not current else "…",
                          ft, Theme.TEXT_MUTED, shadow=0.0, th=th)


# ----------------------------------------------------------------------------- minimapa
class MiniMap(HudPanel):
    def __init__(self, theme, parent=None):
        super().__init__(theme, parent)
        self.t = 0.0

    def tick(self, dt):
        self.t += dt

    def paint(self, p, R):
        th, s = self.th, self.state
        draw_panel(p, R, th)
        if not s.track:
            return
        pad = th.px(16)
        xs = [q[0] for q in s.track]
        zs = [q[1] for q in s.track]
        minx, maxx, minz, maxz = min(xs), max(xs), min(zs), max(zs)
        top_h = th.px(16)
        area = QRectF(R.left() + pad, R.top() + pad + top_h * 0.5, R.width() - 2 * pad,
                      R.height() - 2 * pad - top_h * 0.5)
        k = min(area.width() / (maxx - minx), area.height() / (maxz - minz))
        ox = area.center().x() - (minx + maxx) / 2 * k
        oz = area.center().y() + (minz + maxz) / 2 * k

        def m(q):
            return QPointF(ox + q[0] * k, oz - q[1] * k)  # norte arriba

        path = QPainterPath(m(s.track[0]))
        for q in s.track[1:]:
            path.lineTo(m(q))
        path.closeSubpath()
        p.setBrush(Qt.BrushStyle.NoBrush)
        for w, c in ((th.px(11), QColor(0, 0, 0, 110)), (th.px(7), QColor(70, 80, 100, 200)),
                     (th.px(4.5), QColor(150, 160, 180, 120))):
            p.setPen(QPen(c, w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.drawPath(path)
        # progreso de la vuelta
        pi = min(range(len(s.track)), key=lambda i: (s.track[i][0] - s.player_pos[0]) ** 2
                 + (s.track[i][1] - s.player_pos[1]) ** 2)
        if pi > 0:
            prog = QPainterPath(m(s.track[0]))
            for q in s.track[1:pi + 1]:
                prog.lineTo(m(q))
            prog.lineTo(m(s.player_pos))
            p.setPen(QPen(with_alpha(Theme.ACCENT, 45), th.px(8), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawPath(prog)
            p.setPen(QPen(with_alpha(Theme.ACCENT, 190), th.px(2.4), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawPath(prog)
        # checkpoints
        for i, q in enumerate(s.checkpoints_xy):
            c = m(q)
            if i == len(s.checkpoints_xy) - 1:  # meta: bandera a cuadros
                sq = th.px(3)
                for a in range(4):
                    for b in range(2):
                        p.setPen(Qt.PenStyle.NoPen)
                        p.setBrush(QColor(255, 255, 255) if (a + b) % 2 == 0 else QColor(20, 20, 20))
                        p.drawRect(QRectF(c.x() - 2 * sq + a * sq, c.y() - sq + b * sq, sq, sq))
                continue
            passed = i < s.checkpoint
            nxt = i == s.checkpoint
            if nxt:
                ph = (self.t * 1.6) % 1.0
                p.setPen(QPen(with_alpha(Theme.ACCENT, 220 * (1 - ph)), th.px(1.5)))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(c, th.px(5 + 9 * ph), th.px(5 + 9 * ph))
            p.setPen(QPen(QColor(0, 0, 0, 160), th.px(1)))
            p.setBrush(Theme.ACCENT if nxt else QColor(255, 255, 255, 220) if passed else QColor(120, 130, 150))
            p.drawEllipse(c, th.px(3.6), th.px(3.6))
        # rivales
        fr = self.f(th.px(7.5), 800)
        for rv in s.rivals:
            c = m(rv.pos)
            col = QColor(*rv.color)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(with_alpha(col, 70))
            p.drawEllipse(c, th.px(9), th.px(9))
            p.setPen(QPen(QColor(10, 12, 18), th.px(1.5)))
            p.setBrush(col)
            p.drawEllipse(c, th.px(6.2), th.px(6.2))
            draw_text(p, QRectF(c.x() - th.px(6), c.y() - th.px(6), th.px(12), th.px(12)), AC | AV,
                      rv.name[0], fr, QColor(15, 15, 20), shadow=0.0, th=th)
        # ghost
        if s.ghost_pos:
            c = m(s.ghost_pos)
            p.setPen(QPen(QColor(255, 255, 255, 230), th.px(1.6), Qt.PenStyle.DashLine))
            p.setBrush(QColor(255, 255, 255, 60))
            p.drawEllipse(c, th.px(6.2), th.px(6.2))
        # jugador (flecha orientada)
        c = m(s.player_pos)
        p.save()
        p.translate(c)
        p.rotate(-math.degrees(s.player_heading))
        u = th.px(9)
        tri = QPolygonF([QPointF(u * 1.1, 0), QPointF(-u * 0.7, u * 0.72), QPointF(-u * 0.35, 0),
                         QPointF(-u * 0.7, -u * 0.72)])
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(with_alpha(Theme.ACCENT, 80))
        p.drawEllipse(QPointF(0, 0), u * 1.5, u * 1.5)
        p.setPen(QPen(QColor(255, 255, 255), th.px(1.5), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                      Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Theme.ACCENT)
        p.drawPolygon(tri)
        p.restore()
        # título + leyenda (centro de la elipse)
        label(p, R.left() + pad * 0.8, R.top() + pad * 0.45, R.width(), top_h, "MAPA", th, size=9.5,
              color=Theme.TEXT)
        label(p, R.left(), R.top() + pad * 0.45, R.width() - pad * 0.8, top_h, "N ↑", th, size=9,
              align=AR, color=Theme.TEXT_MUTED)
        entries = [("Ghost", QColor(255, 255, 255), s.delta, True)]
        entries += [(rv.name, QColor(*rv.color), rv.gap, False) for rv in s.rivals]
        lh = th.px(14.5)
        lx = area.center().x() - th.px(56)
        ly = area.center().y() - lh * len(entries) / 2
        fn = self.f(th.px(9.5), 700)
        fg = self.f(th.px(9.5), 700, tnum=True)
        for i, (name, col, gap, ghost) in enumerate(entries):
            y = ly + i * lh
            p.setPen(QPen(col, th.px(1.3), Qt.PenStyle.DashLine if ghost else Qt.PenStyle.SolidLine))
            p.setBrush(with_alpha(col, 60) if ghost else col)
            p.drawEllipse(QPointF(lx + th.px(4), y + lh / 2), th.px(3.6), th.px(3.6))
            draw_text(p, QRectF(lx + th.px(12), y, th.px(60), lh), AL | AV, name, fn, Theme.TEXT, shadow=0.5, th=th)
            if gap is not None:
                # gap > 0: el rival va detrás (tú ganas) -> verde; delta ghost: negativo = verde
                good = (gap < 0) if ghost else (gap > 0)
                gc = Theme.GREEN if good else Theme.RED
                txt = nice_delta(gap, 2)  # rivales: + = va detrás de ti
                draw_text(p, QRectF(lx + th.px(64), y, th.px(48), lh), AR | AV, txt, fg, gc, shadow=0.5, th=th)
