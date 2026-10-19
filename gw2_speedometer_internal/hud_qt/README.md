# hud_qt — maqueta de HUD nuevo (PySide6 + QPainter)

**Estado:** maqueta independiente, NO integrada con `speedometer.py`. Datos simulados
(`sim_source.SimRace`, circuito elíptico de `mumblelink_linux --simulate` y
`maps/SIM_CIRCUIT.csv`). No lee MumbleLink real y no escribe logs.

Dependencias: `PySide6-Essentials` (y `ffmpeg` sólo para generar el GIF de capturas).
Tipografía: Montserrat (repo `fonts/Montserrat-Regular.ttf`; si hay Montserrat variable
en el sistema se usan los pesos bold/extrabold).

```bash
python hud_qt_demo.py                       # HUD completo (overlay frameless/translúcido/on-top)
python hud_qt_demo.py --compact --scale 2   # compacto, 4K
python hud_qt_demo.py --opacity 0.8 --bg-alpha 0.45
python hud_qt_demo.py --click-through       # Qt.WindowTransparentForInput
python hud_qt_demo.py --backdrop            # fondo de juego simulado detrás (pruebas sin GW2)
python hud_qt_demo.py --finish              # pantalla de fin de carrera
python hud_qt_demo.py --capture DIR         # PNG + GIF renderizados offscreen
```

Teclas: `C` compacto/completo · `+`/`-` escala · `O` opacidad · `B` translucidez fondo ·
`T` click-through · `Esc` salir. Arrastrar con el ratón mueve el HUD.

| Módulo | Contenido |
|---|---|
| `model.py` | `HudState` (contrato de datos del HUD), `Split`, `Rival`, `RankEntry`, formateadores |
| `sim_source.py` | carrera simulada: jugador, ghost, 3 rivales, splits, delta, trazas, ranking ficticio |
| `theme.py` / `painting.py` | paleta, Montserrat, escala/opacidad, panel translúcido con sombra suave |
| `widgets.py` | velocímetro, barra acel/boost, delta con flash, splits, minimapa, siguiente CP, crono |
| `hud_window.py` | ventana overlay y layouts completo/compacto |
| `finish_screen.py` | fin de carrera: tiempo, ranking, gráfica velocidad vs distancia, "Subir log" (sin acción) |
| `capture.py` | render ARGB offscreen + composición sobre fondo de juego generado |

## Integración futura (sin tocar los logs)
Escribir un adaptador que **lea** el estado que `speedometer.py` ya calcula (velocidad,
checkpoints, tiempos, ghost) y rellene un `HudState` en el hilo de Qt (p. ej. con un
`QTimer` a 60 Hz o una cola thread-safe). El HUD sólo consume `HudState`; el cálculo y la
escritura de logs siguen siendo los de siempre.
