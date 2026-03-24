# Documentación del Protocolo MQTT - Beetlerank Speed Suite v6.00.00

## Descripción General

El speedometer utiliza el protocolo MQTT para comunicarse con otros clientes y compartir información de carrera en tiempo real. Los mensajes se publican en un topic que incluye el ID de sesión.

### Formato del Topic

```
gw2speedometer/{session_id}
```

### Formato del Mensaje

Todos los mensajes son objetos JSON con campos específicos dependiendo del tipo de operación.

---

## Tipos de Mensajes MQTT

### 1. Inicio de Carrera (Start)

**Option:** `s`

**Descripción:** Se envía cuando un corredor inicia una vuelta/checkpoint.

```json
{
    "option": "s",
    "lap": 1,
    "step": 0,
    "time": 0,
    "user": "nombre_usuario"
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `option` | string | Tipo de mensaje: `s` = start |
| `lap` | integer | Número de vuelta actual |
| `step` | integer | Número de checkpoint (0 = inicio) |
| `time` | float | Tiempo en segundos (0 al inicio) |
| `user` | string | Nombre del corredor |

---

### 2. Fin de Carrera (Finish)

**Option:** `f`

**Descripción:** Se envía cuando el corredor termina una vuelta completa.

```json
{
    "option": "f",
    "lap": 1,
    "step": 999,
    "time": 125.5,
    "user": "nombre_usuario"
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `option` | string | Tipo de mensaje: `f` = finish |
| `lap` | integer | Número de vuelta completada |
| `step` | integer | 999 = vuelta completa, 998 = abandono |
| `time` | float | Tiempo total de la vuelta en segundos |
| `user` | string | Nombre del corredor |

---

### 3. Checkpoint (Checkpoint)

**Option:** `c`

**Descripción:** Se envía cuando el corredor pasa por un checkpoint intermedio.

```json
{
    "option": "c",
    "step": 5,
    "lap": 1,
    "time": 45.2,
    "user": "nombre_usuario"
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `option` | string | Tipo de mensaje: `c` = checkpoint |
| `step` | integer | Número del checkpoint (1-999) |
| `lap` | integer | Número de vuelta actual |
| `time` | float | Tiempo acumulado hasta el checkpoint |
| `user` | string | Nombre del corredor |

---

### 4. Posición en Mapa (Map Position)

**Option:** `position`

**Descripción:** Se envía continuamente para mostrar la posición del jugador en el mapa en tiempo real.

```json
{
    "option": "position",
    "x": 1234.56,
    "y": 987.65,
    "z": 100.0,
    "user": "nombre_usuario",
    "map": "Rata River",
    "color": "#FF5733"
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `option` | string | Tipo de mensaje: `position` |
| `x` | float | Coordenada X del jugador |
| `y` | float | Coordenada Y (altitud) del jugador |
| `z` | float | Coordenada Z del jugador |
| `user` | string | Nombre del corredor |
| `map` | string | Nombre del mapa/guild hall |
| `color` | string | Color del jugador en formato hexadecimal |

---

### 5. Cuenta Regresiva (Countdown)

**Option:** `321GO-*`

**Descripción:** Se envía durante la cuenta regresiva antes de una carrera.

```json
{"option": "321GO-3"}
{"option": "321GO-2"}
{"option": "321GO-1"}
{"option": "321GO-GO"}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `option` | string | `321GO-3`, `321GO-2`, `321GO-1`, `321GO-GO` |

---

### 6. Estado de Listo/Abandono (Ready/Surrender)

**Option:** `c` con step especial

**Descripción:** Se envía para indicar estado del jugador.

```json
// Abandono (surrender)
{"option": "c", "step": 1000, "time": 0, "lap": 1, "user": "nombre_usuario"}

// Listo para empezar (ready)
{"option": "c", "step": 1001, "time": 0, "lap": 1, "user": "nombre_usuario"}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `option` | string | `c` = checkpoint (usado para estados) |
| `step` | integer | 1000 = surrender, 1001 = ready |
| `time` | float | Siempre 0 |
| `lap` | integer | Siempre 1 |
| `user` | string | Nombre del corredor |

---

## Códigos de Step Especiales

| Step | Significado | Descripción |
|------|-------------|-------------|
| 0 | Inicio | Punto de partida de la vuelta |
| 1-998 | Checkpoint | Checkpoints intermedios normales |
| 999 | Finish | Vuelta completada correctamente |
| 998 | Abandon | Carrera abandonada antes de terminar |
| 1000 | Surrender | Jugador se rinde/abandona |
| 1001 | Ready | Jugador está listo para competir |

---

## Ejemplo de Flujo de Carrera

```
1. Usuario inicia carrera:
   {"option": "s", "lap": 1, "step": 0, "time": 0, "user": "Player1"}

2. Pasa checkpoint 1 (a los 10 segundos):
   {"option": "c", "step": 1, "lap": 1, "time": 10.0, "user": "Player1"}

3. Pasa checkpoint 2 (a los 25 segundos):
   {"option": "c", "step": 2, "lap": 1, "time": 25.0, "user": "Player1"}

4. Llega al finish (a los 60 segundos):
   {"option": "f", "lap": 1, "step": 999, "time": 60.0, "user": "Player1"}

5. Inicia segunda vuelta:
   {"option": "s", "lap": 2, "step": 0, "time": 0, "user": "Player1"}
```

---

## Configuración del Servidor MQTT

El speedometer se conecta a un broker MQTT configurado. Los parámetros de conexión se configuran en el archivo `config.txt`:

```
mqtt_server = broker.beetlerank.com
mqtt_port = 1883
mqtt_user = usuario
mqtt_password = contraseña
mqtt_topic_prefix = gw2speedometer/
```

---

## Notas

- Los mensajes de posición se envían aproximadamente cada 0.5 segundos
- El topic incluye un session_id único para cada sesión de carrera
- El formato es compatible con el servidor MQTT de Beetlerank para rankings online
