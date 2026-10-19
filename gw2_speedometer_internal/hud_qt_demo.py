"""Demo de la MAQUETA del HUD nuevo en PySide6 (no integrada con speedometer.py).

v2 (por defecto): overlay MINIMALISTA transparente a pantalla completa, click-through,
con el medidor centrado (abajo-centro o centro) + selector de mapas.
Datos de carrera 100% simulados; la lista de mapas viene de beetlerank.com (GET de solo
lectura) o, sin red, de una instantánea de ejemplo. No lee MumbleLink real, no escribe logs,
no escribe cup.txt/guildhall.txt.

    python hud_qt_demo.py                          # minimal, medidor abajo-centro
    python hud_qt_demo.py --anchor center --offset-y 40
    python hud_qt_demo.py --show splits,minimap,nextcp --scrim 0
    python hud_qt_demo.py --select-map             # abre el selector al arrancar
    python hud_qt_demo.py --backdrop               # fondo de juego simulado detrás (pruebas)
    python hud_qt_demo.py --classic                # HUD v1 con tarjetas
    python hud_qt_demo.py --capture DIR            # capturas v2 (o v1 con --classic)

Atajo del selector: Ctrl+Shift+M global (si pynput está instalado), icono de bandeja,
o Ctrl+M / F2 con el foco en el selector u overlay no click-through (--no-click-through).
"""

import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from hud_qt.finish_screen import FinishScreen
from hud_qt.sim_source import SimRace
from hud_qt.theme import Theme
from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication


class _Hotkey(QObject):
    fired = Signal()


def _global_hotkey(combo, callback):
    """Atajo global opcional con pynput (dependencia que ya usa speedometer.py)."""
    try:
        from pynput import keyboard
    except ImportError:
        return None
    bridge = _Hotkey()
    bridge.fired.connect(callback)  # hilo de pynput -> hilo de Qt (conexión en cola)
    listener = keyboard.GlobalHotKeys({combo: bridge.fired.emit})
    listener.daemon = True
    listener.start()
    listener._qt_bridge = bridge  # mantener referencia
    return listener


def auto_scale(app):
    scr = app.primaryScreen()
    return max(1.0, round(scr.geometry().height() / 1080, 1))  # px lógicos (Qt ya aplica el DPR)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Maqueta HUD Qt (datos simulados)")
    ap.add_argument("--classic", action="store_true", help="HUD v1 con tarjetas")
    ap.add_argument("--anchor", choices=("bottom", "center"), default="bottom")
    ap.add_argument("--offset-y", type=float, default=None,
                    help="px (a 1080p, se escala) hacia arriba desde el ancla. Por defecto 250 abajo / 0 centro")
    ap.add_argument("--offset-x", type=float, default=0.0)
    ap.add_argument("--show", default="", help="opcionales: splits,minimap,nextcp")
    ap.add_argument("--scrim", type=float, default=0.10, help="velo radial detrás del medidor (0 = sin fondo)")
    ap.add_argument("--scale", type=float, default=None, help="escala (1.0=1080p, 2.0=4K). Auto si se omite")
    ap.add_argument("--opacity", type=float, default=1.0)
    ap.add_argument("--no-click-through", action="store_true", help="el overlay recibe ratón/teclas")
    ap.add_argument("--select-map", action="store_true", help="abrir el selector de mapas al inicio")
    ap.add_argument("--offline", action="store_true", help="no consultar beetlerank.com (usa la instantánea)")
    ap.add_argument("--hotkey", default="<ctrl>+<shift>+m", help="atajo global pynput del selector")
    ap.add_argument("--backdrop", action="store_true", help="fondo de juego simulado detrás (pruebas sin GW2)")
    ap.add_argument("--laps", type=int, default=3)
    ap.add_argument("--speedup", type=float, default=1.0)
    ap.add_argument("--capture", metavar="DIR", help="renderizar capturas en DIR y salir")
    # opciones del HUD v1
    ap.add_argument("--compact", action="store_true", help="(v1) modo compacto")
    ap.add_argument("--bg-alpha", type=float, default=0.66, help="(v1) translucidez de las tarjetas")
    ap.add_argument("--click-through", action="store_true", help="(v1) click-through")
    ap.add_argument("--finish", action="store_true", help="(v1) saltar al fin de carrera")
    args = ap.parse_args(argv)

    app = QApplication(sys.argv[:1])
    if args.capture:
        if args.classic:
            from hud_qt.capture import run_capture
            run_capture(args.capture, scale=args.scale or 1.0)
        else:
            from hud_qt.capture_v2 import run_capture_v2
            run_capture_v2(args.capture, online=not args.offline)
        return 0
    if args.classic:
        return _classic(app, args)

    from hud_qt.map_selector import MapSelector
    from hud_qt.minimal import MinimalOverlay, OverlayOptions

    scale = args.scale or auto_scale(app)
    show = {s.strip() for s in args.show.split(",") if s.strip()}
    opts = OverlayOptions(anchor=args.anchor,
                          offset_y=args.offset_y if args.offset_y is not None else (250.0 if args.anchor == "bottom" else 0.0),
                          offset_x=args.offset_x, show_splits="splits" in show, show_minimap="minimap" in show,
                          show_nextcp="nextcp" in show, scrim=args.scrim)
    th = Theme(scale=scale, opacity=args.opacity)
    sim = SimRace(laps=args.laps)
    if args.backdrop:
        _backdrop(app)
    ov = MinimalOverlay(th, opts, click_through=not args.no_click_through)
    ov.cover_screen(app.primaryScreen())
    ov.show()
    QTimer.singleShot(300, ov.raise_)

    selector = MapSelector(th, hotkey_label="Ctrl+Shift+M")
    selector.start_loading(online=not args.offline)

    def chosen(entry):
        ov.toast(f"MAPA · {entry.name}")
        print(f"[maqueta] mapa elegido: {entry.name!r} ({entry.cup}, {entry.source}) -> {entry.checkpoints_ref}")

    selector.mapChosen.connect(chosen)
    for seq in ("Ctrl+M", "F2"):
        QShortcut(QKeySequence(seq), ov, activated=selector.toggle)
        QShortcut(QKeySequence(seq), selector, activated=selector.toggle,
                  context=Qt.ShortcutContext.WindowShortcut)
    hk = _global_hotkey(args.hotkey, selector.toggle)
    if hk is None:
        print("[maqueta] pynput no disponible: sin atajo global (usa --select-map, la bandeja o F2)")
    _tray(app, selector, ov)
    if args.select_map:
        QTimer.singleShot(500, selector.open)

    last = [time.perf_counter()]

    def frame():
        now = time.perf_counter()
        dt = min(0.1, now - last[0])
        last[0] = now
        s = sim.step(dt * args.speedup)
        if s.finished:
            sim.reset()
        ov.update_state(sim.state)
        ov.tick(dt)

    t = QTimer()
    t.timeout.connect(frame)
    t.start(16)
    return app.exec()


def _tray(app, selector, ov):
    from PySide6.QtWidgets import QMenu, QSystemTrayIcon

    if not QSystemTrayIcon.isSystemTrayAvailable():
        return None
    from PySide6.QtGui import QIcon
    tray = QSystemTrayIcon(QIcon(os.path.join(HERE, "logo.png")), app)
    menu = QMenu()
    menu.addAction("Seleccionar mapa…", selector.open)
    menu.addAction("Salir", app.quit)
    tray.setContextMenu(menu)
    tray.show()
    app._tray = tray
    return tray


def _backdrop(app):
    from hud_qt.capture_v2 import _bg
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import QLabel
    geo = app.primaryScreen().geometry()
    b = QLabel()
    b.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnBottomHint)
    b.setAttribute(Qt.WidgetAttribute.WA_X11NetWmWindowTypeDesktop, True)  # Openbox: siempre debajo
    pm = QPixmap.fromImage(_bg(1.0)).scaled(geo.size())
    b.setPixmap(pm)
    b.setGeometry(geo)
    b.show()
    app._backdrop = b


def _classic(app, args):
    from hud_qt.hud_window import HudWindow

    scale = args.scale or auto_scale(app)
    th = Theme(scale=scale, opacity=args.opacity, bg_alpha=args.bg_alpha, compact=args.compact)
    sim = SimRace(laps=args.laps)
    hud = HudWindow(th, click_through=args.click_through)
    fin = FinishScreen(Theme(scale=scale, opacity=args.opacity, bg_alpha=max(args.bg_alpha, 0.8)))
    if args.backdrop:
        _backdrop(app)
    hud.show()
    hud.place_bottom_left()
    if args.finish:
        while not sim.finished:
            sim.step(1 / 30)
    last = [time.perf_counter()]
    done = [False]

    def frame():
        now = time.perf_counter()
        dt = min(0.1, now - last[0])
        last[0] = now
        s = sim.step(dt * args.speedup)
        hud.update_state(s)
        hud.tick(dt)
        if s.finished and not done[0]:
            done[0] = True
            fin.set_state(s)
            fin.show()
            g = fin.screen().availableGeometry()
            fin.move(g.center() - fin.rect().center())
        elif done[0] and not fin.isVisible():
            sim.reset()
            done[0] = False

    t = QTimer()
    t.timeout.connect(frame)
    t.start(16)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
