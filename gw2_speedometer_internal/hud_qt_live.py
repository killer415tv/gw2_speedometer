"""Qt HUD process for ``speedometer.py --qt-hud`` (started by qt_hud_bridge.py).

Shows the minimal transparent HUD (hud_qt.minimal) with the REAL values that
speedometer.py measures, received as JSON datagrams on 127.0.0.1, and the map
selector (hud_qt.map_selector).  It never reads MumbleLink, never writes logs,
cup.txt or guildhall.txt: choosing a map only sends the choice back to the
speedometer, which applies it through its own Tk menus code.

Hotkeys (global, pynput):  Ctrl+Shift+M  map selector
                           Ctrl+Shift+O  show/hide optional widgets (splits, next CP, minimap)
Closing this process (tray icon > Close, or killing it) never stops the
measurement: the speedometer shows its classic Tk HUD again.

Started by the speedometer as::

    python hud_qt_live.py --port <udp port of the speedometer> --parent-pid <pid>
    (token in the GW2_QT_HUD_TOKEN environment variable)
"""

import argparse
import contextlib
import ctypes
import os
import socket
import sys
import time
from dataclasses import fields

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from qt_hud_bridge import ENV_TOKEN, LOCALHOST, decode, encode  # (no Qt, no Tk)

IS_WINDOWS = sys.platform == "win32"


# ----------------------------------------------------------------- protocol ---
class ClientLink:
    """UDP endpoint of the HUD process (non-blocking, drops when it cannot send)."""

    def __init__(self, port, token):
        self.server = (LOCALHOST, int(port))
        self.token = token
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((LOCALHOST, 0))
        self.sock.setblocking(False)
        if IS_WINDOWS and hasattr(socket, "SIO_UDP_CONNRESET"):
            try:
                self.sock.ioctl(socket.SIO_UDP_CONNRESET, False)
            except (OSError, ValueError):
                pass
        self.seq = 0

    def send(self, msg_type, payload=None):
        self.seq += 1
        try:
            self.sock.sendto(encode(msg_type, self.token, payload, self.seq), self.server)
            return True
        except (BlockingIOError, InterruptedError, OSError):
            return False

    def poll(self, max_msgs=64):
        out = []
        for _ in range(max_msgs):
            try:
                data, addr = self.sock.recvfrom(65535)
            except (BlockingIOError, InterruptedError):
                break
            except ConnectionResetError:
                continue
            except OSError:
                break
            if addr != self.server:
                continue
            msg = decode(data, self.token)
            if msg is not None:
                out.append(msg)
        return out


def state_from_dict(d, static=None):
    """HudState from a ``state`` payload (+ ``map`` payload for the static parts)."""
    from hud_qt.model import HudState, Split

    names = {f.name for f in fields(HudState)}
    kw = {}
    for k, v in (d or {}).items():
        if k in names and k != "splits":
            kw[k] = v
    for k in ("player_pos", "ghost_pos"):
        if kw.get(k) is not None:
            kw[k] = tuple(kw[k])
    if static:
        kw["track"] = [tuple(p) for p in static.get("track", [])]
        kw["checkpoints_xy"] = [tuple(p) for p in static.get("checkpoints_xy", [])]
    s = HudState(**kw)
    s.splits = [Split(label, t, diff) for label, t, diff in (d or {}).get("splits", [])]
    return s


# ---------------------------------------------------------- process helpers ---
_WIN = None


def _win():
    """kernel32/user32 with explicit prototypes (64-bit safe handles), cached."""
    global _WIN
    if _WIN is None:
        from ctypes import wintypes as w

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        u32 = ctypes.WinDLL("user32", use_last_error=True)
        k32.OpenProcess.restype = w.HANDLE
        k32.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
        k32.WaitForSingleObject.restype = w.DWORD
        k32.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
        k32.CloseHandle.argtypes = [w.HANDLE]
        k32.GetCurrentThreadId.restype = w.DWORD
        get = getattr(u32, "GetWindowLongPtrW", u32.GetWindowLongW)
        put = getattr(u32, "SetWindowLongPtrW", u32.SetWindowLongW)
        get.restype = ctypes.c_ssize_t
        get.argtypes = [w.HWND, ctypes.c_int]
        put.restype = ctypes.c_ssize_t
        put.argtypes = [w.HWND, ctypes.c_int, ctypes.c_ssize_t]
        u32.SetWindowPos.restype = w.BOOL
        u32.SetWindowPos.argtypes = [w.HWND, w.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                     ctypes.c_int, ctypes.c_uint]
        u32.GetForegroundWindow.restype = w.HWND
        u32.GetWindowThreadProcessId.restype = w.DWORD
        u32.GetWindowThreadProcessId.argtypes = [w.HWND, ctypes.c_void_p]
        u32.AttachThreadInput.restype = w.BOOL
        u32.AttachThreadInput.argtypes = [w.DWORD, w.DWORD, w.BOOL]
        u32.BringWindowToTop.argtypes = [w.HWND]
        u32.SetForegroundWindow.argtypes = [w.HWND]
        _WIN = (k32, u32, get, put)
    return _WIN


def parent_alive(pid):
    if not pid:
        return True
    if IS_WINDOWS:
        k32 = _win()[0]
        SYNCHRONIZE, QUERY_LIMITED = 0x00100000, 0x1000
        h = k32.OpenProcess(SYNCHRONIZE | QUERY_LIMITED, False, int(pid))
        if not h:
            return ctypes.get_last_error() == 5  # access denied -> it exists
        try:
            return k32.WaitForSingleObject(h, 0) == 0x102  # WAIT_TIMEOUT = still running
        finally:
            k32.CloseHandle(h)
    try:
        os.kill(int(pid), 0)  # POSIX only: signal 0 = existence check (never on Windows)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


# ---------------------------------------------------------------- Windows -----
def win_overlay_styles(widget):
    """Belt and braces for the click-through overlay on Windows.

    Qt already sets WS_EX_LAYERED (per-pixel alpha of WA_TranslucentBackground)
    and WS_EX_TRANSPARENT (WindowTransparentForInput).  Add WS_EX_NOACTIVATE and
    WS_EX_TOOLWINDOW (never takes focus from GW2, not in Alt+Tab), and
    WS_EX_TRANSPARENT if missing, but ONLY on a layered window: making a
    non-layered window layered without SetLayeredWindowAttributes hides it.
    """
    if not IS_WINDOWS:
        return None
    try:
        _k32, _u32, get, put = _win()
        hwnd = int(widget.winId())
        GWL_EXSTYLE = -20
        LAYERED, TRANSPARENT, TOOLWINDOW, NOACTIVATE = 0x80000, 0x20, 0x80, 0x08000000
        ex = get(hwnd, GWL_EXSTYLE)
        if ex & LAYERED:
            new = ex | TRANSPARENT | TOOLWINDOW | NOACTIVATE
            if new != ex:
                put(hwnd, GWL_EXSTYLE, new)
        print(f"[qt-hud] overlay exstyle {ex:#x} -> {get(hwnd, GWL_EXSTYLE):#x}")
        return ex
    except Exception as exc:  # noqa: BLE001
        print("[qt-hud] could not adjust window styles:", exc)
        return None


def win_keep_topmost(widget):
    """Re-assert HWND_TOPMOST without activating (games sometimes push overlays down)."""
    if not IS_WINDOWS or not widget.isVisible():
        return
    with contextlib.suppress(Exception):
        u32 = _win()[1]
        HWND_TOPMOST = -1
        SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE = 0x1, 0x2, 0x10
        u32.SetWindowPos(int(widget.winId()), HWND_TOPMOST, 0, 0, 0, 0,
                         SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE)


def win_force_foreground(widget):
    """Bring the selector to the front while GW2 has the focus (foreground lock)."""
    if not IS_WINDOWS:
        return
    with contextlib.suppress(Exception):
        k32, u32, _get, _put = _win()
        hwnd = int(widget.winId())
        fg = u32.GetForegroundWindow()
        fg_thread = u32.GetWindowThreadProcessId(fg, None) if fg else 0
        me = k32.GetCurrentThreadId()
        attached = bool(fg_thread and fg_thread != me and u32.AttachThreadInput(me, fg_thread, True))
        try:
            u32.BringWindowToTop(hwnd)
            u32.SetForegroundWindow(hwnd)
        finally:
            if attached:
                u32.AttachThreadInput(me, fg_thread, False)


# ---------------------------------------------------------------- hotkeys -----
class Hotkeys:
    """Global Ctrl+Shift+<letter> hotkeys with pynput (works while GW2 has focus).

    Matches the letter by virtual-key code as well as by char: with Ctrl held,
    Windows reports e.g. Ctrl+M as the control character '\\r', so pynput's
    GlobalHotKeys string matching is not reliable there.
    """

    def __init__(self, bindings):
        self.bindings = {k.lower(): fn for k, fn in bindings.items()}  # letter -> callable
        self.mods = set()
        self.listener = None

    @staticmethod
    def letter_of(key):
        vk = getattr(key, "vk", None)
        if isinstance(vk, int) and (0x41 <= vk <= 0x5A or 0x61 <= vk <= 0x7A):
            return chr(vk).lower()
        ch = getattr(key, "char", None)
        if isinstance(ch, str) and len(ch) == 1:
            if 1 <= ord(ch) <= 26:
                return chr(ord(ch) + 96)  # control character (Ctrl+letter)
            return ch.lower()
        return None

    def _mod(self, key):
        name = getattr(key, "name", "") or ""
        if name.startswith("ctrl"):
            return "ctrl"
        if name.startswith("shift"):
            return "shift"
        return None

    def on_press(self, key):
        m = self._mod(key)
        if m:
            self.mods.add(m)
            return
        if {"ctrl", "shift"} <= self.mods:
            fn = self.bindings.get(self.letter_of(key) or "")
            if fn is not None:
                fn()

    def on_release(self, key):
        m = self._mod(key)
        if m:
            self.mods.discard(m)

    def start(self):
        try:
            from pynput import keyboard
        except Exception as exc:  # noqa: BLE001 - optional
            print("[qt-hud] pynput not available, no global hotkeys:", exc)
            return False
        try:
            self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
            self.listener.daemon = True
            self.listener.start()
        except Exception as exc:  # noqa: BLE001 - e.g. no X display access
            print("[qt-hud] global hotkeys unavailable:", exc)
            return False
        return True


# -------------------------------------------------------------------- app -----
def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="Qt HUD for speedometer.py --qt-hud")
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--parent-pid", type=int, default=0)
    ap.add_argument("--anchor", choices=("bottom", "center"), default="bottom")
    ap.add_argument("--offset-y", type=float, default=None)
    ap.add_argument("--offset-x", type=float, default=0.0)
    ap.add_argument("--show", default="", help="optional widgets: splits,minimap,nextcp")
    ap.add_argument("--scrim", type=float, default=0.10)
    ap.add_argument("--scale", type=float, default=None)
    ap.add_argument("--opacity", type=float, default=1.0)
    ap.add_argument("--fps", type=float, default=50.0, help="overlay repaint rate (30 = less CPU)")
    ap.add_argument("--offline", action="store_true", help="map list from the bundled snapshot")
    ap.add_argument("--select-map", action="store_true", help="open the map selector at start")
    ap.add_argument("--fullscreen", action="store_true", help="cover the whole screen (default: band)")
    ap.add_argument("--no-click-through", action="store_true")
    return ap.parse_args(argv)


def band_geometry(screen_rect, th, opt):
    """Smallest window that holds every overlay element (cheaper than full screen).

    ``MinimalOverlay.center()`` is computed from the widget size and the anchor;
    the band keeps the gauge at exactly the same screen position as a full-screen
    overlay would (bottom edge aligned for "bottom", centred for "center").
    """
    from PySide6.QtCore import QRect

    px = th.px
    w = min(screen_rect.width(), int(px(1200) + 2 * abs(px(opt.offset_x))))
    x = screen_rect.x() + (screen_rect.width() - w) // 2
    if opt.anchor == "center":
        h = min(screen_rect.height(), int(2 * (abs(px(opt.offset_y)) + px(280))))
        y = screen_rect.y() + (screen_rect.height() - h) // 2
    else:
        h = min(screen_rect.height(), int(px(opt.offset_y) + px(104 + 170)))
        y = screen_rect.y() + screen_rect.height() - h
    return QRect(x, y, w, h)


def build_overlay_class():
    from hud_qt.minimal import LABEL, MinimalOverlay
    from hud_qt.model import fmt_time
    from hud_qt.painting import outlined_text
    from hud_qt.theme import Theme
    from hud_qt.widgets import nice_delta

    class LiveOverlay(MinimalOverlay):
        """MinimalOverlay + map name, record line and "--" when there is no reference."""

        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            self.setWindowTitle("GW2 Speedometer HUD (Qt)")
            self.extra = {}
            self.connected = False
            self.paint_errors = 0

        def _apply_flags(self):
            # Frameless | Tool | StaysOnTop | TransparentForInput (MinimalOverlay) and
            # never take the keyboard focus from GW2. Set here, BEFORE the
            # WA_TranslucentBackground attribute: changing the flags afterwards
            # recreates the native window and breaks the per-pixel alpha clear.
            from PySide6.QtCore import Qt

            super()._apply_flags()
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowDoesNotAcceptFocus)

        def paintEvent(self, _e):
            # Same layers as MinimalOverlay.paintEvent, but the painter is ALWAYS
            # ended: an exception in one layer used to leave it active, so Qt
            # stopped clearing the translucent window (frames accumulated) and
            # then stopped repainting at all.
            from hud_qt.painting import setup
            from PySide6.QtGui import QPainter

            p = QPainter(self)
            try:
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
            except Exception as exc:  # noqa: BLE001 - never kill the overlay
                self.paint_errors += 1
                if self.paint_errors == 1:
                    import traceback

                    print("[qt-hud] paint error (ignored):", repr(exc))
                    traceback.print_exc()
            finally:
                p.end()

        def _splits(self, p, C, R):
            # MinimalOverlay._splits assumes every crossed split has a diff; with
            # real data the first lap has no reference yet -> show "--".
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
                cur = i == s.checkpoint and not s.finished and bool(self.extra.get("racing", True))
                done = sp.time is not None
                base = Theme.ACCENT if cur else Theme.TEXT if done else Theme.TEXT_MUTED
                outlined_text(p, left, y, sp.label, fl, base, th, outline=0.8)
                t = fmt_time(sp.time) if done else (fmt_time(s.lap_time) if cur else "--:--.---")
                outlined_text(p, left + th.px(48), y, t, ft, base if not done else Theme.TEXT_DIM, th, outline=0.8)
                if done and sp.diff is not None:
                    outlined_text(p, right, y, nice_delta(sp.diff, 2), ft, Theme.delta_color(round(sp.diff, 3)),
                                  th, align="right", outline=0.8)
                elif done:
                    outlined_text(p, right, y, "--", ft, Theme.TEXT_DIM, th, align="right", outline=0.8)

        def closeEvent(self, e):  # Esc (only without click-through): close the whole HUD
            from PySide6.QtWidgets import QApplication

            super().closeEvent(e)
            QApplication.quit()

        def _delta(self, p, C, R):
            s = self.state
            split = self.flash > 0 and self.flash_diff is not None
            if split or s.delta is not None:
                return super()._delta(p, C, R)
            th = self.th
            x = C.x() - R - th.px(30)
            y = C.y() - th.px(4)
            outlined_text(p, x, y - th.px(34), "DELTA", self.f(10.5, 800, spacing=2.0), LABEL, th,
                          align="right", outline=0.9)
            outlined_text(p, x, y, "--", self.f(40, 800, tnum=True), Theme.TEXT_DIM, th, align="right")

        def _timer(self, p, C, R):
            th, s = self.th, self.state
            x = C.x() + R + th.px(30)
            y = C.y() - th.px(4)
            if s.checkpoints_total and s.finished:
                head = f"VUELTA {s.lap}/{s.laps_total}  ·  FIN"
            elif s.checkpoints_total:
                cp = min(s.checkpoint + 1, s.checkpoints_total)
                head = f"VUELTA {s.lap}/{s.laps_total}  ·  CP {cp}/{s.checkpoints_total}"
            else:
                head = "SIN CHECKPOINTS"
            outlined_text(p, x, y - th.px(34), head, self.f(10.5, 800, spacing=2.0), LABEL, th, outline=0.9)
            outlined_text(p, x, y, fmt_time(s.lap_time), self.f(34, 800, tnum=True), Theme.TEXT, th)
            name = s.map_name if s.map_name not in ("", "-", "SELECT MAP") else "SIN MAPA · Ctrl+Shift+M"
            outlined_text(p, x, y - th.px(56), name.upper()[:42], self.f(10.5, 800, spacing=1.6),
                          Theme.ACCENT, th, outline=0.9)
            rec = self.extra.get("record")
            best = s.best_lap
            line = f"MEJOR {fmt_time(best, '--')}   RÉCORD {fmt_time(rec, '--')}"
            if s.finished and s.final_time is not None:
                line = f"FINAL {fmt_time(s.final_time)}"
                if s.race_best_delta is not None:
                    line += f"  ({nice_delta(s.race_best_delta, 3)})"
            outlined_text(p, x, y + th.px(30), line, self.f(10.5, 700, spacing=1.2, tnum=True),
                          LABEL, th, outline=0.9)
            if not self.connected:
                outlined_text(p, x, y + th.px(50), "ESPERANDO AL SPEEDOMETER…",
                              self.f(10, 800, spacing=1.6), Theme.ORANGE, th, outline=0.9)

    return LiveOverlay


class LiveHud:
    def __init__(self, app, args, token):
        from hud_qt.map_catalog import MapEntry
        from hud_qt.map_selector import MapSelector
        from hud_qt.minimal import OverlayOptions
        from hud_qt.theme import Theme
        from PySide6.QtCore import QTimer

        self.app = app
        self.args = args
        self.MapEntry = MapEntry
        self.link = ClientLink(args.port, token)
        scale = args.scale or max(1.0, round(app.primaryScreen().geometry().height() / 1080, 1))
        show = {s.strip() for s in args.show.split(",") if s.strip()}
        offset_y = args.offset_y if args.offset_y is not None else (250.0 if args.anchor == "bottom" else 0.0)
        self.opts = OverlayOptions(anchor=args.anchor, offset_y=offset_y, offset_x=args.offset_x,
                                   show_splits="splits" in show, show_minimap="minimap" in show,
                                   show_nextcp="nextcp" in show, scrim=args.scrim)
        self._optional_default = ("splits", "nextcp", "minimap")
        self.th = Theme(scale=scale, opacity=args.opacity)
        self.ov = build_overlay_class()(self.th, self.opts, click_through=not args.no_click_through)
        self.place()
        self.ov.show()
        win_overlay_styles(self.ov)
        self.selector = MapSelector(self.th, hotkey_label="Ctrl+Shift+M")
        self.selector.setWindowTitle("Seleccionar mapa")
        self.selector.start_loading(online=not args.offline)
        self.selector.mapChosen.connect(self.on_map_chosen)
        self.static = {}
        self.static_seq = None
        self.state_dict = None
        self.state_time = 0.0
        self.last_rx = 0.0
        self.last_hello = -1e9
        self.map_name = None
        self.last_frame = time.perf_counter()
        self.quitting = False

        from PySide6.QtCore import QObject, Signal

        class _Bridge(QObject):
            selector = Signal()
            optional = Signal()

        self.bridge = _Bridge()  # pynput thread -> Qt thread (queued signals)
        self.bridge.selector.connect(self.toggle_selector)
        self.bridge.optional.connect(self.toggle_optional)
        self.hotkeys = Hotkeys({"m": self.bridge.selector.emit, "o": self.bridge.optional.emit})
        self.hotkeys.start()
        self._shortcuts()
        self._tray()

        self.timer = QTimer()
        self.timer.timeout.connect(self.frame)
        self.timer.start(max(5, int(1000 / max(10.0, args.fps))))
        self.keep_up = QTimer()  # the speedometer's Tk windows re-assert -topmost every 500 ms
        self.keep_up.timeout.connect(self.keep_selector_on_top)
        self.keep_up.start(400)
        self.watch = QTimer()
        self.watch.timeout.connect(self.watchdog)
        self.watch.start(2000)
        app.aboutToQuit.connect(self.on_quit)
        self.say_hello(force=True)
        if args.select_map:
            QTimer.singleShot(600, self.open_selector)

    @staticmethod
    def _qt():
        from PySide6.QtCore import Qt

        return Qt

    def place(self):
        scr = self.app.primaryScreen()
        if self.args.fullscreen:
            self.ov.cover_screen(scr)
        else:
            self.ov.setGeometry(band_geometry(scr.geometry(), self.th, self.opts))

    def _shortcuts(self):
        from PySide6.QtGui import QKeySequence, QShortcut

        Qt = self._qt()
        for seq in ("Ctrl+Shift+M", "Ctrl+M", "F2"):
            QShortcut(QKeySequence(seq), self.selector, activated=self.toggle_selector,
                      context=Qt.ShortcutContext.WindowShortcut)
            QShortcut(QKeySequence(seq), self.ov, activated=self.toggle_selector)
        QShortcut(QKeySequence("Ctrl+Shift+O"), self.ov, activated=self.toggle_optional)

    def _tray(self):
        from PySide6.QtGui import QIcon
        from PySide6.QtWidgets import QMenu, QSystemTrayIcon

        self.tray = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        tray = QSystemTrayIcon(QIcon(os.path.join(HERE, "logo.png")), self.app)
        menu = QMenu()
        menu.addAction("Seleccionar mapa (Ctrl+Shift+M)", self.open_selector)
        menu.addAction("Opcionales on/off (Ctrl+Shift+O)", self.toggle_optional)
        menu.addSeparator()
        menu.addAction("Cerrar HUD nuevo (vuelve el clásico)", self.app.quit)
        tray.setContextMenu(menu)
        tray.setToolTip("GW2 Speedometer · HUD nuevo")
        tray.show()
        self.tray = tray
        self._tray_menu = menu

    # -- actions ------------------------------------------------------------
    def open_selector(self):
        self.selector.open(self.app.primaryScreen())
        win_force_foreground(self.selector)

    def toggle_selector(self):
        if self.selector.isVisible():
            self.selector.hide()
        else:
            self.open_selector()

    def toggle_optional(self):
        o = self.opts
        on = not (o.show_splits or o.show_nextcp or o.show_minimap)
        o.show_splits = o.show_nextcp = o.show_minimap = on
        self.ov.toast("OPCIONALES " + ("ON" if on else "OFF"), 1.5)
        self.ov.update()

    def on_map_chosen(self, entry):
        print(f"[qt-hud] map chosen: {entry.name!r} ({entry.cup}, {entry.source})")
        self.link.send("choose_map", {"cup": entry.cup, "name": entry.name, "source": entry.source})
        self.ov.toast(f"CARGANDO MAPA · {entry.name}", 4.0)

    def say_hello(self, force=False):
        now = time.monotonic()
        every = 1.0 if not self.ov.connected else 3.0
        if force or now - self.last_hello >= every:
            self.last_hello = now
            self.link.send("hello", {"pid": os.getpid()})

    # -- loop ---------------------------------------------------------------
    def handle(self, msg):
        kind = msg.get("type")
        data = msg.get("data") or {}
        if kind == "state":
            self.state_dict = data
            self.state_time = time.monotonic()
        elif kind == "map":
            self.static = data
            name = data.get("map_name", "")
            if data.get("map_seq") != self.static_seq:
                self.static_seq = data.get("map_seq")
                print(f"[qt-hud] map {name!r}: {len(data.get('checkpoints_xy', []))} checkpoints,"
                      f" {len(data.get('track', []))} track points")
            if self.map_name is not None and name != self.map_name and name not in ("", "-", "SELECT MAP"):
                self.ov.toast(f"MAPA · {name}", 3.0)
            self.map_name = name
            if name and name not in ("-", "SELECT MAP"):
                cup = data.get("cup", "")
                src = "local" if cup == "OWN MAPS FOLDER" else "online"
                self.selector.selected = self.MapEntry(name, cup, src)
        elif kind == "quit":
            self.app.quit()

    def frame(self):
        for msg in self.link.poll():
            self.last_rx = time.monotonic()
            self.handle(msg)
        self.ov.connected = self.state_dict is not None and time.monotonic() - self.last_rx < 3.0
        self.say_hello()
        if self.state_dict is not None:
            s = state_from_dict(self.state_dict, self.static)
            if self.state_dict.get("racing"):
                s.lap_time += min(0.1, time.monotonic() - self.state_time)  # smooth between packets
            self.ov.extra = self.state_dict
            self.ov.update_state(s)
        now = time.perf_counter()
        dt = min(0.1, now - self.last_frame)
        self.last_frame = now
        self.ov.tick(dt)

    def keep_selector_on_top(self):
        if self.selector.isVisible():
            self.selector.raise_()
            win_keep_topmost(self.selector)

    def watchdog(self):
        win_keep_topmost(self.ov)
        if not parent_alive(self.args.parent_pid):
            print("[qt-hud] speedometer is gone: closing")
            self.app.quit()

    def on_quit(self):
        if not self.quitting:
            self.quitting = True
            self.link.send("bye")


def main(argv=None):
    args = parse_args(argv)
    token = os.environ.get(ENV_TOKEN, "")
    if not token:
        print(f"[qt-hud] missing {ENV_TOKEN}: start it with speedometer.py --qt-hud")
        return 2
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import QApplication

    # Qt 6 is per-monitor DPI aware (v2) on Windows by default; keep fractional
    # scale factors (125 %, 150 %) instead of rounding them.
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv[:1])
    app.setQuitOnLastWindowClosed(False)  # hiding the selector must not quit
    app.setApplicationName("GW2 Speedometer HUD")
    hud = LiveHud(app, args, token)
    app._live_hud = hud
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
