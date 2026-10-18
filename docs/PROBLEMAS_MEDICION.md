# PROBLEMAS_MEDICION.md — Bugs/rarezas que afectan a la medición (NO corregidos)

> Detectados durante la fase 3 al construir los tests golden. **Ninguno se ha
> corregido**: todos pueden cambiar logs, tiempos o el comportamiento visible y
> la decisión es de Guillermo. Cada entrada indica evidencia reproducible (test
> o escenario golden), efecto, propuesta y riesgo para la compatibilidad
> competitiva. Etiquetas: `[VERIFICADO]` = reproducido con el código real en los
> tests (Linux, sin GW2); `[INFERIDO]` = deducido del código.

Resumen:

| ID | Problema | Gravedad | Riesgo de arreglarlo |
|---|---|---|---|
| PM-01 | `Meter` (gauge v1) + sesión multijugador ⇒ `UnboundLocalError` y el bucle muere | Media (v1 no es el gauge por defecto) | Bajo |
| PM-02 | `log = 0` y terminar la carrera ⇒ `FileNotFoundError` y el bucle muere | Media | Bajo |
| PM-03 | Cualquier excepción en `updateMeterTimer` detiene el muestreo para siempre | Alta (amplifica PM-01/02/…) | Bajo/Medio |
| PM-04 | Si falla la recarga de checkpoints, la lista queda **vacía** | Media | Bajo |
| PM-05 | Mapa con `end` y `start` en la misma esfera: el `start` de la vuelta siguiente se pierde o se retrasa ~0,8 s (cadencia-dependiente) | Alta para multivuelta | Alto (cambia tiempos) |
| PM-06 | Terminar en la esfera de `start` inicia una carrera nueva y deja un CSV vacío (solo cabecera) en `logs/` | Baja | Bajo/Medio |
| PM-07 | Cambiar de mapa a mitad de carrera sigue escribiendo en el log del mapa anterior | Baja | Medio |

---

## PM-01 — `Meter` (v1) + multijugador: `UnboundLocalError: map_angle`

- **Dónde:** `Meter.updateMeterTimer`. Asigna `map_angle` (rama de ángulos) sin
  declararla `global` en esa función ⇒ es local; el envío de posición
  multijugador (antes de esa asignación) la lee: `"angle": map_angle`.
- **Evidencia `[VERIFICADO]`:** golden `v1_session_unbound_map_angle`
  (`tests/golden/…/result.json`, `exceptions`): `UnboundLocalError` en la primera
  muestra con `velocity > 0` y sesión activa.
- **Efecto:** con el gauge v1 (`hud_gauge_v1 = 1`) y una sala multijugador, la
  excepción sale del callback de Tk ⇒ ver PM-03 (deja de medir). Con el gauge v2
  (por defecto) no ocurre.
- **Propuesta:** inicializar `map_angle = 0` al principio de `Meter.updateMeterTimer`
  (conserva la semántica v1 de `MAP_ANGLE` en el CSV, arregla solo el crash). La
  alternativa (`global map_angle`, como v2) **cambiaría la columna `MAP_ANGLE` de
  los usuarios v1**.
- **Riesgo:** bajo con la propuesta (el CSV no cambia en los casos en que hoy
  funciona).

## PM-02 — `log = 0` y terminar la carrera ⇒ `FileNotFoundError`

- **Dónde:** rama `end` de `checkpoint()`: `filename` se asigna aunque `log == 0`
  y al llegar a la meta (última vuelta) se hace `pd.read_csv(logs/<filename>)`
  incondicionalmente para sacar el tiempo final.
- **Evidencia `[VERIFICADO]`:** golden `v2_log_disabled`: `FileNotFoundError` en
  el tick de cruce de meta; no se muestra el tiempo final, no se actualizan
  vueltas/estado ni se llega a `records`.
- **Efecto:** con "Log to file" desactivado, el primer final de carrera rompe el
  bucle (PM-03). No afecta a logs subidos (sin log no se sube).
- **Propuesta:** calcular el tiempo final desde memoria (último `TIME` escrito) o
  saltar la lectura si `log == 0`. Mantener la lectura del CSV cuando `log == 1`
  para no tocar el valor.
- **Riesgo:** bajo si el valor con `log == 1` sigue saliendo del CSV.

## PM-03 — Una excepción en `updateMeterTimer` detiene la medición

- **Dónde:** `self.root.after(10, self.updateMeterTimer)` está al final; cualquier
  excepción previa lo salta. Tk imprime el traceback y el HUD queda congelado.
- **Casos conocidos:** PM-01, PM-02, `roundstr(None)` si `calculateAcceleration()`
  devolviera `None` (TELEMETRY §10.1.2; no reproducido), CSV de mapa con
  columnas ausentes (`KeyError`), fallo de escritura del log (disco lleno), CSV
  de la vuelta sin filas al llegar a `end` (`IndexError` en `values[-1]`).
- **Propuesta:** reprogramar el `after` en un `try/finally` (y registrar el
  error). Los tests golden ya capturan las excepciones por tick.
- **Riesgo:** bajo para los logs válidos (no cambian); cambia el modo de fallo:
  el bucle seguiría con el estado posiblemente inconsistente tras el error.

## PM-04 — Recarga fallida de checkpoints ⇒ lista vacía

- **Dónde:** `Racer.saveGuildhall`: `checkpoints_list = pd.DataFrame()` se asigna
  **antes** de `read_csv`; si falla (red caída, timeout), la lista queda vacía.
  Se llama al terminar cada carrera con subida activa.
- **Evidencia `[VERIFICADO]`:** `tests/test_net_flow.py::test_failed_checkpoint_download_empties_list_like_before`.
- **Efecto:** un fallo de red tras una carrera deja al usuario sin checkpoints
  (ninguna carrera nueva arranca) hasta reseleccionar el mapa; no hay aviso.
- **Fase 3:** se conserva exactamente (la recarga ahora es en segundo plano y con
  timeout de 10 s, lo que hace el fallo *más* probable que cuando colgaba).
- **Propuesta:** conservar la lista anterior si la recarga falla (y avisar).
- **Riesgo:** bajo.

## PM-05 — `end` y `start` en la misma esfera: pérdida/retraso del `start` de la vuelta siguiente

- **Dónde:** `checkpoint()`: tras `end` se fija `pressedQ = 0.5`, que
  baja 0,01 **por muestra** (50 muestras ≈ 0,5 s a 100 Hz, **≈ 0,8 s a ~64 Hz**);
  mientras tanto el `start` (mismas coordenadas ⇒ `different()` es falso) no se
  acepta.
- **Evidencia `[VERIFICADO]`:**
  - `v2_end_equals_start_2laps_debounce` (SPEED 99 ≈ 45 m/s): cruzar una esfera
    de 15 m dura ~0,66 s < 0,8 s ⇒ el `start` de la vuelta 2 **no se detecta** en
    ese paso; la vuelta 2 solo empieza al pasar de nuevo por la esfera.
  - `v2_end_equals_start_2laps_slow_at_start` (11 m/s en la esfera): la vuelta 2
    arranca **≈ 0,86 s** después de la entrada (la vuelta 2 se mide ~0,86 s más
    corta de lo que correspondería a la entrada en la esfera).
- **Efecto:** en mapas multivuelta con `end` = `start`, el origen de `TIME` de la
  vuelta ≥ 2 depende de la cadencia del bucle (y de la velocidad). Hoy es el
  comportamiento "oficial".
- **Propuesta:** descontar `pressedQ` con tiempo real (`_time`) en vez de por
  muestra, o permitir el `start` si la esfera se abandonó y se reentró.
- **Riesgo:** **alto**: cambia los tiempos de vuelta ≥ 2 ⇒ solo con acuerdo del
  servidor/ranking.

## PM-06 — Terminar en la esfera de `start` inicia una carrera nueva

- **Evidencia `[VERIFICADO]`:** `v2_end_equals_start_2laps_slow_at_start`: tras
  `TF` de la última vuelta aparece `1/2 T0 00:00:000` y se crea un tercer CSV
  con solo la cabecera (62 bytes, 0 filas) en `logs/`.
- **Efecto:** ficheros residuales en `logs/` (los visores `glob`ean `logs/`);
  no se sube (no hay `end`). Es una carrera "fantasma" hasta el siguiente reset.
- **Propuesta:** no crear el fichero hasta la primera fila, o ignorar `start`
  durante el debounce de `end` también con vueltas completas.
- **Riesgo:** bajo/medio (los visores esperan que exista el fichero de la vuelta
  en curso; revisar `ghost_online*.py`).

## PM-07 — Cambiar de mapa durante una carrera

- **Evidencia `[VERIFICADO]`:** golden `v2_map_change_during_race`: `saveGuildhall`
  no toca `filename`; el log sigue en el fichero del mapa anterior mientras
  `guildhall_name` (usado como campo `guildhall` de la subida y para
  `<mapa>_records.csv`) ya es el nuevo (`Another Map_records.csv`).
- **Efecto:** si la carrera se completara tras el cambio, se subiría el CSV del
  mapa A con `guildhall = B`. En la práctica la lista de checkpoints cambia a B,
  así que el `end` de A no se detecta; el riesgo real es un log huérfano.
- **Propuesta:** cerrar la carrera en curso (`filename = ""`) al cambiar de mapa.
- **Riesgo:** medio (cambia qué ocurre con un log a medias).

---

### Efectos secundarios documentados de la fase 3 (no son bugs de medición)

- **Subida/ranking en segundo plano.** En carreras de 1 vuelta el mensaje con la
  respuesta de la subida ya no bloquea el bucle: aparece cuando llega la
  respuesta. Orden de peticiones: POST de subida → GET del CSV de checkpoints →
  GET del ranking (en multivuelta antes el POST iba en paralelo a los GET).
- **CSV abierto durante la vuelta.** Mientras se corre, el CSV de la vuelta está
  abierto (con `flush` por fila); en Windows no se puede borrar/renombrar ese
  fichero hasta terminar o resetear la carrera. El contenido en disco tras cada
  fila es idéntico al de antes.
