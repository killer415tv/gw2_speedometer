# TELEMETRY.md — Especificación de compatibilidad de la telemetría

> **Para qué sirve este documento.** Describe *exactamente* cómo el speedometer
> mide, calcula y registra la telemetría, qué formato tienen los logs CSV y qué se
> sube a beetlerank.com. Es la **especificación de compatibilidad**: cualquier
> refactor (unificación, nuevo HUD, optimización) debe producir **los mismos
> bytes de log y los mismos campos de subida**, salvo que se demuestre
> equivalencia con los tests de la sección 11.
>
> - Base de código descrita: rama `easy-install-uv-launcher`, commit de fixes
>   `de1dae7` (la fase 1 **no cambió** ninguna lógica de medición ni el formato;
>   ver sección 12). Referencias `speedometer.py:NNN` = líneas de ese commit.
> - **Fase 3** (optimización sin cambio observable del log, ver §12.1): el
>   comportamiento descrito es el de `de1dae7`/`dddbafa`; lo que cambió
>   internamente (CSV abierto por vuelta, checkpoints precalculados, red en
>   segundo plano) está anotado en las secciones afectadas (§3.1, §5.2, §6) y los
>   tests golden de `tests/golden/` garantizan los mismos bytes/orden. Bugs de
>   medición hallados: `docs/PROBLEMAS_MEDICION.md`.
> - Se leyó el código completo de la ruta de medición. **No hay Windows en el
>   entorno de análisis**: nada de lo marcado `[INFERIDO]` o `[NO VERIFICADO]` se
>   ha medido con GW2 real. Etiquetas usadas:
>   `[CÓDIGO]` = leído directamente del código; `[DOC]` = documentación externa
>   citada; `[INFERIDO]` = deducción razonada/simulada, a confirmar con logs
>   reales; `[NO VERIFICADO]` = desconocido (p. ej. el servidor).
> - El servidor de beetlerank.com **no está en este repositorio**: solo se sabe
>   lo que el cliente envía, no cómo lo valida/usa el servidor.

---

## 1. Visión general del pipeline

```
 GW2 (juego)
   │  memoria compartida "MumbleLink" (Windows, mmap con tagname)
   ▼
 mumblelink.py  ──ml.read()──►  speedometer.py :: Meterv2/Meter.updateMeterTimer()
   (Link + Context)              (callback de Tk, root.after(10 ms))
                                   │ 1. lee MumbleLink (posición, front avatar/cámara, uiState, mapId, identity)
                                   │ 2. comprueba checkpoints (start / * / end / reset)
                                   │ 3. calcula velocidad, ángulos, aceleración
                                   │ 4. escribe fila CSV (append) si hay carrera en curso
                                   │ 5. actualiza HUD (Tk canvas)
                                   │ 6. envía posición multijugador (20 Hz)
                                   ▼
                       logs/<mapa>_log_<epoch>.csv ──(fin de carrera, si "upload")──► POST beetlerank.com/upload-log
```

Hechos clave `[CÓDIGO]`:

1. **Medición, checkpoints, log, HUD y red comparten un único hilo y un único
   bucle** (el `after(10)` de Tk). Todo lo que tarde en la interfaz retrasa el
   muestreo.
2. La velocidad **no usa el tiempo real entre muestras**, sino un divisor
   nominal fijo `timer = 0.01` s (`speedometer.py:192, 1644`).
3. `uiTick` de MumbleLink **se guarda pero no se usa** en ningún cálculo
   (`_tick/_lastTick`, `speedometer.py:1593, 1924`).
4. Una fila CSV se escribe **solo si `velocity > 0`**, es decir, solo en las
   muestras en las que la posición cambió respecto a la muestra anterior.
5. Los tiempos usan `time.time()` (reloj de pared, no monótono). En Python 3.12
   sobre Windows su resolución es la del reloj del sistema (**15,625 ms** salvo
   que otro proceso haya elevado la resolución del temporizador); Python 3.13
   cambió a `GetSystemTimePreciseAsFileTime` (~1 µs) `[DOC]` (docs de Python:
   *time.time, “Changed in version 3.13”*). El proyecto fija Python 3.12
   (`numpy<2`).

Ficheros de estado compartidos entre procesos (IPC "casero") `[CÓDIGO]`, todos
en `gw2_speedometer_internal/`: `guildhall.txt` (mapa), `cup.txt` (copa),
`checkpoint.txt` (siguiente checkpoint), `config.txt` (configuración). Además el
speedometer **simula teclas globales** con `pynput` (`t` al empezar carrera,
`y` al terminar/cambiar mapa; `l`/`k` si LiveSplit está activo) que escuchan los
visores *ghost*.

---

## 2. Fuente de datos: MumbleLink

`mumblelink.py` abre la memoria compartida `MumbleLink`
(`mmap.mmap(-1, len, tagname="MumbleLink")`, solo Windows). Estructura
(`Link` + `Context`) `[CÓDIGO]`/`[DOC]` (wiki GW2 *API:MumbleLink*):

| Campo | Tipo | Uso en la app |
|---|---|---|
| `uiVersion` | uint32 | 0 = juego sin datos (los visores hacen `return`) |
| `uiTick` | DWORD | **no usado** en cálculos |
| `fAvatarPosition[3]` | float32 ×3 | **posición**: [0]=X (este/oeste), [1]=Y (altura), [2]=Z (norte/sur), **metros** |
| `fAvatarFront[3]` | float32 ×3 | dirección del avatar (se usan X y Z) |
| `fCameraFront[3]` | float32 ×3 | dirección de la cámara (X y Z) |
| `fCameraPosition`, `fAvatarTop`, `fCameraTop` | float32 ×3 | solo visores 3D |
| `identity` | wchar[256] (JSON) | `name` (nombre del personaje: se envía como `user` al subir), `fov` |
| `context.mapId`, `uiState` | uint32 | `uiState` en binario de 8 bits, `game_focus = bit índice 4` (juego con foco) |

- Unidades: MumbleLink usa **metros**; el juego usa pulgadas (×39,3701)
  `[DOC]`. La app convierte con `39.3700787` (`speedometer.py:1644`).
- **Frecuencia real de actualización de la posición** `[DOC]` (wiki GW2): "todos
  los valores se actualizan cada frame; `fAvatarPosition` usa una posición
  *estimada* que se sincroniza **25 veces por segundo**". `[INFERIDO]` (ver §4.4):
  el diseño de la fórmula de velocidad es coherente con que la posición cambie
  en escalones de 40 ms.
- `ml.read()` (`mumblelink.py`) copia la memoria a un buffer ctypes en cada
  llamada; no hay *seqlock*/comprobación de coherencia con `uiTick` (posible
  lectura a medias, improbable).
- Tras el commit de fixes: `identity` vacío/inválido (juego cerrado, selección de
  personaje) ya no lanza excepción (`get_identity_name`, `get_identity_fov`).

---

## 3. Bucle de muestreo

`Meterv2.updateMeterTimer` (clase usada por defecto: `hud_gauge_v1 = 0` en
`config.txt`; `Meter` es el gauge "clásico" v1, casi idéntico, ver §10.2).

Orden de operaciones en cada llamada `[CÓDIGO]` (`speedometer.py:1040–1985`):

1. `ml.read()` (l.1561). `game_focus`, `mapId`.
2. `_tick = ml.data.uiTick`; **`_time = time.time()`**; `_last3Dpos = _3Dpos`;
   `_3Dpos = ml.data.fAvatarPosition` (l.1593–1596). `_pos` = `[x, y, z]` si
   `speed_in_3D` o `[x, z]` si no.
3. `if _lastTime + timer <= _time:` (**puerta de muestreo**, `timer = 0.01`)
   (l.1610). Dentro:
   1. `pressedQ = max(pressedQ - timer, 0)`: cuenta atrás del antirrebote de
      checkpoints, **descuenta 0,01 por muestra**, no segundos reales.
   2. Si hay ventana de carrera: `checkpoint(...)` para **cada** fila de
      `checkpoints_list` (pandas `iterrows`, en cada muestra).
   3. `dst = euclidean(_pos, _lastPos)`; `total_distance += dst`;
      **`velocity = dst * 39.3700787 / timer`** (l.1642–1644).
   4. Ángulos, aceleración, escritura de fila CSV, actualización de HUD.
   5. `_lastTime = _time; _lastPos = _pos; _lastTick = _tick`.
4. Envío de posición multijugador (20 Hz) y `root.after(10, ...)` (l.1985).

### 3.1 Cadencia efectiva `[INFERIDO]`

- `after(10)` en Tk/Windows se programa con temporizadores del sistema: la
  cadencia real suele ser ≥ 10 ms, típicamente **~15,6 ms o múltiplos** más el
  coste del propio callback (checkpoints, canvas; hasta la fase 3 también
  `iterrows` por muestra y apertura de fichero por fila).
- Con la puerta `timer = 0.01`, **casi todas las llamadas pasan la puerta**: la
  frecuencia de muestreo = frecuencia del `after` (≈ 30–100 Hz según carga).
- `time.time()` en Python 3.12/Windows puede estar cuantizado a 15,625 ms: en
  ese caso `_time` y todos los `TIME` del CSV serían múltiplos de 1/64 s
  (comprobable en un log real, ver §13).

### 3.2 Cómo se obtienen las magnitudes `[CÓDIGO]`

| Magnitud | Fórmula exacta |
|---|---|
| `dst` (m) | `scipy.spatial.distance.euclidean(_pos, _lastPos)` (2D o 3D según `speed_in_3D`) |
| `velocity` | `dst * 39.3700787 / 0.01` (pulgadas/s **si** el intervalo entre muestras fuera exactamente 10 ms) |
| **`SPEED`** (columna/HUD/red) | `round((velocity * 100 / 10000) * 99 / 72)` = `round(velocity * 99 / 7200)` ≈ `velocity × 0,01375`. Entero. |
| Gauge HUD | `round(velocity*100/10000)` (< 140), `var100` = SPEED |
| `ACCELERATION` | solo si `hud_acceleration` (en `config.txt` entregado = 1; por defecto de código = 0 → columna **0**): `round(((velocity − _lastVel) / (_time − _lastTime)) / 100)` donde `_lastVel` = última velocidad > 0 que se mostró en el HUD (se pone a 0 tras >50 ms parado) y `_time − _lastTime` = intervalo de la **muestra anterior del bucle** (no el intervalo entre las dos actualizaciones de posición comparadas). Solo se calcula si `velocity` y `_lastVel` son ≠ 0; en otro caso 0 |
| `ANGLE_CAM` | ángulo con signo (−180..180) entre el vector de cámara `(fCameraFront.x, fCameraFront.z)` y el vector velocidad `(Δx, Δz)`, ambos unitarios: `degrees(arctan2(cross(v1,v2), dot(v1,v2)))` |
| `ANGLE_BEETLE` | igual con `fAvatarFront` (x, z) |
| `MAP_ANGLE` | `angle_between([0,1], unit(avatarFront(x,z))) + 180` (0..360) |
| `slope` | solo HUD (`hud_slope`), no se registra |

Reglas de borde `[CÓDIGO]` (l.1664–1690): los ángulos solo se recalculan si
`Δx != 0 **and** Δz != 0` (con `or` en la condición de "parado": moverse
exactamente a lo largo de un eje cuenta como "parado" y deja los ángulos en 0).
`np.cross` sobre vectores 2D está **deprecado en NumPy 2** (el pin `numpy<2` es
parte del contrato).

### 3.3 Modo 2D / 3D

`speed_in_3D` se lee de `config.txt` (`speed_in_3d`; el `config.txt` incluido
tiene **`speed_in_3d = 1`**, el valor por defecto del código es 0). Cambia la
definición de `dst`/`SPEED` (incluye o no la altura). Es parte del contrato de
comparabilidad entre jugadores: cualquier unificación debe conservar ese ajuste.

### 3.4 Por qué la fórmula "funciona" con cadencia variable `[INFERIDO]`

Si la posición solo cambia cada 40 ms (25 Hz) y el muestreo es más rápido que
25 Hz, entonces `dst` en las muestras con cambio = desplazamiento de **una**
actualización = `v · 0,04 s`, independientemente de la cadencia exacta, y las
muestras sin cambio dan `velocity = 0` (no se loguean). Con
`SPEED = dst_pulgadas · 100 · 99/7200 = dst_pulgadas · 1,375`, el valor 99
corresponde a **72 pulgadas por actualización = 1800 pulgadas/s**: la constante
`99/72` encaja exactamente con el modelo de "una fila por actualización a 25 Hz".

Simulación orientativa (script en §14, *no* es medición real): velocidad 1800
pulg/s, posición en escalones de 40 ms:

| Escenario de muestreo | filas/s | SPEED (no cero) | notas |
|---|---|---|---|
| 10 ms ideal | 25 | 99 constante | 75 % muestras con `velocity = 0` |
| ~15,6 ms, reloj 15,6 ms (py3.12 típico) | ~25 | 99 constante | separación entre filas 40 ± 8 ms |
| ~15,6 ms + jitter 4 ms | ~25 | 99 y **198** esporádicos | los 198 (≥150) se descartan del log |
| ~33 ms | 25 | 99 | |
| 50 ms (> 40 ms) | **15** | media 124, desv. 43 | pérdida de actualizaciones: SPEED ×2 y filas perdidas |

Conclusión: **la medición es robusta mientras el bucle muestree más rápido que
~25 Hz y no tenga "huecos" > 40 ms**. Si el bucle se atasca (HUD pesado, subida
de log síncrona, antivirus al abrir el fichero…), aparecen SPEED duplicados y
filas perdidas. Esto es una **propiedad a conservar o a mejorar de forma
demostrable**, nunca a cambiar a ciegas.

---

## 4. Checkpoints, vueltas y tiempos

### 4.1 CSV de mapa (entrada) `[CÓDIGO]`

Origen: `https://www.beetlerank.com/uploads/checkpoints/<mapa>.csv` (copas
online, `requests.utils.requote_uri`) o `maps/<mapa>.csv` si la copa es
`OWN MAPS FOLDER`. Columnas: `STEP,STEPNAME,X,Y,Z,RADIUS[,ANGLE]`.
Los creadores (`RACINGcheckpointcreator.py`, `JPcheckpointcreator.py`) escriben
con terminador de línea **`\r`** y valores `str(float32)` sin redondear;
`STEPNAME` ∈ `start` (STEP 0), `*` (intermedios), `end`, `reset` (STEP −1, radio 5).

### 4.2 Algoritmo (`checkpoint()`, `speedometer.py:1125`) `[CÓDIGO]`

- Radio: `RADIUS` de la fila; si es 0 o falta → 5 m (reset) o 15 m (resto).
  Condición de entrada: `euclidean(_3Dpos, punto) < radio` en **3D siempre**
  (aunque `speed_in_3D = 0`), en metros.
- `STEP == -1` (reset/teleport): reinicia carrera (`filename = ""`, `lap = 1`,
  `next_step = 0`).
- Solo se evalúa la fila con `STEP == next_step`. Antirrebote: se acepta si
  `pressedQ == 0` **o** el punto es distinto del último (`different()`).
- `start`: `next_step = 1`; `pressedQ = delaytimer (1)`; si `lap == 1`:
  `total_timer = lap_timer = _time`, crea el fichero de log y escribe la
  cabecera, y manda `option:"s"` al multijugador. Si `lap > 1`: `lap_timer = _time`
  y nuevo fichero de log para esa vuelta (`total_timer` se conserva).
- `*`: `next_step = step + 1`, `pressedQ = 2`; solo HUD + mensaje `"c"`.
- `end`: `next_step = 0`, `pressedQ = 0.5`; cierra el log (`filename = ""`),
  **sube el log** (si `upload == 1` y `log`), y si es la última vuelta calcula el
  tiempo final **leyendo el CSV recién escrito**:
  `datefinish = strftime("%M:%S:%f")[:-3]` de `df.values[-1][6]` (= columna
  `TIME` de la **última fila**). Si no, `lap += 1`.

### 4.3 Definición de los tiempos

| Valor | Cómo se obtiene |
|---|---|
| `TIME` (columna CSV) | `str(_time − lap_timer)` → segundos (float64 con `repr` completo) desde que se **detectó** la entrada en la esfera `start` de **esa vuelta** (el `_time` de la primera muestra dentro del radio, **sin interpolar**) |
| Tiempo final mostrado/registrado (`datefinish`, `*_records.csv`) | `TIME` de la última fila del log de la **última vuelta** (tiempo de vuelta, no el total de la carrera), formateado `MM:SS:mmm` |
| Tiempo HUD en carrera | `_time − total_timer` (total) |
| `time` enviado por red en `s/c/f` | `_time − total_timer` (total, float) |

Consecuencias `[CÓDIGO]`/`[INFERIDO]`:

- La **precisión de un tiempo** es la de la detección: la muestra puede estar
  hasta un periodo de muestreo (~16–40 ms) después del cruce real, y el tiempo
  final es el de la última fila escrita (puede ser hasta ~40 ms anterior a
  detectar `end`, porque `checkpoint()` se ejecuta *antes* de escribir la fila de
  esa muestra).
- Cualquier cambio de cadencia, de reloj o de orden de operaciones **desplaza
  los tiempos oficiales** (±decenas de ms): es "competitivamente observable".
- En carreras multivuelta cada vuelta genera **su propio CSV** y su propia
  subida; el HUD de fin solo muestra el tiempo de la última vuelta.

---

## 5. Formato exacto del log CSV (`logs/`)

### 5.1 Nombre y codificación `[CÓDIGO]`

- Carpeta `gw2_speedometer_internal/logs/` (se crea al empezar).
- Nombre: **`<MAPA>_log_<time.time()>.csv`**, p. ej.
  `Rata River_log_1760790123.109375.csv` (el `repr` del float incluye un punto
  decimal; con reloj de 15,625 ms los decimales son múltiplos de .015625).
- `<MAPA>` = nombre de mapa del servidor **sanitizado** desde fase 1
  (`pathutils.sanitize_map_name`): idéntico para nombres normales; solo cambia
  si contenía separadores/`..`/caracteres inválidos en Windows/nombres reservados/
  >100 caracteres.
- Apertura: `open(path, "a", newline="", encoding="utf-8")`: **UTF-8 sin BOM, sin
  traducción de saltos de línea**.

### 5.2 Estructura `[CÓDIGO]` + verificado con pandas

- **Cabecera** (sin terminador al final):
  `X,Y,Z,SPEED,ANGLE_CAM,ANGLE_BEETLE,TIME,ACCELERATION,MAP_ANGLE`
- **Cada fila va precedida de un `\r` (CR solo, no CRLF)** y no termina en
  salto: el fichero completo es `cabecera \r fila1 \r fila2 … filaN` (**sin
  terminador final**). pandas lo lee bien (`\r` es terminador de línea); cualquier
  "mejora" a `\n` / `\r\n` / terminador final **cambia los bytes**.
- Escritura por fila (**fase 3**): `telemetry_log.LapCsvWriter` mantiene **un solo
  fichero abierto por vuelta** (`open(..., "a", newline="", encoding="utf-8")`) y
  hace `write("\r" + ",".join([...]))` + `flush()` por fila; se cierra al terminar
  la vuelta (antes de leerlo con pandas y de subirlo), al resetear, al cambiar de
  fichero y al salir. Hasta `dddbafa` era `open` → `seek(0,2)` → `writelines("\r")`
  → `writelines(fila)` → cierre en **cada** fila. Los **bytes** y su estado en
  disco tras cada fila son idénticos (test golden con el tamaño del fichero tras
  cada tick).

| # | Columna | Origen | Formato | Unidades / rango |
|---|---|---|---|---|
| 0 | `X` | `fAvatarPosition[0]` | `roundstr` | metros (4 decimales) |
| 1 | `Y` | `fAvatarPosition[1]` | `roundstr` | metros, **altura** |
| 2 | `Z` | `fAvatarPosition[2]` | `roundstr` | metros |
| 3 | `SPEED` | §3.2 | entero (`str(int)`) | "unidades de velocidad" (99 ≈ 1800 pulg/s `[INFERIDO]`); filas con SPEED ≥ 150 **no se escriben** |
| 4 | `ANGLE_CAM` | §3.2 | `roundstr` | grados con signo; 0 si parado/eje |
| 5 | `ANGLE_BEETLE` | §3.2 | `roundstr` | grados con signo |
| 6 | `TIME` | `_time − lap_timer` | `str(float)` completo (repr, ~16–17 cifras) | segundos desde el inicio de **la vuelta** |
| 7 | `ACCELERATION` | §3.2 | `roundstr` | 0 si `hud_acceleration = 0` |
| 8 | `MAP_ANGLE` | §3.2 | `roundstr` | grados 0..360; **en `Meter` v1 es 0 cuando no hay ángulos nuevos; en `Meterv2` conserva el último** (ver §10.2) |

`roundstr(a) = str(round(a * 10000) / 10000)` (Python `round`, redondeo bancario
sobre `a*10000`; los enteros salen como `"0.0"`/`"98"` según tipo).

Ejemplo (bytes reales de una escritura simulada con el mismo código):

```
b'X,Y,Z,SPEED,ANGLE_CAM,ANGLE_BEETLE,TIME,ACCELERATION,MAP_ANGLE\r100.1235,10.5,-200.9877,98,12.3457,-3.21,0.01530003547668457,0.0,181.5\r101.1235,...'
```

**Frecuencia de filas** `[INFERIDO]`: una fila por cada muestra con
`velocity > 0` ⇒ ≈ una por actualización de posición (≈ 25 filas/s en carrera
continua), separadas ~40 ms con jitter de la cadencia del bucle. No hay filas
mientras el personaje está parado.

**Versiones antiguas** `[CÓDIGO]` (visores `ghost_online*.py`): existen logs de
8 columnas (sin `MAP_ANGLE`, al leerlos + `file_name` tienen 9 valores por fila)
y de 9 (con `MAP_ANGLE`). Los consumidores indexan **por posición**
(`values[0]=X … [3]=SPEED … [8]=MAP_ANGLE o file_name`), por lo que **el orden de
columnas es parte del contrato**.

### 5.3 `<MAPA>_records.csv` (local, en `gw2_speedometer_internal/`)

Al terminar la última vuelta (si `log`): `open(<APP>/<MAPA>_records.csv, "a")`,
escribe `\r` + `datefinish,dd/mm/yyyy HH:MM:SS,<nombre personaje>`
(`datefinish` = `MM:SS:mmm`). No se sube.

---

## 6. Subida a beetlerank.com

Disparador `[CÓDIGO]`: al cruzar `end`, si el checkbox **upload** está activo
(`IntVar(value=0)`: **apagado por defecto**) y `log == 1` y existe `filename`.
Se sube **cada vuelta** (un POST por CSV).

```
POST https://www.beetlerank.com/upload-log
Headers: Origin: null, Referer: null
Multipart:  user      = <identity.name del personaje (MumbleLink)>
            guildhall = <nombre de mapa tal cual (guildhall_name), SIN sanitizar>
            file      = <CSV de la vuelta; filename = nombre del fichero, content = bytes del log>
```

- El nombre de fichero del campo `file` es el del log (el `basename` del path) →
  contiene mapa sanitizado + `_log_<epoch>.csv`.
- Respuesta: se muestra `response.text` en el mensaje del HUD solo si
  `total_laps == 1`. Hasta `dddbafa` el hilo se esperaba con `join()` **en el hilo
  de Tk** (bloqueaba el bucle de muestreo hasta 35 s); desde la fase 3 la subida
  corre en el worker `background.jobs` y el texto se muestra al llegar la
  respuesta.
- Tras subir se llama `racer.saveGuildhall(..., in_background=True)`: recarga el
  CSV de checkpoints y consulta el ranking (`GET /rank/api/<mapa>/<usuario>`),
  en el **mismo worker FIFO, después del POST** (orden POST → checkpoints →
  ranking); los resultados se aplican en el hilo de Tk (`background.pump()`).
- Fase 1 (sin cambiar campos ni contenido): `timeout=(5, 30)`, archivo cerrado con
  `with`, errores de red capturados (devuelve `""`), y **no se sube si no hay
  nombre de personaje** (antes: excepción). Verificado por test: el cuerpo
  multipart es idéntico con ruta relativa o absoluta.
- `[NO VERIFICADO]` qué valida el servidor (p. ej. recalcula el tiempo con la
  última fila `TIME`, usa `SPEED`, `Z`, etc.). **Hipótesis a tratar como
  restricción:** el servidor puede depender de cabecera, orden de columnas,
  `\r`, `TIME` de la última fila y nombre del fichero.

Otras llamadas HTTP (todas ahora con `timeout` y `headers=` por keyword desde
fase 1; **antes `headers` se enviaba como parámetros de la query**):

| Endpoint | Uso |
|---|---|
| `GET /api/cups`, `/api/maps/<copa>`, `/api/info` | listas de copas/mapas, mensaje de bienvenida |
| `GET /uploads/checkpoints/<mapa>.csv` | checkpoints del mapa. Fase 3: misma petición `urllib` que hacía `pd.read_csv(url)` (mismas cabeceras) pero con **timeout de 10 s** (`checkpoint_cache.fetch_checkpoint_frame`); al terminar una carrera se descarga en segundo plano |
| `GET /api/top3/<mapa>[/<usuario>]` | ranking: `ranking[*].{time,name,file,pos}`; `file` = URL del log ganador, que los *ghost* descargan |
| `GET /rank/api/<mapa>/<usuario>` | texto de posición del jugador |

---

## 7. Telemetría en vivo (multijugador) `[CÓDIGO]`

Independiente del log; **no** afecta al ranking de tiempos.

- `telemetry_client.TelemetryClient`: **UDP 41234** para `position`, **TCP 41235**
  (JSON + `\n`) para `s`, `f`, `c`, `321GO-*`. JSON compacto
  (`separators=(",",":")`), se añaden `user` (nombre del jugador en `connect`) y
  `sessionCode` (string).
- Recepción: `MultiplayerListener` → `wss://www.beetlerank.com:3002` (snapshots
  `{"type":"snapshot","users":[…],"sessionCodes":[…]}`).
- Posición: como máx. **cada 50 ms** (`round(_time*20)` cambia → ≈ 20 Hz; el README
  dice 30 ms: **discrepancia**), solo si la posición ≠ (0,0,0) y hay
  `velocity > 0` (o una velocidad válida de < 50 ms antes).
  Campos: `option:"position"`, `x,y,z` (float32→float sin redondear), `speed`
  (`round(v*99/7200)`, misma unidad que SPEED), `angle` (= `map_angle`),
  `user`, `map`, `color`.
- Carrera: `s`/`c`/`f` con `lap`, `step` (999 = fin, 998 = fin de vuelta,
  1000 = abandonar, 1001 = listo), `time` (total, segundos).
- WebSocket local opcional (`use_websocket`, `ws://beetlerank.com:1234`): eventos
  `position` con **y/z intercambiados** (`y = pos[2]`, `z = pos[1]`) y
  `countdown_start`.
- Desde fase 1 los mensajes recibidos se validan (`netmsg.py`) y los callbacks no
  propagan excepciones.

---

## 8. Consumidores (qué usa cada script)

| Script | Qué lee | Cadencia / notas |
|---|---|---|
| `launcher.py` | solo lanza procesos (`sys.executable`, `cwd` = carpeta de la app) | no lista `forzaHorizon.py`, `ghost_online_relative_to_user.py`, `web3DPlotter.py` |
| `speedometer.py` | MumbleLink, `maps/*.csv`/web, `config.txt`; **escribe** `logs/*.csv`, `*_records.csv`, `guildhall.txt`, `cup.txt`, `checkpoint.txt`, `config.txt` | bucle Tk 10 ms |
| `checkpoints.py` (visor de checkpoints) | `guildhall.txt`, `cup.txt`, `checkpoint.txt`, CSV de mapa; MumbleLink (cámara/avatar/`fov`); dibuja cilindros 3D (PySide6 + pyqtgraph.opengl) en ventana **transparente, sin marco, topmost, transparente a la entrada**, con la cámara de GW2 sincronizada | `QTimer.start(0.5)` y `start(1)` (`[INFERIDO]` 0,5 ms se trunca a 0 ⇒ temporizador a la máxima frecuencia, CPU alta) |
| `forzaHorizon.py` | mismo que el visor + minijuego (llegar a puntos en tiempo, nivel de dificultad); lee `checkpoint.txt` en cada `update` | `QTimer` de pocos ms |
| `ghost_online.py`, `ghost_online_relative_to_user.py` | logs CSV propios o el log online ganador (`/api/top3` → URL); **columnas por posición** (`X,Y,Z,SPEED,…,MAP_ANGLE`); compara `perf_counter() − filename_timer` (tecla `t`) con `TIME` del punto más cercano (distancia 3D mínima) para mostrar ±tiempo | su reloj es **otro proceso/otro reloj** (`perf_counter`) sincronizado por una pulsación de tecla simulada |
| `map_realtime.py`, `map_realtime_multiplayer.py` | `logs/<mapa>_log*.csv` (`glob`), checkpoint CSV; `X`,`Z` para el mapa 2D; multiplayer: snapshots WSS | `after(...)` con intervalos propios (50 ms en `map_realtime`); el multiplayer ahora se lanza con `--room <código>` |
| `vectors.py` | MumbleLink: vectores de cámara/avatar/velocidad | `QTimer` 0,5/1 ms |
| `JPcheckpointcreator.py`, `RACINGcheckpointcreator.py` | MumbleLink; teclas numéricas (1–4 JP, 5–7… RACING; `t`/`y` también) escriben `maps/NEW.csv` (`STEP,STEPNAME,X,Y,Z,RADIUS[,ANGLE]`, `\r`) | por tecla |
| `web3DPlotter.py` | todos los `*.csv` junto al script con `plotly` (opcional) | un solo disparo |
| `telemetry_client.py`, `netmsg.py`, `pathutils.py`, `mumblelink.py` | librerías | — |

Observaciones: cada visor **duplica** las clases `Link/Context/MumbleLink` y una
clase llamada `Ghost3d` (copiar/pegar ×9). Los visores usan `os.path ... + "\\"`
(solo Windows).

---

## 9. Configuración que altera la telemetría

`config.txt` (sección `[general]`, `RawConfigParser`, claves case-insensitive):

| Clave | Efecto sobre la telemetría |
|---|---|
| `speed_in_3d` | 2D vs 3D en `dst`/`SPEED`/velocidad enviada (incluido: 1) |
| `hud_acceleration` | si 0 → columna `ACCELERATION` = 0 (incluido: 1) |
| `log` | 1 = escribe CSV (necesario para subir) |
| `hud_gauge_v1` | elige `Meter` (v1) o `Meterv2` (diferencias en `MAP_ANGLE`) |
| `show_checkpoints_window` | sin ella no hay checkpoints ni carreras |
| `enable_ghost_keys`, `ghost_start`, `recalculate_ghost`, `enable_livesplit_hotkey`, `live_*` | pulsaciones de teclas globales simuladas |
| `hud_slope`, `hud_altitude`, `hud_angles*`, `hud_max_speed`, `hud_drift_hold`, `hud_distance` | solo HUD (pero ejecutan más trabajo por tick) |

El `config.txt` versionado en el repo es el del autor: los valores por defecto
**de un usuario nuevo** son los de ese fichero (3D, aceleración, etc.), no los
del código.

---

## 10. Quirks y discrepancias detectadas (documentadas, **no corregidas**)

### 10.1 Medición

1. `velocity` usa el divisor nominal `0,01` s, no el intervalo real (§3.4): es
   correcto solo bajo el modelo de "una fila por actualización de posición".
2. `ACCELERATION` mezcla una diferencia de velocidades entre dos *actualizaciones
   de posición* (≈ 40 ms) con un divisor que es el intervalo de la última
   muestra del bucle (≈ 16 ms): **es cadencia-dependiente** y no es una
   aceleración física. Además `calculateAcceleration()` devuelve `None` si
   `velocity`/`_lastVel` son 0 y han pasado < 50 ms desde el último cálculo;
   `roundstr(None)` lanzaría `TypeError`, pero por el orden en que se actualiza
   `_lastVel` el caso parece prácticamente inalcanzable `[INFERIDO]`.
3. `pressedQ` (antirrebote) se descuenta por **muestra** (−0,01), no por
   segundo real ⇒ su duración real depende de la cadencia.
4. Los checkpoints se evalúan **antes** de escribir la fila de la muestra actual.
5. `TIME` se calcula con `time.time()` (no monótono): un ajuste de reloj del
   sistema durante la carrera lo corrompería.

### 10.2 `Meter` (v1) vs `Meterv2`

Diferencias reales en `updateMeterTimer`: (a) en `Meter`, `map_angle` es **local**
(vale 0 cuando no se recalculan ángulos) y el multijugador envía siempre
`angle = 0`; en `Meterv2` es global y conserva el último valor ⇒ **la columna
`MAP_ANGLE` del log difiere entre ambos gauges** cuando hay muestras "paradas
por eje"; (b) `Meterv2` envía además por el websocket local y filtra
posición (0,0,0); (c) geometría y colores del gauge; (d) `hud_altitude`.
`SPEED`, `X,Y,Z`, `TIME`, `ANGLE_*` son idénticos.

### 10.3 Otros

- `Racer.setOnTopfullscreen` compara `game_focus == 1` pero `game_focus` es `str`
  (`"0"/"1"`) ⇒ nunca es cierto.
- El README dice posición cada 30 ms; el código envía cada 50 ms.
- `TelemetryClient.send` sobrescribe `user` con el nombre fijado en `connect()`.
- Varios `Tk()` raíz en el mismo proceso (HUD, panel, cuenta atrás, mensajes,
  TrackMania HUD) comparten el bucle del primero.

---

## 11. Invariantes de compatibilidad y cómo demostrarlas

**No debe cambiar de forma observable** (checklist para cada PR de las fases 3+):

1. Nombre de fichero de log (`<mapa>_log_<time.time()>.csv`) para mapas normales.
2. Codificación UTF-8 sin BOM; cabecera idéntica; `\r` antes de cada fila; sin
   terminador final; mismas 9 columnas y orden.
3. Formato numérico por columna (`roundstr`, SPEED entero, `TIME` = `repr(float)`).
4. Definición de `SPEED` (constantes `39.3700787`, `0.01`, `99/72`), modo 2D/3D,
   filtro `SPEED < 150`, `velocity > 0`.
5. Definición de `TIME`: referencia = detección de `start` de la vuelta; el tiempo
   final = `TIME` de la última fila.
6. Orden de operaciones por muestra (checkpoints → cálculo → fila).
7. Subida: URL, cabeceras, campos `user/guildhall/file`, un POST por vuelta, nombre
   de fichero del multipart, y que `guildhall` se envía sin sanitizar.
8. Frecuencia efectiva de filas (≈ una por actualización de posición) y que el
   muestreo no pierda actualizaciones (§3.4).

**Cómo demostrarlo (propuesta, ver `ANALISIS_FASE2.md`):**

- *Golden de formato y medición (hecho en la fase 3)*: `tests/golden_harness.py`
  extrae con `ast` las clases `Meter`/`Meterv2`/`Racer` (sin refactor), alimenta
  el `updateMeterTimer` **real** con un flujo MumbleLink sintético determinista y
  un reloj simulado, y compara con `tests/golden/` (generados con el código de
  `dddbafa`, antes de optimizar): bytes del CSV, tamaño en disco tras cada tick,
  estado por tick con precisión completa, subidas, mensajes multijugador, teclas.
  Cualquier commit nuevo debe pasarlos **sin regenerarlos**.
- *Golden de medición con repetición*: **grabar en Windows** el flujo crudo de
  MumbleLink (`uiTick`, posición, ffronts, `time.time()` real por muestra) mientras
  se corre la versión actual y se guarda el log; reproducir ese flujo contra el
  código nuevo y exigir logs byte a byte idénticos (o diferencias explicadas).
- *Comparación estadística de cadencia* con los logs reales del autor (§13).

---

## 12. Cambios de fase 1 que tocan esta superficie

Ninguno altera medición, `TIME`, columnas ni campos de subida. Resumen
(commit `de1dae7`):

- `sanitize_map_name`: idéntico para mapas normales (test: lista de nombres
  legítimos); solo afecta a nombre de log/records/CSV de mapas propios y al
  `glob` de los visores (con `glob.escape`).
- `uploadLog`: `with`, timeout, errores capturados, no sube sin nombre; mismos
  campos.
- `requests.get(url, headers)` → `headers=headers` (**cambio observable en el
  servidor**: antes las cabeceras viajaban como query string; ahora como cabeceras
  HTTP `Origin: null`, `Referer: null`, `Accept`) + timeouts.
- `identity` robusto (`""` ⇒ `anon` en HUD/records; sin nombre no se sube).
- Rutas absolutas desde `__file__`; cambio de `python` → `sys.executable`.
- (`pd.read_csv(<url de checkpoints>)` sin timeout: resuelto en la fase 3, ver §12.1.)

### 12.1 Cambios de fase 3 (optimización; ningún cambio observable en el log)

Todos protegidos por los tests golden (`tests/golden/`, `tests/golden_harness.py`:
ver §11) que ejecutan el código **real** de `Meter`/`Meterv2` con un flujo
sintético y reloj simulado y exigen **bytes idénticos** del CSV, mismo tamaño en
disco tras cada tick, mismas subidas, mensajes multijugador y teclas simuladas.

1. `loop_probe.py` (**desactivado por defecto**): con `GW2_SPEEDOMETER_PROBE=1`
   mide, con `perf_counter`, intervalo entre ticks (jitter), duración del tick y
   huecos > 40 ms (actualizaciones de posición posiblemente perdidas); escribe en
   `diagnostics/loop_probe_<epoch>.csv` (+ `.summary.txt`), **nunca** en `logs/`.
2. `telemetry_log.LapCsvWriter`: un fichero abierto por vuelta + `flush` por fila
   (§5.2). Cierre en fin de vuelta, reset (checkpoint `-1` y `Racer.reset`),
   cambio de fichero y `atexit`. Si el proceso muere, lo ya escrito está en disco.
3. `checkpoint_cache.rows_for`: `iterrows()` una vez por mapa (antes en cada
   muestra) y solo se llama a `checkpoint()` para la fila `-1` y la de
   `next_step` (las demás no hacen nada). El cuerpo de `checkpoint()` (float32,
   `euclidean < radio`, antirrebote) no cambia. No se añadió filtro por caja
   (AABB): ahorraría ≤ 2 llamadas a `euclidean` por tick con riesgo en el
   redondeo float32.
4. `background.py`: worker `jobs` (subida → CSV de checkpoints → ranking) y
   worker `net_out` (telemetría UDP/TCP y posición por websocket), ambos FIFO ⇒
   mismo contenido y orden; resultados a Tk vía `pump()`. Una recarga de mapa en
   segundo plano se descarta si el usuario eligió otro mapa mientras tanto.

No se tocaron: reloj (`time.time`), `timer = 0.01`, fórmulas de `SPEED`/`ACCELERATION`,
umbrales (`velocity > 0`, `SPEED < 150`), columnas y orden del CSV, detección de
cruce, orden de operaciones por muestra. Los bugs de medición encontrados están en
`docs/PROBLEMAS_MEDICION.md` (no corregidos).

---

## 13. Verificación con logs reales (para hacer en Windows)

Script para caracterizar un log existente (no modifica nada):

```python
import sys, numpy as np, pandas as pd
df = pd.read_csv(sys.argv[1])
t = df.TIME.values; d = np.diff(t)
print("filas:", len(df), "| duración s:", round(t[-1] - t[0], 3))
print("filas/s:", round(len(df) / (t[-1] - t[0]), 2))
print("dt ms  p5/p50/p95:", np.percentile(d, [5, 50, 95]) * 1000)
print("dt múltiplo de 1/64 s (reloj 15,6 ms):", float((np.abs(d * 64 - np.round(d * 64)) < 1e-6).mean()))
print("SPEED únicos más frecuentes:", df.SPEED.value_counts().head(5).to_dict())
raw = open(sys.argv[1], "rb").read()
print("separador \\r:", raw.count(b"\r"), "| \\n:", raw.count(b"\n"), "| termina en \\r/\\n:", raw[-1:] in (b"\r", b"\n"))
```

Preguntas que respondería con un log real: ¿25 filas/s? ¿`dt` ≈ 40 ms? ¿`TIME`
cuantizado a 1/64 s (⇒ reloj de 15,6 ms)? ¿aparecen `SPEED` duplicados
(huecos del bucle)? Con eso se confirman o refutan los `[INFERIDO]` de §3.

---

## 14. Apéndice: simulación usada en §3.4

Posición en escalones de 40 ms (25 Hz, fase aleatoria), avance constante 1800
pulg/s, mismo algoritmo (`timer`, `velocity`, `SPEED`, filtro `< 150`, fila si
`velocity > 0`). Parámetros por escenario: periodo del bucle (10 ms; 15,625 ms;
15,625 ms con jitter N(0, 4 ms); 31,2 ms; 50 ms) y cuantización de
`time.time()` (ninguna o 15,625 ms). Resultado: ver tabla de §3.4. **Es un modelo,
no una medición**; su valor es mostrar qué propiedades dependen de la cadencia.
