"""Pantalla de fin de carrera (maqueta): tiempo final, ranking ficticio, gráfica
velocidad vs distancia (vuelta actual frente a la mejor) y botón "Subir log" sin acción."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QPushButton, QWidget

from .model import HudState, fmt_time
from .painting import draw_panel, draw_text, label, pill, setup
from .theme import Theme, with_alpha
from .widgets import AC, AL, AR, AV, nice_delta

BASE_W, BASE_H = 1040, 600


class FinishScreen(QWidget):
    def __init__(self, theme: Theme = None, click_through=False, parent=None):
        super().__init__(parent)
        self.th = theme or Theme()
        self.state = HudState()
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint
        if click_through:
            flags |= Qt.WindowType.WindowTransparentForInput
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowTitle("Fin de carrera (maqueta)")
        self.btn_upload = QPushButton("⇪  Subir log", self)
        self.btn_close = QPushButton("Cerrar", self)
        self.btn_close.clicked.connect(self.hide)
        # "Subir log": deliberadamente SIN acción en la maqueta.
        self.btn_upload.setCursor(Qt.CursorShape.PointingHandCursor)
        self.relayout()

    def f(self, px, weight=600, spacing=0.0, tnum=False):
        return self.th.font(px, weight, spacing=spacing, tnum=tnum)

    def relayout(self):
        th = self.th
        self.setFixedSize(int(th.px(BASE_W)), int(th.px(BASE_H)))
        fam = th.family
        bw, bh = th.px(170), th.px(44)
        m = th.px(12 + 30)
        y = self.height() - m - bh + th.px(8)
        self.btn_upload.setGeometry(int(self.width() - m - bw), int(y), int(bw), int(bh))
        self.btn_close.setGeometry(int(self.width() - m - 2 * bw + th.px(50) - th.px(14)), int(y),
                                   int(bw - th.px(50)), int(bh))
        r = int(bh / 2)
        fs = int(th.px(14))
        self.btn_upload.setStyleSheet(
            f"QPushButton {{ font-family: '{fam}'; font-size: {fs}px; font-weight: 800; color: #04121a;"
            f" border: none; border-radius: {r}px; letter-spacing: 1px;"
            " background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #5ee7ff, stop:1 #00b4e6); }"
            "QPushButton:hover { background: #7fefff; } QPushButton:pressed { background: #00a0cc; }")
        self.btn_close.setStyleSheet(
            f"QPushButton {{ font-family: '{fam}'; font-size: {fs}px; font-weight: 700; color: #dfe6f2;"
            f" border: 1px solid rgba(255,255,255,70); border-radius: {r}px;"
            " background: rgba(255,255,255,18); }"
            "QPushButton:hover { background: rgba(255,255,255,40); }")

    def set_state(self, s: HudState):
        self.state = s
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        setup(p)
        p.setOpacity(self.th.opacity)
        th, s = self.th, self.state
        m = th.px(12)
        R = QRectF(self.rect()).adjusted(m, m, -m, -m)
        draw_panel(p, R, th, radius=th.px(22))
        pad = th.px(30)
        x0, y0 = R.left() + pad, R.top() + pad * 0.8
        # cabecera
        g = QLinearGradient(QPointF(R.left(), 0), QPointF(R.right(), 0))
        g.setColorAt(0, with_alpha(Theme.ACCENT, 0))
        g.setColorAt(0.5, with_alpha(Theme.ACCENT, 200))
        g.setColorAt(1, with_alpha(Theme.ACCENT, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(g))
        p.drawRect(QRectF(R.left() + th.px(40), R.top(), R.width() - th.px(80), th.px(2)))
        label(p, x0, y0, th.px(400), th.px(20), "CARRERA TERMINADA", th, size=12, color=Theme.ACCENT,
              spacing=3.0, weight=800)
        draw_text(p, QRectF(x0, y0 + th.px(18), th.px(600), th.px(30)), AL | AV, s.map_name,
                  self.f(20, 700), Theme.TEXT, shadow=0.8, th=th)
        label(p, R.right() - pad - th.px(400), y0, th.px(400), th.px(20),
              f"{s.laps_total} VUELTAS · {s.checkpoints_total} CP/VUELTA", th, size=10, align=AR)
        label(p, R.right() - pad - th.px(400), y0 + th.px(20), th.px(400), th.px(26),
              "DATOS SIMULADOS · MAQUETA", th, size=9, align=AR, color=Theme.TEXT_MUTED)

        # ---------------- columna izquierda
        lw = th.px(330)
        y = y0 + th.px(70)
        label(p, x0, y, lw, th.px(18), "TIEMPO FINAL", th, size=10)
        draw_text(p, QRectF(x0, y + th.px(14), lw, th.px(66)), AL | AV, fmt_time(s.final_time),
                  self.f(54, 800, tnum=True), Theme.TEXT, shadow=1.0, th=th)
        y += th.px(88)
        cols = (("MEJOR VUELTA (CARRERA)", fmt_time(s.race_best_lap or s.best_lap), Theme.GOLD),
                ("Δ VS RÉCORD", nice_delta(s.race_best_delta, 3),
                 Theme.delta_color(s.race_best_delta)))
        for i, (k, v, c) in enumerate(cols):
            cx = x0 + i * lw / 2
            label(p, cx, y, lw / 2, th.px(16), k, th, size=9)
            draw_text(p, QRectF(cx, y + th.px(14), lw / 2, th.px(30)), AL | AV, v, self.f(19, 800, tnum=True), c,
                      shadow=0.7, th=th)
        y += th.px(62)
        # posición
        player = next((e for e in s.ranking if e.is_player), None)
        pos = player.pos if player else 0
        label(p, x0, y, lw, th.px(16), "POSICIÓN EN EL RANKING", th, size=9)
        draw_text(p, QRectF(x0, y + th.px(10), th.px(110), th.px(64)), AL | AV, f"#{pos}",
                  self.f(50, 800, tnum=True), Theme.GOLD, shadow=1.0, th=th)
        draw_text(p, QRectF(x0 + th.px(104), y + th.px(18), th.px(200), th.px(30)), AL | AV,
                  f"/ {s.ranking_total}", self.f(20, 700, tnum=True), Theme.TEXT_DIM, shadow=0.6, th=th)
        if s.ranking_total:
            pr = QRectF(x0 + th.px(108), y + th.px(48), th.px(78), th.px(20))
            pill(p, pr, Theme.GREEN, fill_alpha=50, border_alpha=160)
            draw_text(p, pr, AC | AV, f"TOP {max(1, round(100 * pos / s.ranking_total))}%",
                      self.f(10, 800, spacing=1.0), Theme.GREEN, shadow=0.0, th=th)
        y += th.px(84)
        # tabla ranking
        rh = th.px(30)
        for i, e in enumerate(s.ranking):
            rr = QRectF(x0 - th.px(8), y + i * rh, lw + th.px(8), rh - th.px(4))
            p.setPen(Qt.PenStyle.NoPen)
            if e.is_player:
                gg = QLinearGradient(rr.topLeft(), rr.topRight())
                gg.setColorAt(0, with_alpha(Theme.ACCENT, 90))
                gg.setColorAt(1, with_alpha(Theme.ACCENT, 15))
                p.setBrush(QBrush(gg))
            else:
                p.setBrush(QColor(255, 255, 255, 12))
            p.drawRoundedRect(rr, th.px(6), th.px(6))
            medal = {1: Theme.GOLD, 2: QColor(200, 210, 225), 3: QColor(214, 140, 80)}.get(e.pos, Theme.TEXT_DIM)
            fnt = self.f(13, 800 if e.is_player else 600, tnum=True)
            draw_text(p, QRectF(rr.left() + th.px(10), rr.top(), th.px(30), rr.height()), AL | AV, f"{e.pos}",
                      self.f(13, 800, tnum=True), medal, shadow=0.5, th=th)
            draw_text(p, QRectF(rr.left() + th.px(40), rr.top(), th.px(170), rr.height()), AL | AV, e.name, fnt,
                      Theme.ACCENT if e.is_player else Theme.TEXT, shadow=0.5, th=th)
            draw_text(p, QRectF(rr.left(), rr.top(), rr.width() - th.px(10), rr.height()), AR | AV,
                      fmt_time(e.time), fnt, Theme.TEXT, shadow=0.5, th=th)

        # ---------------- gráfica velocidad vs distancia
        gx = x0 + lw + th.px(40)
        gw = R.right() - pad - gx
        gy = y0 + th.px(70)
        label(p, gx, gy, gw, th.px(18), "VELOCIDAD VS DISTANCIA · ÚLTIMA VUELTA", th, size=10)
        # leyenda
        lx = gx + gw
        for name, c, dashed in (("Récord / ghost", Theme.GOLD, True), ("Última vuelta", Theme.ACCENT, False)):
            fm = self.f(10, 700)
            tw = th.px(96)
            lx -= tw + th.px(26)
            p.setPen(QPen(c, th.px(2.5), Qt.PenStyle.DashLine if dashed else Qt.PenStyle.SolidLine))
            p.drawLine(QPointF(lx, gy + th.px(9)), QPointF(lx + th.px(20), gy + th.px(9)))
            draw_text(p, QRectF(lx + th.px(26), gy, tw, th.px(18)), AL | AV, name, fm, Theme.TEXT, shadow=0.4, th=th)
        plot = QRectF(gx + th.px(38), gy + th.px(34), gw - th.px(44), th.px(330))
        self._plot(p, plot, s)

    def _plot(self, p, r, s):
        th = self.th
        vmin, vmax = 60.0, 150.0
        L = max(1.0, s.lap_length)

        def X(d):
            return r.left() + r.width() * d / L

        def Y(v):
            return r.bottom() - r.height() * (max(vmin, min(vmax, v)) - vmin) / (vmax - vmin)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 60))
        p.drawRoundedRect(r.adjusted(-th.px(6), -th.px(6), th.px(6), th.px(6)), th.px(8), th.px(8))
        # zonas de color de fondo
        for a, b, c in ((99, 120, Theme.ORANGE), (120, 150, Theme.RED)):
            p.setBrush(with_alpha(c, 16))
            p.drawRect(QRectF(r.left(), Y(b), r.width(), Y(a) - Y(b)))
        ft = self.f(9.5, 600, tnum=True)
        for v in range(60, 151, 15):
            p.setPen(QPen(QColor(255, 255, 255, 22), th.px(1)))
            p.drawLine(QPointF(r.left(), Y(v)), QPointF(r.right(), Y(v)))
            draw_text(p, QRectF(r.left() - th.px(40), Y(v) - th.px(8), th.px(34), th.px(16)), AR | AV, str(v), ft,
                      Theme.TEXT_MUTED, shadow=0, th=th)
        # checkpoints
        cps = [sp for sp in s.splits]
        cp_d = s.cp_distances
        for i, d in enumerate(cp_d):
            p.setPen(QPen(QColor(255, 255, 255, 30), th.px(1), Qt.PenStyle.DotLine))
            p.drawLine(QPointF(X(d), r.top()), QPointF(X(d), r.bottom()))
            lbl = cps[i].label if i < len(cps) else ""
            draw_text(p, QRectF(X(d) - th.px(30), r.bottom() + th.px(4), th.px(30), th.px(14)), AR | AV,
                      lbl, self.f(8.5, 700), Theme.TEXT_MUTED, shadow=0, th=th)
        for km in range(int(L // 1000) + 1):
            draw_text(p, QRectF(X(km * 1000) - th.px(20), r.bottom() + th.px(18), th.px(40), th.px(14)), AC | AV,
                      f"{km} km", ft, Theme.TEXT_MUTED, shadow=0, th=th)
        # línea boost 99
        p.setPen(QPen(with_alpha(Theme.GOLD, 150), th.px(1.2), Qt.PenStyle.DashLine))
        p.drawLine(QPointF(r.left(), Y(99)), QPointF(r.right(), Y(99)))
        # etiqueta sobre el valle de velocidad (zona donde las curvas quedan por debajo de 99)
        ref = s.best_trace or s.trace
        d_low = min(ref, key=lambda q: q[1])[0] if ref else L / 2
        lx = max(r.left() + th.px(4), min(r.right() - th.px(124), X(d_low) - th.px(60)))
        draw_text(p, QRectF(lx, Y(99) - th.px(16), th.px(120), th.px(14)), AC | AV, "BOOST 99",
                  self.f(8.5, 800, spacing=1.0), Theme.GOLD, shadow=0.5, th=th)

        def path_of(pts):
            path = QPainterPath()
            for i, (d, v) in enumerate(pts):
                (path.moveTo if i == 0 else path.lineTo)(QPointF(X(d), Y(v)))
            return path

        if s.trace:
            cur = path_of(s.trace)
            area = QPainterPath(cur)
            area.lineTo(QPointF(X(s.trace[-1][0]), r.bottom()))
            area.lineTo(QPointF(X(s.trace[0][0]), r.bottom()))
            area.closeSubpath()
            g = QLinearGradient(QPointF(0, r.top()), QPointF(0, r.bottom()))
            g.setColorAt(0, with_alpha(Theme.ACCENT, 90))
            g.setColorAt(1, with_alpha(Theme.ACCENT, 0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(g))
            p.drawPath(area)
        if s.best_trace:
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(with_alpha(Theme.GOLD, 230), th.px(2.0), Qt.PenStyle.DashLine))
            p.drawPath(path_of(s.best_trace))
        if s.trace:
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(with_alpha(Theme.ACCENT, 80), th.px(6)))
            p.drawPath(cur)
            p.setPen(QPen(Theme.ACCENT, th.px(2.4)))
            p.drawPath(cur)
