"""Selector de mapa minimalista (Qt): buscador con filtro, lista agrupada por copa,
online/local, indicación del mapa actual, navegación con teclado; se cierra al elegir.

No carga checkpoints: emite ``mapChosen(MapEntry)``; quien lo use decide qué hacer
(en la app real: lo mismo que ``saveGuildhall``).
"""

import threading

from PySide6.QtCore import QObject, QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFontMetricsF, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStyle,
    QStyledItemDelegate,
    QWidget,
)

from .map_catalog import Catalog, MapEntry, current_selection, load_catalog, normalize
from .painting import draw_panel, draw_text, pill, setup
from .theme import Theme, with_alpha
from .widgets import AC, AL, AR, AV

ROLE = Qt.ItemDataRole.UserRole + 1


class _Loader(QObject):
    loaded = Signal(object)


def _search_icon(px, color):
    pm = QPixmap(int(px), int(px))
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(color, px * 0.11, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    r = px * 0.28
    c = QPointF(px * 0.44, px * 0.44)
    p.drawEllipse(c, r, r)
    p.drawLine(QPointF(px * 0.64, px * 0.64), QPointF(px * 0.84, px * 0.84))
    p.end()
    return QIcon(pm)


class _Delegate(QStyledItemDelegate):
    def __init__(self, sel):
        super().__init__(sel)
        self.sel = sel

    def sizeHint(self, option, index):
        d = index.data(ROLE) or {}
        th = self.sel.th
        return QSize(100, int(th.px(34 if d.get("kind") == "header" else 36)))

    def paint(self, p, option, index):
        d = index.data(ROLE) or {}
        th = self.sel.th
        p.save()
        setup(p)
        r = QRectF(option.rect).adjusted(th.px(2), th.px(1.5), -th.px(8), -th.px(1.5))
        if d.get("kind") == "header":
            col = Theme.ACCENT if d["source"] == "online" else Theme.GOLD
            draw_text(p, r.adjusted(th.px(10), th.px(8), 0, 0), AL | AV, d["title"],
                      th.font(10, 800, spacing=1.8), col, shadow=0, th=th)
            fm = QFontMetricsF(th.font(10, 800, spacing=1.8))
            tw = fm.horizontalAdvance(d["title"])
            draw_text(p, r.adjusted(th.px(18) + tw, th.px(8), 0, 0), AL | AV, str(d["count"]),
                      th.font(9.5, 700, tnum=True), Theme.TEXT_MUTED, shadow=0, th=th)
            p.setPen(QPen(QColor(255, 255, 255, 18), th.px(1)))
            y = r.center().y() + th.px(4)
            p.drawLine(QPointF(r.left() + th.px(28) + tw + th.px(16), y), QPointF(r.right() - th.px(6), y))
            p.restore()
            return
        e: MapEntry = d["entry"]
        is_cur = bool(option.state & QStyle.StateFlag.State_Selected)
        hover = bool(option.state & QStyle.StateFlag.State_MouseOver) and self.sel.list.underMouse()
        active = self.sel.is_selected(e)
        if is_cur or hover:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(with_alpha(Theme.ACCENT, 46 if is_cur else 20))
            p.drawRoundedRect(r, th.px(9), th.px(9))
        if active:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(Theme.ACCENT)
            p.drawRoundedRect(QRectF(r.left() + th.px(3), r.top() + th.px(8), th.px(3), r.height() - th.px(16)),
                              th.px(1.5), th.px(1.5))
        # nombre con coincidencias resaltadas
        f_norm = th.font(13, 700 if (is_cur or active) else 600)
        f_hit = th.font(13, 800)
        x = r.left() + th.px(16)
        y = r.top()
        avail = r.width() - th.px(16) - th.px(110)
        name = QFontMetricsF(f_norm).elidedText(e.name, Qt.TextElideMode.ElideRight, avail)
        spans = self.sel.highlight_spans(name)
        base_col = Theme.TEXT if (is_cur or active) else QColor(214, 222, 236)
        for text, hit in spans:
            f = f_hit if hit else f_norm
            draw_text(p, QRectF(x, y, avail, r.height()), AL | AV, text, f,
                      Theme.ACCENT if hit else base_col, shadow=0, th=th)
            x += QFontMetricsF(f).horizontalAdvance(text)
        # copa (en búsqueda) + insignias
        right = r.right() - th.px(10)
        if active:
            br = QRectF(right - th.px(72), r.center().y() - th.px(10), th.px(72), th.px(20))
            pill(p, br, Theme.ACCENT, fill_alpha=60, border_alpha=200)
            draw_text(p, br, AC | AV, "✓ ACTUAL", th.font(9, 800, spacing=1.0), Theme.TEXT, shadow=0, th=th)
            right -= th.px(80)
        src = "LOCAL" if e.source == "local" else ""
        if src:
            fm = QFontMetricsF(th.font(8.5, 700, spacing=0.8))
            tw = min(th.px(150), fm.horizontalAdvance(src) + th.px(14))
            br = QRectF(right - tw, r.center().y() - th.px(9), tw, th.px(18))
            c = Theme.GOLD if e.source == "local" else Theme.TEXT_MUTED
            pill(p, br, c, fill_alpha=18, border_alpha=90)
            draw_text(p, br, AC | AV, fm.elidedText(src, Qt.TextElideMode.ElideRight, tw - th.px(10)),
                      th.font(8.5, 700, spacing=0.8), c, shadow=0, th=th)
        p.restore()


class MapSelector(QWidget):
    mapChosen = Signal(object)

    BASE_W, BASE_H = 600, 660

    def __init__(self, theme: Theme = None, hotkey_label="Ctrl+Shift+M", parent=None):
        super().__init__(parent)
        base = theme or Theme()
        self.th = Theme(scale=base.scale, opacity=1.0, bg_alpha=0.86)
        self.hotkey_label = hotkey_label
        self.catalog: Catalog = Catalog([], "offline", "cargando…")
        self.selected = current_selection()
        self.query = ""
        self.tokens = []
        self.source_filter = "all"
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
                            | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowTitle("Seleccionar mapa (maqueta)")
        th = self.th
        fam = th.family
        self.search = QLineEdit(self)
        self.search.setPlaceholderText("Buscar mapa o copa…  (p. ej. «drft», «tyria»)")
        self.search.addAction(_search_icon(th.px(20), Theme.TEXT_DIM), QLineEdit.ActionPosition.LeadingPosition)
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._on_query)
        self.search.installEventFilter(self)
        r = int(th.px(12))
        self.search.setStyleSheet(
            f"QLineEdit {{ font-family:'{fam}'; font-size:{int(th.px(15))}px; font-weight:600; color:#eef3fa;"
            f" background: rgba(255,255,255,16); border:1px solid rgba(255,255,255,40); border-radius:{r}px;"
            f" padding: 0 {int(th.px(10))}px; selection-background-color: #00a6cc; }}"
            "QLineEdit:focus { border:1px solid rgba(0,212,255,170); background: rgba(255,255,255,22); }")
        self.chips = QButtonGroup(self)
        self.chip_btns = {}
        for i, (key, text) in enumerate((("all", "Todos"), ("online", "Online"), ("local", "Locales"))):
            b = QPushButton(text, self)
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.setStyleSheet(
                f"QPushButton {{ font-family:'{fam}'; font-size:{int(th.px(11.5))}px; font-weight:700;"
                f" color:#97a3b8; background: transparent; border:1px solid rgba(255,255,255,34);"
                f" border-radius:{int(th.px(13))}px; padding: 0 {int(th.px(12))}px; }}"
                "QPushButton:hover { color:#eef3fa; border-color: rgba(255,255,255,80); }"
                "QPushButton:checked { color:#04121a; background:#00d4ff; border-color:#00d4ff; }")
            b.clicked.connect(lambda _=False, k=key: self._set_source(k))
            self.chips.addButton(b, i)
            self.chip_btns[key] = b
        self.chip_btns["all"].setChecked(True)
        self.list = QListWidget(self)
        self.list.setItemDelegate(_Delegate(self))
        self.list.setMouseTracking(True)
        self.list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setStyleSheet(
            "QListWidget { background: transparent; border: none; outline: none; }"
            "QListWidget::item { border: none; }"
            f"QScrollBar:vertical {{ background: transparent; width:{int(th.px(6))}px; margin: 4px 0; }}"
            f"QScrollBar::handle:vertical {{ background: rgba(255,255,255,55); border-radius:{int(th.px(3))}px;"
            " min-height: 30px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }")
        self.list.itemClicked.connect(self._on_click)
        self._loader = _Loader()
        self._loader.loaded.connect(self.set_catalog)
        self.relayout()

    # ------------------------------------------------------------ layout / pintado
    def relayout(self):
        th = self.th
        self.setFixedSize(int(th.px(self.BASE_W)), int(th.px(self.BASE_H)))
        m, pad = th.px(14), th.px(24)
        x, w = m + pad, self.width() - 2 * (m + pad)
        self.search.setGeometry(int(x), int(m + th.px(86)), int(w), int(th.px(46)))
        cx = x
        for key in ("all", "online", "local"):
            b = self.chip_btns[key]
            b.adjustSize()
            bw = max(b.sizeHint().width(), th.px(70))
            b.setGeometry(int(cx), int(m + th.px(146)), int(bw), int(th.px(27)))
            cx += bw + th.px(8)
        top = m + th.px(186)
        self.list.setGeometry(int(x - th.px(6)), int(top), int(w + th.px(12)),
                              int(self.height() - m - th.px(62) - top))

    def paintEvent(self, _e):
        p = QPainter(self)
        setup(p)
        th = self.th
        m, pad = th.px(14), th.px(24)
        R = QRectF(self.rect()).adjusted(m, m, -m, -m)
        draw_panel(p, R, th, radius=th.px(20))
        x, w = R.left() + pad, R.width() - 2 * pad
        draw_text(p, QRectF(x, R.top() + th.px(18), w, th.px(30)), AL | AV, "Seleccionar mapa",
                  th.font(21, 800), Theme.TEXT, shadow=0.6, th=th)
        kr = QRectF(R.right() - pad - th.px(112), R.top() + th.px(22), th.px(112), th.px(22))
        pill(p, kr, Theme.TEXT_DIM, fill_alpha=14, border_alpha=70)
        draw_text(p, kr, AC | AV, self.hotkey_label, th.font(9.5, 700, spacing=0.6), Theme.TEXT_DIM, shadow=0, th=th)
        # estado de la fuente de datos
        dot = {"live": Theme.GREEN, "snapshot": Theme.GOLD}.get(self.catalog.origin, Theme.TEXT_MUTED)
        cy = R.top() + th.px(60)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(with_alpha(dot, 60))
        p.drawEllipse(QPointF(x + th.px(4), cy), th.px(6), th.px(6))
        p.setBrush(dot)
        p.drawEllipse(QPointF(x + th.px(4), cy), th.px(3.2), th.px(3.2))
        draw_text(p, QRectF(x + th.px(16), cy - th.px(10), w, th.px(20)), AL | AV, self.catalog.detail,
                  th.font(11, 600), Theme.TEXT_DIM, shadow=0, th=th)
        # contador de resultados a la derecha de los chips
        n = self._visible_count
        draw_text(p, QRectF(x, R.top() + th.px(146) - m + th.px(14), w, th.px(27)), AR | AV,
                  f"{n} resultado{'s' if n != 1 else ''}", th.font(10.5, 700, tnum=True), Theme.TEXT_MUTED,
                  shadow=0, th=th)
        # pie: mapa actual + atajos
        fy = R.bottom() - th.px(48)
        p.setPen(QPen(QColor(255, 255, 255, 20), th.px(1)))
        p.drawLine(QPointF(x, fy), QPointF(x + w, fy))
        cur = f"{self.selected.name}  ·  {self.selected.cup}" if self.selected else "ninguno"
        draw_text(p, QRectF(x, fy + th.px(6), w * 0.55, th.px(34)), AL | AV, "ACTUAL",
                  th.font(9, 800, spacing=1.6), Theme.TEXT_MUTED, shadow=0, th=th)
        fm = QFontMetricsF(th.font(11, 700))
        draw_text(p, QRectF(x + th.px(58), fy + th.px(6), w * 0.55, th.px(34)), AL | AV,
                  fm.elidedText(cur, Qt.TextElideMode.ElideRight, w * 0.5), th.font(11, 700), Theme.ACCENT,
                  shadow=0, th=th)
        draw_text(p, QRectF(x, fy + th.px(6), w, th.px(34)), AR | AV, "↑↓ navegar   ⏎ elegir   Esc cerrar",
                  th.font(10, 700), Theme.TEXT_MUTED, shadow=0, th=th)
        p.end()

    # ------------------------------------------------------------ datos
    _visible_count = 0

    def start_loading(self, online=True):
        def run():
            self._loader.loaded.emit(load_catalog(online))

        threading.Thread(target=run, daemon=True, name="map-catalog").start()

    def set_catalog(self, catalog: Catalog):
        self.catalog = catalog
        self._populate()

    def is_selected(self, e: MapEntry):
        s = self.selected
        return bool(s) and s.name == e.name and (s.cup == e.cup or s.source == e.source == "local")

    def highlight_spans(self, text):
        if not self.tokens:
            return [(text, False)]
        low = text.casefold()
        if len(low) != len(text):
            return [(text, False)]
        marks = [False] * len(text)
        nlow = normalize(text)
        src = nlow if len(nlow) == len(text) else low
        for tok in self.tokens:
            i = src.find(tok)
            while i >= 0 and tok:
                for k in range(i, i + len(tok)):
                    marks[k] = True
                i = src.find(tok, i + len(tok))
        spans, cur, hit = [], "", marks[0] if marks else False
        for ch, mk in zip(text, marks):
            if mk != hit and cur:
                spans.append((cur, hit))
                cur = ""
            hit = mk
            cur += ch
        if cur:
            spans.append((cur, hit))
        return spans

    def _matches(self, e: MapEntry):
        if self.source_filter != "all" and e.source != self.source_filter:
            return False
        if not self.tokens:
            return True
        hay = normalize(e.name + " " + e.cup)
        return all(t in hay for t in self.tokens)

    def _populate(self):
        self.list.clear()
        first, sel_item, sel_header, count = None, None, None, 0
        for g in self.catalog.groups:
            items = [e for e in g.maps if self._matches(e)]
            if not items:
                continue
            h = QListWidgetItem()
            h.setData(ROLE, {"kind": "header", "title": g.title, "count": len(items), "source": g.source})
            h.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list.addItem(h)
            for e in items:
                it = QListWidgetItem()
                it.setData(ROLE, {"kind": "map", "entry": e})
                it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.list.addItem(it)
                count += 1
                first = first or it
                if sel_item is None and self.is_selected(e):
                    sel_item, sel_header = it, h
        self._visible_count = count
        target = first if self.tokens else (sel_item or first)
        if target is not None:
            self.list.setCurrentItem(target)
            if target is sel_item:  # mostrar la cabecera de su copa arriba y el mapa actual visible
                self.list.scrollToItem(sel_header, QListWidget.ScrollHint.PositionAtTop)
                self.list.scrollToItem(sel_item, QListWidget.ScrollHint.EnsureVisible)
            else:
                self.list.scrollToTop()
        self.update()

    def _on_query(self, text):
        self.query = text.strip()
        self.tokens = [normalize(t) for t in self.query.split() if t]
        self._populate()

    def _set_source(self, key):
        self.source_filter = key
        self._populate()

    # ------------------------------------------------------------ interacción
    def _move(self, step):
        n = self.list.count()
        if not n:
            return
        d = 1 if step > 0 else -1
        target = max(0, min(n - 1, self.list.currentRow() + step))
        fwd = range(target, n if d > 0 else -1, d)
        back = range(target, -1 if d > 0 else n, -d)
        for rng in (fwd, back):
            for r in rng:
                it = self.list.item(r)
                if it.flags() & Qt.ItemFlag.ItemIsSelectable:
                    self.list.setCurrentItem(it)
                    self.list.scrollToItem(it)
                    return

    def eventFilter(self, obj, ev):
        if obj is self.search and ev.type() == ev.Type.KeyPress:
            k = ev.key()
            if k == Qt.Key.Key_Down:
                self._move(1)
                return True
            if k == Qt.Key.Key_Up:
                self._move(-1)
                return True
            if k == Qt.Key.Key_PageDown:
                self._move(8)
                return True
            if k == Qt.Key.Key_PageUp:
                self._move(-8)
                return True
            if k in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                it = self.list.currentItem()
                if it is not None:
                    self._on_click(it)
                return True
            if k == Qt.Key.Key_Escape:
                self.hide()
                return True
        return super().eventFilter(obj, ev)

    def _on_click(self, it):
        d = it.data(ROLE) or {}
        if d.get("kind") != "map":
            return
        self.selected = d["entry"]
        self.mapChosen.emit(d["entry"])
        self.hide()

    def open(self, screen=None):
        scr = screen or self.screen()
        if scr is not None:
            g = scr.availableGeometry()
            self.move(int(g.center().x() - self.width() / 2), int(g.top() + g.height() * 0.06))
        self.search.clear()
        self.show()
        self.raise_()
        self.activateWindow()
        self.search.setFocus()

    def toggle(self):
        if self.isVisible():
            self.hide()
        else:
            self.open()
