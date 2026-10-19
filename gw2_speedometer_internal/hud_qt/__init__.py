"""Maqueta de HUD nuevo en PySide6/QPainter (no integrada todavía).

Paquete independiente: no importa speedometer.py ni toca la medición ni los logs.
La única dependencia del resto de la app es opcional (geometría del circuito
simulado de ``mumblelink_linux`` y ``maps/SIM_CIRCUIT.csv``).

Piezas:
    model.HudState          -> contrato de datos que pinta el HUD
    sim_source.SimRace      -> fuente simulada (datos de ejemplo, NO medición real)
    hud_window.HudWindow    -> ventana overlay (frameless, translúcida, on-top)
    finish_screen.FinishScreen -> pantalla de fin de carrera
    capture                 -> render offscreen + composición sobre fondo de juego
"""

__all__ = ["capture", "finish_screen", "hud_window", "model", "sim_source", "theme", "widgets"]
