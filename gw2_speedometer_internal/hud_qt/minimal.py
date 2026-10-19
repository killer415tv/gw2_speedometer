"""HUD v2 MINIMALISTA: overlay transparente a pantalla completa con el medidor centrado.

Sin tarjetas ni paneles: sólo trazos finos y texto con contorno/sombra sutil, legible sobre
cualquier escena. Por defecto muestra velocidad, cronómetro, delta y vuelta/CP; splits,
minimapa y siguiente checkpoint son opcionales (ocultos por defecto).
"""

import math
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
    QRadialGradient,
)
from PySide6.QtWidgets import QWidget

from .model import HudState, fmt_time
from .painting import outlined_line, outlined_text, setup
from .theme import Theme, lerp_color, with_alpha
from .widgets import nice_delta

LABEL = QColor(206, 215, 230)  # etiquetas pequeñas: más claras que TEXT_DIM para leerse sin fondo


@dataclass
class OverlayOptions:
    anchor: str = "bottom"          # "bottom" (inferior-central) | "center"
    offset_y: float = 250.0         # px a 1080p hacia arriba desde el ancla (se escala)
    offset_x: float = 0.0
    show_splits: bool = False
    show_minimap: bool = False
    show_nextcp: bool = False
    scrim: float = 0.10             # velo radial casi invisible detrás del medidor (0 = nada)


class MinimalOverlay(QWidget):
    VMAX = 150.0
    START, SWEEP = 220.0, 260.0     # anillo abierto por abajo
    FLASH_TIME = 1.5

    def __init__(self, theme: Theme = None, options: OverlayOptions = None, click_through=True,
                 on_top=True, parent=None):
        super().__init__(parent)
        self.th = theme or Theme()
        self.opt = options or OverlayOptions()
        self.state = HudState()
        self._click_through = click_through
        self._on_top = on_top
        self._apply_flags()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setWindowTitle("GW2 Speedometer HUD v2 (maqueta minimal)")
        # animación
        self.needle = 0.0
        self.needle_v = 0.0
        self._init = False
        self.acc = 0.0
        self.boost = 0.0
        self.delta = 0.0
        self.flash = 0.0
        self.flash_diff = None
        self.flash_label = ""
        self._last_event = None
        self.nc_ang = 0.0
        self.t = 0.0
        self.toast_text = ""
        self.toast_t = 0.0

    # ------------------------------------------------------------ ventana
    def _apply_flags(self):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self._on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        if self._click_through:
            flags |= Qt.WindowType.WindowTransparentForInput
        self.setWindowFlags(flags)

    def set_click_through(self, on):
        self._click_through = on
        vis = self.isVisible()
        self._apply_flags()
        if vis:
            self.show()

    def cover_screen(self, screen=None):
        scr = screen or self.screen()
        if scr is not None:
            self.setGeometry(scr.geometry())

    def toast(self, text, seconds=3.0):
        self.toast_text, self.toast_t = text, seconds

    # ------------------------------------------------------------ datos
    def update_state(self, s: HudState):
        self.state = s
        if self._last_event is None:
            self._last_event = s.last_cp_event
        elif s.last_cp_event != self._last_event:
            self._last_event = s.last_cp_event
            self.flash, self.flash_diff = 1.0, s.last_cp_diff
            self.flash_label = "META" if s.checkpoint == 0 else (
                s.splits[s.checkpoint - 1].label if 0 < s.checkpoint <= len(s.splits) else "CP")

    def tick(self, dt):
        s = self.state
        tgt = max(0.0, min(self.VMAX + 6, s.speed))
        if not self._init:
            self.needle, self._init = tgt, True
        k = 90.0
        c = 2 * math.sqrt(k)
        n = max(1, int(dt / 0.004))
        for _ in range(n):
            h = dt / n
            self.needle_v += (k * (tgt - self.needle) - c * self.needle_v) * h
            self.needle += self.needle_v * h
        self.acc += (s.accel - self.acc) * min(1.0, dt * 8)
        self.boost += ((1.0 if s.boost else 0.0) - self.boost) * min(1.0, dt * 6)
        self.delta += ((s.delta or 0.0) - self.delta) * min(1.0, dt * 10)
        self.flash = max(0.0, self.flash - dt / self.FLASH_TIME)
        d = (s.next_cp_bearing - self.nc_ang + 180) % 360 - 180
        self.nc_ang += d * min(1.0, dt * 9)
        self.t += dt
        self.toast_t = max(0.0, self.toast_t - dt)
        self.update()

    # ------------------------------------------------------------ geometría
    def center(self):
        px = self.th.px
        w, h = self.width(), self.height()
        cx = w / 2 + px(self.opt.offset_x)
        if self.opt.anchor == "center":
            cy = h / 2 - px(self.opt.offset_y)
        else:
            cy = h - px(self.opt.offset_y)
        return QPointF(cx, cy)

    def ang(self, v):
        return self.START - self.SWEEP * max(0.0, min(1.0, v / self.VMAX))

    def f(self, px, weight=700, spacing=0.0, tnum=False):
        return self.th.font(px, weight, spacing=spacing, tnum=tnum)

    # ------------------------------------------------------------ pintado
    def paintEvent(self, _e):
        p = QPainter(self)
        setup(p)
        p.setOpacity(self.th.opacity)
        C = self.center()
        R = self.th.px(104)
        self._scrim(p, C, R)
        self._gauge(p, C, R)
        self._delta(p, C, R)
        self._timer(p, C, R)
        if self.opt.show_nextcp:
            self._nextcp(p, C, R)
        if self.opt.show_splits:
            self._splits(p, C, R)
        if self.opt.show_minimap:
            self._minimap(p, C, R)
        self._toast(p, C, R)
        p.end()

    def _scrim(self, p, C, R):
        a = self.opt.scrim
        if a <= 0.001:
            return
        p.save()
        p.translate(C)
        p.scale(2.6, 1.0)
        g = QRadialGradient(QPointF(0, 0), R * 1.5)
        g.setColorAt(0.0, QColor(0, 0, 0, int(255 * a)))
        g.setColorAt(0.6, QColor(0, 0, 0, int(160 * a)))
        g.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(g))
        p.drawEllipse(QPointF(0, 0), R * 1.5, R * 1.5)
        p.restore()

    def _gauge(self, p, C, R):
        th = self.th
        v = max(0.0, self.needle)
        col = Theme.speed_color(v)
        cx, cy = C.x(), C.y()
        rect = QRectF(cx - R, cy - R, 2 * R, 2 * R)
        fl = self.flash
        fcol = Theme.delta_color(round(self.flash_diff, 2)) if self.flash_diff is not None else Theme.ACCENT
        # onda del flash de checkpoint
        if fl > 0:
            e = 1 - fl
            rr = R * (1.0 + 0.30 * e)
            p.setPen(QPen(with_alpha(fcol, 150 * fl * fl), th.px(2.0)))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(C, rr, rr)
        # pista: contorno oscuro + línea fina clara
        a0, span_all = int(self.ang(self.VMAX) * 16), int(self.SWEEP * 16)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(4, 8, 14, 95), th.px(7.5), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(rect, a0, span_all)
        p.setPen(QPen(QColor(255, 255, 255, 60), th.px(3.0), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(rect, a0, span_all)
        # zonas naranja/roja (sutiles, por fuera)
        zr = R + th.px(7)
        zrect = QRectF(cx - zr, cy - zr, 2 * zr, 2 * zr)
        for lo, hi, c in ((99, 120, Theme.ORANGE), (120, 150, Theme.RED)):
            p.setPen(QPen(with_alpha(c, 150), th.px(1.6), Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
            p.drawArc(zrect, int(self.ang(hi) * 16), int((self.ang(lo) - self.ang(hi)) * 16))
        # marcas mínimas cada 10
        for val in range(0, 151, 10):
            a = math.radians(self.ang(val))
            major = val % 30 == 0
            r0, r1 = R - th.px(9 if major else 7), R - th.px(5)
            p.setPen(QPen(QColor(255, 255, 255, 170 if major else 85), th.px(1.6 if major else 1.1),
                          Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(cx + math.cos(a) * r0, cy - math.sin(a) * r0),
                       QPointF(cx + math.cos(a) * r1, cy - math.sin(a) * r1))
        # marca boost 99 (dorada)
        a = math.radians(self.ang(99))
        outlined_line(p, QPointF(cx + math.cos(a) * (R - th.px(11)), cy - math.sin(a) * (R - th.px(11))),
                      QPointF(cx + math.cos(a) * (R + th.px(10)), cy - math.sin(a) * (R + th.px(10))),
                      Theme.GOLD, th.px(2.0), th)
        # arco activo (degradado cónico) con brillo
        span = self.SWEEP * min(1.0, v / self.VMAX)
        if span > 0.5:
            gpos = lambda val: (self.ang(val) - (self.START - self.SWEEP)) / 360.0
            g = QConicalGradient(C, self.START - self.SWEEP)
            for val, c in ((150, QColor(255, 40, 70)), (124, Theme.RED), (118, Theme.ORANGE),
                           (102, QColor(255, 196, 50)), (98, QColor(190, 235, 70)), (86, Theme.GREEN),
                           (0, QColor(0, 205, 175))):
                g.setColorAt(max(0.0, min(1.0, gpos(val))), c)
            g.setColorAt(1.0, QColor(0, 205, 175))
            a_v = int(self.ang(v) * 16)
            p.setPen(QPen(with_alpha(col, 55), th.px(12), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(rect, a_v, int(span * 16))
            p.setPen(QPen(QBrush(g), th.px(4.2), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(rect, a_v, int(span * 16))
        # aguja: trazo corto que cruza el anillo
        a = math.radians(self.ang(v))
        ca, sa = math.cos(a), -math.sin(a)
        n0, n1 = R - th.px(18), R + th.px(9)
        p.setPen(QPen(with_alpha(col, 90), th.px(7), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(cx + ca * n0, cy + sa * n0), QPointF(cx + ca * n1, cy + sa * n1))
        outlined_line(p, QPointF(cx + ca * n0, cy + sa * n0), QPointF(cx + ca * n1, cy + sa * n1),
                      QColor(255, 255, 255), th.px(2.6), th)
        # cifra central + unidades
        outlined_text(p, cx, cy - R * 0.06, f"{round(v)}", self.f(66, 800, tnum=True), Theme.TEXT, th,
                      align="center")
        outlined_text(p, cx, cy + R * 0.36, "u/s", self.f(11.5, 700, spacing=1.5), lerp_color(Theme.TEXT, col, 0.85),
                      th, align="center", outline=0.8)
        # barra fina de aceleración / boost
        bw, bh = R * 0.86, th.px(3)
        by = cy + R * 0.62
        bx = cx - bw / 2
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(4, 8, 14, 110))
        p.drawRoundedRect(QRectF(bx - th.px(1.2), by - th.px(1.2), bw + th.px(2.4), bh + th.px(2.4)), bh, bh)
        p.setBrush(QColor(255, 255, 255, 50))
        p.drawRoundedRect(QRectF(bx, by, bw, bh), bh / 2, bh / 2)
        k = max(-1.0, min(1.0, self.acc / 30.0))
        if abs(k) > 0.01:
            ln = bw / 2 * abs(k)
            c = lerp_color(Theme.ACCENT, Theme.GOLD, self.boost) if k > 0 else Theme.RED
            p.setBrush(with_alpha(c, 70))
            p.drawRoundedRect(QRectF(cx if k > 0 else cx - ln, by - bh, ln, bh * 3), bh, bh)
            p.setBrush(c)
            p.drawRoundedRect(QRectF(cx if k > 0 else cx - ln, by, ln, bh), bh / 2, bh / 2)
        p.setBrush(QColor(255, 255, 255, 210))
        p.drawRect(QRectF(cx - th.px(0.7), by - bh * 0.9, th.px(1.4), bh * 2.8))
        if self.boost > 0.02:
            p.save()
            p.setOpacity(self.th.opacity * self.boost)
            outlined_text(p, cx, by + th.px(15), "BOOST", self.f(10, 800, spacing=2.4), Theme.GOLD, th,
                          align="center", outline=0.9)
            p.restore()

    def _delta(self, p, C, R):
        th = self.th
        fl = self.flash
        fe = fl * fl * (3 - 2 * fl)
        split = fl > 0 and self.flash_diff is not None
        val = self.flash_diff if split else self.delta
        col = Theme.delta_color(round(val, 2))
        x = C.x() - R - th.px(30)
        y = C.y() - th.px(4)
        lbl = f"{self.flash_label} · SPLIT" if split else "DELTA"
        outlined_text(p, x, y - th.px(34), lbl, self.f(10.5, 800, spacing=2.0),
                      col if split else LABEL, th, align="right", outline=0.9)
        size = 40 * (1.0 + 0.12 * fe)
        outlined_text(p, x, y, nice_delta(val, 2), self.f(size, 800, tnum=True), col, th, align="right",
                      glow=col if split else None, glow_strength=fe)

    def _timer(self, p, C, R):
        th, s = self.th, self.state
        x = C.x() + R + th.px(30)
        y = C.y() - th.px(4)
        cp = min(s.checkpoint + 1, s.checkpoints_total)
        outlined_text(p, x, y - th.px(34), f"VUELTA {s.lap}/{s.laps_total}  ·  CP {cp}/{s.checkpoints_total}",
                      self.f(10.5, 800, spacing=2.0), LABEL, th, outline=0.9)
        outlined_text(p, x, y, fmt_time(s.lap_time), self.f(34, 800, tnum=True), Theme.TEXT, th)

    # ------------------------------------------------------------ opcionales
    def _nextcp(self, p, C, R):
        th, s = self.th, self.state
        cy = C.y() - R - th.px(26)
        p.save()
        p.translate(QPointF(C.x(), cy))
        p.rotate(self.nc_ang)
        u = th.px(11)
        chev = QPainterPath(QPointF(-u, u * 0.45))
        chev.lineTo(QPointF(0, -u * 0.55))
        chev.lineTo(QPointF(u, u * 0.45))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(4, 8, 14, 140), th.px(6), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                      Qt.PenJoinStyle.RoundJoin))
        p.drawPath(chev)
        p.setPen(QPen(Theme.ACCENT, th.px(3), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                      Qt.PenJoinStyle.RoundJoin))
        p.drawPath(chev)
        p.restore()
        outlined_text(p, C.x(), cy - th.px(22), f"{s.next_cp_label}  {s.next_cp_distance:.0f} m",
                      self.f(11, 800, spacing=1.5, tnum=True), Theme.TEXT, th, align="center", outline=0.9)

    def _splits(self, p, C, R):
        th, s = self.th, self.state
        rows = s.splits or []
        rh = th.px(19)
        right = C.x() - R - th.px(215)
        left = right - th.px(190)
        y0 = C.y() - rh * len(rows) / 2
        fl = self.f(10, 800, spacing=1.2)
        ft = self.f(11.5, 700, tnum=True)
        for i, sp in enumerate(rows):
            y = y0 + i * rh + rh / 2
            cur = i == s.checkpoint and not s.finished
            done = sp.time is not None
            base = Theme.ACCENT if cur else Theme.TEXT if done else Theme.TEXT_MUTED
            outlined_text(p, left, y, sp.label, fl, base, th, outline=0.8)
            t = fmt_time(sp.time) if done else (fmt_time(s.lap_time) if cur else "--:--.---")
            outlined_text(p, left + th.px(48), y, t, ft, base if not done else Theme.TEXT_DIM, th, outline=0.8)
            if done:
                outlined_text(p, right, y, nice_delta(sp.diff, 2), ft, Theme.delta_color(round(sp.diff, 3)), th,
                              align="right", outline=0.8)

    def _minimap(self, p, C, R):
        th, s = self.th, self.state
        if not s.track:
            return
        box = QRectF(C.x() + R + th.px(235), C.y() - th.px(62), th.px(200), th.px(124))
        xs = [q[0] for q in s.track]
        zs = [q[1] for q in s.track]
        k = min(box.width() / (max(xs) - min(xs)), box.height() / (max(zs) - min(zs)))
        ox = box.center().x() - (min(xs) + max(xs)) / 2 * k
        oz = box.center().y() + (min(zs) + max(zs)) / 2 * k

        def m(q):
            return QPointF(ox + q[0] * k, oz - q[1] * k)

        path = QPainterPath(m(s.track[0]))
        for q in s.track[1:]:
            path.lineTo(m(q))
        path.closeSubpath()
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(4, 8, 14, 110), th.px(5)))
        p.drawPath(path)
        p.setPen(QPen(QColor(255, 255, 255, 150), th.px(1.8)))
        p.drawPath(path)
        for i, q in enumerate(s.checkpoints_xy[:-1]):
            p.setPen(QPen(QColor(4, 8, 14, 150), th.px(1)))
            p.setBrush(Theme.ACCENT if i == s.checkpoint else QColor(255, 255, 255, 200))
            p.drawEllipse(m(q), th.px(2.6), th.px(2.6))
        for rv in s.rivals:
            p.setPen(QPen(QColor(4, 8, 14, 200), th.px(1.4)))
            p.setBrush(QColor(*rv.color))
            p.drawEllipse(m(rv.pos), th.px(4.2), th.px(4.2))
        if s.ghost_pos:
            p.setPen(QPen(QColor(255, 255, 255, 230), th.px(1.4), Qt.PenStyle.DashLine))
            p.setBrush(QColor(255, 255, 255, 50))
            p.drawEllipse(m(s.ghost_pos), th.px(4.6), th.px(4.6))
        c = m(s.player_pos)
        p.save()
        p.translate(c)
        p.rotate(-math.degrees(s.player_heading))
        u = th.px(7)
        tri = QPolygonF([QPointF(u * 1.1, 0), QPointF(-u * 0.7, u * 0.7), QPointF(-u * 0.3, 0),
                         QPointF(-u * 0.7, -u * 0.7)])
        p.setPen(QPen(QColor(4, 8, 14, 200), th.px(1.4)))
        p.setBrush(Theme.ACCENT)
        p.drawPolygon(tri)
        p.restore()

    def _toast(self, p, C, R):
        if self.toast_t <= 0 or not self.toast_text:
            return
        th = self.th
        a = min(1.0, self.toast_t / 0.6)
        p.save()
        p.setOpacity(self.th.opacity * a)
        y = C.y() - R - th.px(70 if self.opt.show_nextcp else 34)
        outlined_text(p, C.x(), y, self.toast_text, self.f(13, 800, spacing=1.6), Theme.TEXT, th, align="center")
        p.restore()

    # ------------------------------------------------------------ teclas (sólo si no es click-through)
    def keyPressEvent(self, e):
        k = e.key()
        o = self.opt
        if k == Qt.Key.Key_1:
            o.show_splits = not o.show_splits
        elif k == Qt.Key.Key_2:
            o.show_minimap = not o.show_minimap
        elif k == Qt.Key.Key_3:
            o.show_nextcp = not o.show_nextcp
        elif k == Qt.Key.Key_A:
            o.anchor = "center" if o.anchor == "bottom" else "bottom"
            o.offset_y = 0.0 if o.anchor == "center" else 250.0
        elif k == Qt.Key.Key_Up:
            o.offset_y += 10
        elif k == Qt.Key.Key_Down:
            o.offset_y -= 10
        elif k in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self.th.scale = min(4.0, self.th.scale + 0.1)
        elif k == Qt.Key.Key_Minus:
            self.th.scale = max(0.5, self.th.scale - 0.1)
        elif k == Qt.Key.Key_O:
            self.th.opacity = self.th.opacity - 0.15 if self.th.opacity > 0.4 else 1.0
        elif k in (Qt.Key.Key_Escape, Qt.Key.Key_Q):
            self.close()
        else:
            super().keyPressEvent(e)
            return
        self.update()
