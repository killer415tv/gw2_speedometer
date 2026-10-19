"""Ventana overlay del HUD: frameless, translúcida, siempre encima, click-through opcional."""

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QWidget

from .model import HudState
from .theme import Theme
from .widgets import (
    DeltaPanel,
    LapTimer,
    MiniMap,
    NextCheckpoint,
    Speedometer,
    SplitsTable,
)

# Tamaños base (escala 1.0 = 1080p). Incluyen el margen de sombra de cada panel.
FULL = {"speedo_w": 330, "mid_w": 284, "right_w": 268, "timer_h": 120, "delta_h": 122, "map_h": 196}
COMPACT = {"speedo_w": 246, "mid_w": 224}


class HudWindow(QWidget):
    def __init__(self, theme: Theme = None, click_through=False, on_top=True, parent=None):
        super().__init__(parent)
        self.th = theme or Theme()
        self._drag = None
        self._click_through = click_through
        self._on_top = on_top
        self._apply_flags()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setWindowTitle("GW2 Speedometer HUD (maqueta Qt)")
        self.speedo = Speedometer(self.th, self)
        self.timer = LapTimer(self.th, self)
        self.delta = DeltaPanel(self.th, self)
        self.nextcp = NextCheckpoint(self.th, self)
        self.splits = SplitsTable(self.th, self)
        self.minimap = MiniMap(self.th, self)
        self.panels = [self.speedo, self.timer, self.delta, self.nextcp, self.splits, self.minimap]
        self.relayout()

    # -------------------------------------------------------------- opciones
    def _apply_flags(self):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self._on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        if self._click_through:
            flags |= Qt.WindowType.WindowTransparentForInput
        self.setWindowFlags(flags)

    def set_click_through(self, enabled: bool):
        self._click_through = enabled
        vis = self.isVisible()
        self._apply_flags()
        if vis:
            self.show()

    def set_compact(self, compact: bool):
        self.th.compact = compact
        self.relayout()

    def set_scale(self, scale: float):
        self.th.scale = max(0.5, min(4.0, scale))
        self.relayout()

    def set_opacity(self, opacity: float):
        self.th.opacity = max(0.15, min(1.0, opacity))
        self.update_all()

    def set_bg_alpha(self, a: float):
        self.th.bg_alpha = max(0.0, min(1.0, a))
        self.update_all()

    # -------------------------------------------------------------- layout
    def relayout(self):
        th = self.th
        px = th.px
        if th.compact:
            L = COMPACT
            sw = px(L["speedo_w"])
            sh = Speedometer.height_for_width(sw, th, compact=True)
            mw = px(L["mid_w"])
            self.speedo.setGeometry(0, 0, int(sw), int(sh))
            hh = sh / 3
            self.timer.setGeometry(int(sw), 0, int(mw), int(hh))
            self.delta.setGeometry(int(sw), int(hh), int(mw), int(hh))
            self.nextcp.setGeometry(int(sw), int(2 * hh), int(mw), int(sh - 2 * hh))
            self.splits.hide()
            self.minimap.hide()
            self.setFixedSize(int(sw + mw), int(sh))
        else:
            L = FULL
            sw = px(L["speedo_w"])
            sh = Speedometer.height_for_width(sw, th)
            mw, rw = px(L["mid_w"]), px(L["right_w"])
            th1, th2 = px(L["timer_h"]), px(L["delta_h"])
            self.speedo.setGeometry(0, 0, int(sw), int(sh))
            self.timer.setGeometry(int(sw), 0, int(mw), int(th1))
            self.delta.setGeometry(int(sw), int(th1), int(mw), int(th2))
            self.nextcp.setGeometry(int(sw), int(th1 + th2), int(mw), int(sh - th1 - th2))
            mh = px(L["map_h"])
            self.minimap.setGeometry(int(sw + mw), 0, int(rw), int(mh))
            self.splits.setGeometry(int(sw + mw), int(mh), int(rw), int(sh - mh))
            self.splits.show()
            self.minimap.show()
            self.setFixedSize(int(sw + mw + rw), int(sh))
        self.update_all()

    # -------------------------------------------------------------- datos
    def update_state(self, s: HudState):
        for w in self.panels:
            w.set_state(s)

    def tick(self, dt: float):
        for w in self.panels:
            w.tick(dt)
        self.update_all()

    def update_all(self):
        for w in self.panels:
            w.update()
        self.update()

    # -------------------------------------------------------------- interacción
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag is not None:
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, _e):
        self._drag = None

    def keyPressEvent(self, e):
        k = e.key()
        if k == Qt.Key.Key_C:
            self.set_compact(not self.th.compact)
        elif k in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self.set_scale(self.th.scale + 0.1)
        elif k == Qt.Key.Key_Minus:
            self.set_scale(self.th.scale - 0.1)
        elif k == Qt.Key.Key_O:
            self.set_opacity(self.th.opacity - 0.15 if self.th.opacity > 0.4 else 1.0)
        elif k == Qt.Key.Key_B:
            self.set_bg_alpha(self.th.bg_alpha - 0.2 if self.th.bg_alpha > 0.25 else 0.85)
        elif k == Qt.Key.Key_T:
            self.set_click_through(True)  # ¡ya no recibirá teclas! salir con Ctrl+C en la terminal
        elif k in (Qt.Key.Key_Escape, Qt.Key.Key_Q):
            self.close()
        else:
            super().keyPressEvent(e)

    def place_bottom_left(self, margin=40):
        scr = self.screen().availableGeometry() if self.screen() else None
        if scr:
            self.move(QPoint(scr.left() + margin, scr.bottom() - self.height() - margin))
