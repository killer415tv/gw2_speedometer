# ANALISIS_FASE2.md — Optimizaciones, unificación y HUD (solo análisis)

> Documento de **análisis**: no se ha implementado nada de lo que aquí se propone.
> Complementa `docs/TELEMETRY.md` (especificación exacta de medición/log/subida).
> Convención de riesgo "compat. competitiva": **Bajo** = no puede cambiar bytes de
> log ni tiempos; **Medio** = puede cambiar valores en casos límite, requiere
> tests de repetición; **Alto** = cambia tiempos/filas observables, requiere
> demostrar equivalencia o aceptación explícita del autor/servidor.
> No hay Windows en el entorno de análisis: todo lo de rendimiento real es
> `[INFERIDO]` hasta medirlo en la máquina del autor.

---

## 1. Posibles optimizaciones de medición y guardado

Punto de partida: el bucle Tk (`after(10)`) hace medición + checkpoints
(`pandas.iterrows` por muestra) + apertura/cierre del CSV por fila + HUD + red.
La medición es correcta si el bucle muestrea > 25 Hz sin huecos > 40 ms
(TELEMETRY §3.4); las optimizaciones buscan **reducir esos huecos**, no cambiar la
fórmula.

| # | Idea | Beneficio esperado | Riesgo compat. | Notas / mitigación |
|---|---|---|---|---|
| 0 | **Instrumentar sin cambiar nada**: contador opcional (debug) de intervalo del bucle, nº de huecos > 40 ms, filas/s; volcado a un fichero aparte | Datos reales para decidir lo demás | **Bajo** | Primer paso obligatorio. No escribe en el CSV |
| 1 | Evitar `open/seek/close` por fila: mantener el fichero abierto y `flush()` por fila (o por lote de N ms) | Quita ~25 `open()`/s del bucle (en Windows, antivirus/indexador por cada cierre = latencia variable) | **Bajo** (contenido idéntico) si se garantiza: mismo `"\r"` previo, mismo orden, `flush`+`close` **antes** de que `end` lea el CSV con pandas y antes de subirlo; cierre en `reset`/cierre de app/excepción | Riesgo real: ficheros truncados si el proceso muere (hoy cada fila ya está en disco). Mantener `flush()` por fila elimina casi todo el riesgo y conserva gran parte del beneficio |
| 2 | Precalcular checkpoints (arrays NumPy/tuplas) y evaluar solo `next_step` y los `reset`, en lugar de `iterrows` de todo el DataFrame por muestra | Reduce mucho el coste CPU por muestra (pandas `iterrows` es lento) | **Bajo/Medio** | Equivalencia exacta con la regla actual: `step == next_step`, radio 5/15 por defecto, `<` estricto, antirrebote `pressedQ`/`different()`; verificar con flujo sintético y mapas reales. Cuidado: hoy `checkpoint()` evalúa filas en orden y puede disparar varias en la misma muestra |
| 3 | Mover el muestreo a un **hilo dedicado** (o proceso) y comunicar al HUD por cola | Elimina el acoplamiento HUD ↔ medición (el motivo principal de huecos) | **Alto** si se cambia la cadencia/cómo se detectan las actualizaciones; **Medio** si el hilo reproduce "una muestra por cambio de posición" | Para equivalencia: detectar cambio de `fAvatarPosition` (o `uiTick`) y calcular el mismo `dst`·constantes por actualización. Hoy un hueco produce SPEED ×2 (filtrado ≥150) y filas perdidas; el hilo dedicado **mejoraría** esos casos pero cambia los logs *en esos casos* ⇒ requiere repetición contra un flujo grabado (§3 paso 0) y aceptación explícita |
| 4 | Hilo/cola para `sendMQTT`/red y para `uploadLog` sin `join()` en el hilo de Tk | Sin bloqueos de hasta 5+30 s del bucle al terminar (`total_laps == 1`) y sin `sendall` bloqueante | **Bajo** (no afecta al log ni a su subida; solo cambia cuándo se muestra el texto de resultado) | Mostrar el resultado de la subida por callback en el hilo de UI (en Qt: señal) |
| 5 | Reloj monótono: `time.perf_counter()` anclado a `time.time()` al inicio de carrera para `TIME` | `TIME` sin saltos si el reloj del sistema se ajusta; resolución sub-ms | **Medio/Alto** | Cambia el valor numérico de los `TIME` (más finos; ya no múltiplos de 15,625 ms) ⇒ tiempos de ranking ligeramente distintos a los de usuarios con la versión actual. Solo con acuerdo del autor/servidor |
| 6 | `timeBeginPeriod(1)` (winmm) o Python ≥ 3.13 (`time.time()` preciso) | Mejor resolución de `after()` y del reloj | **Medio** | Mismo efecto de granularidad que 5; además Python 3.13 exige NumPy ≥ 2.1 (`np.cross` 2D deprecado) ⇒ revisar `angle_between` |
| 7 | Interpolar el instante exacto de cruce de la esfera de `start`/`end` | Tiempos más justos | **Alto** | Cambia los tiempos oficiales sistemáticamente (ganan decenas de ms) y rompe la comparabilidad histórica. **No recomendado** sin decisión del servidor |
| 8 | Corregir la fórmula `ACCELERATION` y el divisor nominal `0,01` | Valores físicamente correctos | **Alto** | `SPEED` depende de esa constante; `ACCELERATION` se registra. Cualquier cambio altera columnas de logs. Mantener "modo legado" bit a bit |
| 9 | Escritura por lotes en memoria y volcado al terminar la vuelta | Menos I/O | **Medio/Alto** | Si el juego/app se cierra a mitad se pierde la vuelta; el `end` actual relee el CSV (habría que leer de memoria). Desaconsejado frente a la opción 1 |
| 10 | Subida con reintentos y cola persistente (carpeta `uploads_pending/`) | No pierde subidas por red caída | **Bajo** (mismos bytes y campos; solo cambia *cuándo*) | Mantener `Origin/Referer: null`, multipart igual; no reenviar duplicados (el servidor puede aceptar duplicados `[NO VERIFICADO]`) |
| 11 | HUD: actualizar widgets solo si cambia el valor; limitar a 60 Hz | Menos coste por muestra | **Bajo** para logs | Si el muestreo sigue en el mismo hilo, mejora los huecos |
| 12 | Unificar `Meter`/`Meterv2` | Menos código | **Medio** | Divergencia real en `MAP_ANGLE` y en el `angle` multijugador (TELEMETRY §10.2): conservar con una opción `legacy_map_angle` |

**Recomendación de orden:** 0 → 2 → 1 (con `flush` por fila) → 4 → 11 → (3 solo
tras tener el flujo grabado). Dejar 5–9 fuera hasta tener decisión explícita.

---

## 2. Arquitectura de unificación propuesta

### 2.1 Objetivo

Una sola aplicación con **núcleo** (speedometer + visor de checkpoints) y
**extras** (ghost, mapa, creadores, vectores, forza, plotter). Una sola
implementación de MumbleLink, una sola de medición, un solo punto de entrada.

### 2.2 Estructura de carpetas

```
gw2_speedometer_easy/
├─ launch.bat / launch.ps1            # uv run python -m gw2speed
├─ pyproject.toml                     # (o requirements*.txt actuales)
├─ gw2speed/
│  ├─ __main__.py                     # único punto de entrada (argparse: gui | extra <nombre> | check-log)
│  ├─ core/                           # SIN GUI, 100 % testeable
│  │  ├─ mumble.py                    # única copia de Link/Context/MumbleLink + parse_identity
│  │  ├─ metrics.py                   # velocidad/ángulos/aceleración: funciones puras (fórmulas actuales, "legacy exacto")
│  │  ├─ logfile.py                   # formato CSV byte-exacto (cabecera, "\r", roundstr)
│  │  ├─ race.py                      # máquina de estados: checkpoints, vueltas, antirrebote, tiempos
│  │  ├─ beetlerank.py                # cliente API + upload-log (timeouts, mismo multipart)
│  │  ├─ netclient.py / netmsg.py     # telemetry_client + validación
│  │  ├─ config.py, paths.py          # config.txt (compatible), APP_DIR, sanitize_map_name
│  │  └─ sampler.py                   # bucle de muestreo (hilo propio o QTimer), emite eventos
│  ├─ ui/
│  │  ├─ main_window.py               # pestañas (Qt)
│  │  ├─ hud/                         # HUD: modelo de vista + backend (qt, tk legado)
│  │  ├─ checkpoints_view.py          # visor 3D (el actual, refactorizado)
│  │  └─ race_panel.py                # copas/mapas, ranking, subida, multijugador
│  └─ extras/
│     ├─ ghost.py (+ relative_to_user), map_realtime.py (+ multiplayer),
│     ├─ creators.py (JP/RACING), vectors.py, forza.py, plotter3d.py
├─ tests/ (unitarios + golden/ con flujos grabados y logs de referencia)
└─ gw2_speedometer_internal/          # se mantiene durante la transición (config.txt, maps/, logs/)
```

Compatibilidad en disco durante la transición: mismas carpetas `logs/`, `maps/`,
`config.txt`, `*_records.csv`; `guildhall.txt`, `cup.txt`, `checkpoint.txt` se
siguen escribiendo mientras haya extras que los lean.

### 2.3 Decisiones de diseño

1. **Un solo bucle de eventos: Qt (PySide6).** El visor 3D ya necesita Qt;
   mezclar `Tk.mainloop` y `QApplication` en un proceso exige hilos/puentes
   frágiles. Unificar significa mover el HUD y los paneles a Qt (§3).
2. **Núcleo sin GUI.** `metrics` + `logfile` + `race` son funciones/objetos puros
   alimentados por muestras `(t, pos, camFront, avatarFront, mapId, name)`:
   permite replays y golden tests sin Windows ni GW2.
3. **Dos modos de medición** en `metrics.py`: `legacy_exact` (por defecto; las
   fórmulas actuales tal cual, incluidas sus rarezas) y, más adelante, `v2`
   opt-in. Los logs de competición **siempre** salen de `legacy_exact` hasta
   acuerdo con el servidor.
4. **Sustituir las teclas globales simuladas** (`pynput` `t`/`y`) entre
   speedometer y ghost por un canal interno (señal Qt / cola / fichero). Hoy esas
   teclas llegan al juego si tiene el foco. Los extras como procesos aparte
   pueden usar un socket local o un fichero de eventos; mantener las teclas como
   opción de compatibilidad.
5. **Extras como subcomandos/pestañas**, cargados bajo demanda (`python -m
   gw2speed extra ghost`) para no importar `plotly`/OpenGL si no se usan.
6. **Una sola implementación de `Meter`.** Resolver `Meter`/`Meterv2` con una
   opción de compatibilidad para `MAP_ANGLE`.
7. **Pestañas**: *Speedometer/Carrera* (HUD, copas/mapas, ranking, subida,
   multijugador), *Checkpoints* (visor 3D), *Config*, *Extras* (lanzadores),
   *Logs* (utilidad `check-log`: valida formato y cadencia de un CSV; ver
   TELEMETRY §13).

### 2.4 Plan por pasos (cada uno = commit/PR con tests verdes; ninguno cambia el log)

| Paso | Qué | Criterio de aceptación |
|---|---|---|
| 0 | **Corpus de referencia en Windows**: (a) grabador opcional del flujo crudo de MumbleLink + `time.time()` por muestra, (b) logs reales generados con la versión actual, (c) subida de prueba si el autor lo autoriza | Existen ≥ 3 carreras grabadas (mapas, 2D/3D, 1 y varias vueltas) |
| 1 | Extraer `metrics.py`+`logfile.py` desde `Meterv2` sin cambiar comportamiento | Test golden: mismo flujo sintético ⇒ **mismos bytes** que el código actual (extraído por AST como ya hacen los tests) |
| 2 | Una sola `mumblelink.py` en todos los scripts (borrar las 8 copias) | Tests de estructura (offsets/tamaños) idénticos; `uiVersion==0` y identity vacío manejados |
| 3 | Extraer `race.py` (checkpoints/vueltas/antirrebote/tiempos), con precálculo de checkpoints (opt. 2) | Mismas decisiones start/*/end/reset en flujos sintéticos y en el corpus del paso 0 |
| 4 | `config.py` + `paths.py` (APP_DIR, sanitize) en todo el proyecto | Mismos valores efectivos de config; sin `sys.argv[0]`/`"\\"` hardcodeados |
| 5 | Unificar `Meter`/`Meterv2` con `legacy_map_angle` | Logs idénticos a ambos modos bajo cada opción |
| 6 | Punto de entrada único + procesos/pestañas (aún con HUD Tk) | `python -m gw2speed` abre lo mismo que hoy |
| 7 | Mover extras a `extras/` + sustituir teclas simuladas por IPC (con modo compat) | Ghost sincroniza igual (diferencia ≤ 1 muestra) |
| 8 | HUD Qt (§3) como backend alternativo, luego por defecto | HUD no toca la lógica; logs byte-idénticos |
| 9 | (Opcional, acordado) optimizaciones 3/5–7 con modo `v2` etiquetado | Aceptación explícita + corpus comparado |

Riesgos de la unificación: (1) cambios sutiles en el orden de operaciones por
muestra; (2) pérdida del comportamiento "una sola hebra" que hoy fija la
cadencia; (3) Qt y OpenGL en una sola ventana principal (el visor 3D usa
`pyqtgraph.opengl`); (4) rutas Windows y `launch.bat`/uv.

---

## 3. Opciones de HUD

Requisitos del HUD actual: ventana sin marco, siempre encima, transparente,
**clic a través** (no robar foco ni clics al juego), gauge con arco, texto de
velocidad/tiempo/mensajes, colores configurables, muy poco coste por frame.

### 3.1 Tabla comparativa

| Opción | Pros | Contras | Esfuerzo | Transparencia / clic-through |
|---|---|---|---|---|
| **A. tkinter mejorado** (canvas, imágenes Pillow supersampleadas, menos `Tk()` raíz, `itemconfig` solo si cambia) | Sin dependencias nuevas; cambio mínimo; sigue en el mismo bucle | Sin alpha por píxel (solo `-transparentcolor` = bordes dentados) ni antialias real; varios `Tk()`; HUD y medición comparten hilo; no combina con Qt en el mismo proceso | S–M | Color-key + `-topmost`; clic-through requiere `WS_EX_TRANSPARENT` vía ctypes |
| **B. CustomTkinter** | Widgets modernos | No resuelve overlay/gauge/alpha; añade dependencia; mismo hilo | M | No mejora |
| **C. PySide6 (Qt Widgets) + `QPainter`** (+ `pyqtgraph` para gráficas) | **Ya es dependencia y ya se usa para overlays transparentes** (visor 3D); alpha por píxel, antialias, hi-DPI, animaciones, `WindowTransparentForInput`; un solo bucle y una sola librería para todo; gráficas en tiempo real (pyqtgraph) | Reescribir HUD y paneles; convivir con Tk durante la migración | M–L | `WA_TranslucentBackground`, `FramelessWindowHint`, `WindowStaysOnTopHint`, `WindowTransparentForInput` (el visor actual ya lo hace) |
| **D. QML / Qt Quick** (PySide6) | Mejor aspecto (gauges animados, sombras, shaders, temas/skins en QML), GPU scenegraph | Nueva competencia (QML), tests más difíciles, empaquetado algo mayor | L | `color: "transparent"` + flags; igual que C |
| **E. HUD web/Electron/WebView2** | Diseño libre con HTML/CSS | Pesado, otra pila; transparencia/click-through más delicado | L | Posible, no recomendable |
| **F. Overlay por inyección DirectX/hook** | Se dibuja "dentro" del juego (incluso en fullscreen exclusivo) | Riesgo de ToS/antivirus, frágil por versión, fuera de alcance | XL | **No recomendado** |

### 3.2 Recomendación

**C (PySide6 + QPainter, con pyqtgraph para gráficas) como destino**, después de
extraer el núcleo (pasos 1–5). Razones: ya es dependencia, ya demuestra el
patrón de overlay transparente en el visor de checkpoints, da alpha real y un solo
bucle de eventos para la app unificada. Mantener el HUD Tk como backend alternativo
una versión (configurable) y migrar por separado la capa visual, sin tocar la
medición. **D (QML)** es una evolución posible si se quieren skins/animaciones
elaboradas; **A** solo si se quiere una mejora rápida sin unificar aún.

Detalles de implementación a tener en cuenta:
- El HUD debe recibir **valores ya calculados** (modelo de vista); no debe
  influir en el muestreo.
- Evitar robar foco: `Qt.WindowDoesNotAcceptFocus` / `WS_EX_NOACTIVATE`; no
  llamar a `focus_force()` (el HUD Tk actual lo hace al arrancar).
- DPI por monitor (`SetProcessDpiAwareness`/Qt lo gestiona) y posicionar sobre el
  rectángulo de la ventana de GW2 (multi-monitor).
- Evitar `QTimer.start(0.5)` en el visor 3D (CPU innecesaria): sincronizar con
  `uiTick`/25 Hz de la posición y renderizar a la tasa del monitor.

### 3.3 ¿Se puede superponer sobre GW2? Limitaciones

Basado en documentación de Blish HUD y en cómo ya funciona el visor actual `[DOC]`:

- Un overlay como **ventana externa transparente** (sin inyección) **solo se ve
  si GW2 está en modo ventana ("Windowed") o "Windowed Fullscreen" (ventana sin
  bordes a pantalla completa)**. En el modo **Fullscreen exclusivo (DX9)** el
  overlay no se puede mostrar encima. Con DX11 la opción "Full Screen" se
  comporta como windowed-fullscreen, así que **el overlay sí funciona**.
  (Conviene que el HUD avise al usuario si detecta un modo incompatible, p. ej.
  comparando el rectángulo de la ventana con el monitor.)
- No se puede dibujar *dentro* de la escena 3D ni con oclusión por geometría del
  juego; los checkpoints 3D se dibujan **encima** del juego (ya es así hoy).
- **Latencia**: la composición de ventanas añade ~1 frame de retraso; además
  `fAvatarPosition` se actualiza a 25 Hz, por lo que un overlay 3D anclado a la
  posición se verá escalonado, mientras la cámara (por frame) sí es fluida.
- Clic a través: `WS_EX_LAYERED | WS_EX_TRANSPARENT` (Qt:
  `WindowTransparentForInput`). Sin eso el HUD captura clics. El HUD Tk con
  `-transparentcolor` hace clic-through solo en los píxeles transparentes.
- Capturas de pantalla/streaming (OBS "captura de juego") pueden no incluir el
  overlay; usar "captura de ventana/monitor".
- Teclas globales: `pynput` escucha/pulsa teclas a nivel de sistema (también las
  recibe GW2 si tiene el foco). Es otra razón para sustituir esas teclas por IPC.
- Sin inyección no hay riesgo de anti-cheat/ToS asociado al render; MumbleLink es
  una API oficial de solo lectura.

---

## 4. Resumen de decisiones pendientes para el autor

1. ¿Se aceptan, con repetición contra logs reales, cambios que alteren
   `TIME`/tiempos (opciones 5–7)? Por defecto: **no**.
2. ¿Se puede grabar un corpus real (paso 0) y, si se desea, validar con el
   servidor de beetlerank cómo trata cabecera, `\r`, columnas y `TIME`?
3. ¿Unificar sobre Qt (recomendado) o mantener el HUD en Tk?
4. ¿Se eliminan las teclas simuladas `t`/`y` a favor de IPC?
