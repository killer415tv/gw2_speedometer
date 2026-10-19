# hud_qt — maqueta de HUD nuevo (PySide6 + QPainter)

**Estado:** maqueta independiente, NO integrada con `speedometer.py`. Datos simulados
(`sim_source.SimRace`, circuito elíptico de `mumblelink_linux --simulate` y
`maps/SIM_CIRCUIT.csv`). No lee MumbleLink real y no escribe logs.

## v2 (por defecto): overlay minimalista + selector de mapas
- Overlay **transparente a pantalla completa**, click-through, siempre encima; sin tarjetas:
  trazos finos y texto con contorno/sombra sutil. Visible por defecto: velocidad (anillo fino con
  aguja suavizada, 99 = boost), cronómetro, delta (flash al cruzar CP) y vuelta/CP.
  Opcionales ocultos: `--show splits,minimap,nextcp`. Velo radial casi invisible `--scrim 0.10` (0 = nada).
- Medidor **centrado** horizontalmente; `--anchor bottom` (por defecto, 250 px sobre el borde inferior a
  1080p, encima de la barra de habilidades) o `--anchor center`; `--offset-y/--offset-x`; escala auto por
  resolución (4K = 2.0) o `--scale`.
- **Selector de mapas** (`map_catalog.py` + `map_selector.py`): misma fuente que speedometer.py
  (`/api/cups`, `/api/maps/<copa>`, `maps/*.csv` = "OWN MAPS FOLDER"); GET de solo lectura con timeout y
  reintentos; sin red usa `data/beetlerank_maps_snapshot.json` (instantánea de EJEMPLO, se indica en la
  cabecera). Buscador sin acentos/multi-palabra con resaltado, agrupado por copa, filtro Todos/Online/
  Locales, mapa actual (leído de cup.txt/guildhall.txt, sin escribir) marcado «✓ ACTUAL», ↑↓/Enter/Esc,
  se cierra al elegir. Atajo global `Ctrl+Shift+M` (pynput), F2/Ctrl+M o icono de bandeja.
  Al elegir sólo emite `mapChosen(MapEntry)` con `checkpoints_ref` (URL o ruta que cargaría la app).

```bash
python hud_qt_demo.py                                   # v2
python hud_qt_demo.py --anchor center --offset-y 120 --scrim 0
python hud_qt_demo.py --select-map --show nextcp
python hud_qt_demo.py --capture DIR                     # capturas v2 (añade --classic para v1)
```

## v1 (`--classic`): HUD con tarjetas

Dependencias: `PySide6-Essentials` (y `ffmpeg` sólo para generar el GIF de capturas).
Tipografía: Montserrat (repo `fonts/Montserrat-Regular.ttf`; si hay Montserrat variable
en el sistema se usan los pesos bold/extrabold).

```bash
python hud_qt_demo.py --classic             # HUD completo (overlay frameless/translúcido/on-top)
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
Overlay: rellenar `HudState` (ver abajo) y llamar a `MinimalOverlay.update_state()`/`tick()`.
Selector: conectar `mapChosen` a la función existente `saveGuildhall(nombre)` (tras fijar `cup_name`),
que ya carga los checkpoints, escribe cup.txt/guildhall.txt y pide el ranking: la lógica no cambia.

Escribir un adaptador que **lea** el estado que `speedometer.py` ya calcula (velocidad,
checkpoints, tiempos, ghost) y rellene un `HudState` en el hilo de Qt (p. ej. con un
`QTimer` a 60 Hz o una cola thread-safe). El HUD sólo consume `HudState`; el cálculo y la
escritura de logs siguen siendo los de siempre.
