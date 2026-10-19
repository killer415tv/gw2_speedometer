"""Demo de la MAQUETA del HUD nuevo en PySide6 (no integrada con speedometer.py).

Datos 100% simulados (circuito elíptico de mumblelink_linux --simulate / SIM_CIRCUIT.csv).
No lee MumbleLink real, no escribe logs.

    python hud_qt_demo.py                      # HUD completo, ventana overlay
    python hud_qt_demo.py --compact --scale 1.5 --opacity 0.85 --bg-alpha 0.5
    python hud_qt_demo.py --click-through      # el ratón atraviesa la ventana
    python hud_qt_demo.py --speedup 3          # simulación 3x
    python hud_qt_demo.py --finish             # salta a la pantalla de fin de carrera
    python hud_qt_demo.py --capture DIR        # genera PNG/GIF offscreen y sale

Teclas (sin --click-through): C compacto/completo · +/- escala · O opacidad ·
B translucidez del fondo · T activar click-through · Esc/Q salir. Arrastrar = mover.
"""

import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from hud_qt.finish_screen import FinishScreen
from hud_qt.hud_window import HudWindow
from hud_qt.sim_source import SimRace
from hud_qt.theme import Theme
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication


def main(argv=None):
    ap = argparse.ArgumentParser(description="Maqueta HUD Qt (datos simulados)")
    ap.add_argument("--compact", action="store_true", help="modo compacto")
    ap.add_argument("--scale", type=float, default=None, help="escala (1.0=1080p, 2.0=4K). Auto si se omite")
    ap.add_argument("--opacity", type=float, default=1.0, help="opacidad global 0-1")
    ap.add_argument("--bg-alpha", type=float, default=0.66, help="translucidez del fondo de paneles 0-1")
    ap.add_argument("--click-through", action="store_true", help="Qt.WindowTransparentForInput")
    ap.add_argument("--no-top", action="store_true", help="sin always-on-top")
    ap.add_argument("--laps", type=int, default=3)
    ap.add_argument("--speedup", type=float, default=1.0)
    ap.add_argument("--finish", action="store_true", help="simular hasta el final y mostrar resultados")
    ap.add_argument("--backdrop", action="store_true",
                    help="fondo de juego simulado a pantalla completa detrás del HUD (pruebas sin GW2)")
    ap.add_argument("--capture", metavar="DIR", help="renderizar capturas en DIR y salir")
    args = ap.parse_args(argv)

    app = QApplication(sys.argv[:1])
    if args.capture:
        from hud_qt.capture import run_capture
        run_capture(args.capture, scale=args.scale or 1.0)
        return 0

    scale = args.scale
    if scale is None:  # auto: 1.0 a 1080p, 2.0 a 2160p
        scr = app.primaryScreen().geometry()
        scale = max(1.0, round(scr.height() / 1080 / app.primaryScreen().devicePixelRatio(), 1))
    th = Theme(scale=scale, opacity=args.opacity, bg_alpha=args.bg_alpha, compact=args.compact)
    sim = SimRace(laps=args.laps)
    hud = HudWindow(th, click_through=args.click_through, on_top=not args.no_top)
    fin = FinishScreen(Theme(scale=scale, opacity=args.opacity, bg_alpha=max(args.bg_alpha, 0.8)),
                       click_through=False)
    if args.backdrop:
        from hud_qt.capture import fake_game_ui, game_background
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QPixmap
        from PySide6.QtWidgets import QLabel
        geo = app.primaryScreen().geometry()
        backdrop = QLabel()
        backdrop.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnBottomHint)
        backdrop.setPixmap(QPixmap.fromImage(fake_game_ui(game_background(geo.width(), geo.height()))))
        # tipo "desktop" en X11 para que el WM lo deje siempre debajo (Openbox lo subía a la capa fullscreen)
        backdrop.setAttribute(Qt.WidgetAttribute.WA_X11NetWmWindowTypeDesktop, True)
        backdrop.setGeometry(geo)
        backdrop.show()
    hud.show()
    hud.place_bottom_left()
    hud.raise_()
    QTimer.singleShot(300, hud.raise_)

    if args.finish:
        while not sim.finished:
            sim.step(1 / 30)

    last = [time.perf_counter()]
    finished_at = [None]

    def frame():
        now = time.perf_counter()
        dt = min(0.1, now - last[0])
        last[0] = now
        s = sim.step(dt * args.speedup)
        hud.update_state(s)
        hud.tick(dt)
        if s.finished:
            if finished_at[0] is None:
                finished_at[0] = now
                fin.set_state(s)
                fin.show()
                g = fin.screen().availableGeometry()
                fin.move(g.center() - fin.rect().center())
            elif now - finished_at[0] > 12 and fin.isVisible():
                pass
            elif not fin.isVisible():  # tras "Cerrar": nueva carrera
                sim.reset()
                finished_at[0] = None

    t = QTimer()
    t.timeout.connect(frame)
    t.start(16)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
