# Guía de Migración: De MQTT a UDP

Este documento explica cómo el sistema de telemetría UDP actual es **compatible** con el protocolo MQTT del speedometer Beetlerank v6.00.00.

## Resumen de Arquitectura

```
┌─────────────────┐      UDP       ┌─────────────────┐     WebSocket      ┌─────────────────┐
│ Speedometer     │ ──────────────│ Server          │ ──────────────────│ Dashboard       │
│ (MQTT Client)   │   41234/UDP   │ (Este proyecto) │    3002/WSS       │ (Web Browser)   │
└─────────────────┘               └─────────────────┘                   └─────────────────┘
```

**El protocolo usa UDP en lugar de MQTT puro**, pero los mensajes son **100% compatibles** con el formato que el speedometer envía por MQTT.

---

## Comparación de Formatos

### MQTT Original (del Speederometer)

```json
// Topic: gw2speedometer/{session_id}
{
    "option": "s",
    "lap": 1,
    "step": 0,
    "time": 0,
    "user": "nombre_usuario"
}
```

### Sistema UDP Actual

```json
// Enviar a: www.beetlerank.com:41234
{
    "option": "s",
    "lap": 1,
    "step": 0,
    "time": 0,
    "user": "nombre_usuario",
    "sessionCode": 1234
}
```

### Diferencia Principal

| Campo | MQTT Original | Sistema UDP |
|-------|---------------|-------------|
| Topic | `gw2speedometer/{session_id}` | No usa topics (directo al puerto) |
| session_id | En el topic | En campo `sessionCode` |

**El resto del formato es idéntico.**

---

## Mapeo de Mensajes

### 1. Inicio de Carrera (Start)

| Campo | MQTT | UDP |
|-------|------|-----|
| option | `s` | `s` |
| lap | integer | integer |
| step | 0 | 0 |
| time | 0 | 0 |
| user | string | string |
| session_id | En topic | `sessionCode` |

**MQTT:**
```json
{"option": "s", "lap": 1, "step": 0, "time": 0, "user": "Player1"}
```

**UDP:**
```json
{"option": "s", "lap": 1, "step": 0, "time": 0, "user": "Player1", "sessionCode": 1234}
```

---

### 2. Checkpoint

| Campo | MQTT | UDP |
|-------|------|-----|
| option | `c` | `c` |
| step | 1-998 | 1-998 |
| lap | integer | integer |
| time | float | float |
| user | string | string |

**MQTT:**
```json
{"option": "c", "step": 5, "lap": 1, "time": 45.2, "user": "Player1"}
```

**UDP:**
```json
{"option": "c", "step": 5, "lap": 1, "time": 45.2, "user": "Player1", "sessionCode": 1234}
```

---

### 3. Fin de Carrera (Finish)

| Campo | MQTT | UDP |
|-------|------|-----|
| option | `f` | `f` |
| step | 999 | 999 |
| time | float | float |

**MQTT:**
```json
{"option": "f", "lap": 1, "step": 999, "time": 125.5, "user": "Player1"}
```

**UDP:**
```json
{"option": "f", "lap": 1, "step": 999, "time": 125.5, "user": "Player1", "sessionCode": 1234}
```

---

### 4. Posición en Mapa

| Campo | MQTT | UDP |
|-------|------|-----|
| option | `position` | `position` |
| x, y, z | float | float |
| speed | - | float |
| angle | - | float |
| map | string | string |
| color | string | string |

**MQTT:**
```json
{"option": "position", "x": 1234.56, "y": 987.65, "z": 100.0, "user": "Player1", "map": "Rata River", "color": "#FF5733"}
```

**UDP:**
```json
{"option": "position", "x": 1234.56, "y": 987.65, "z": 100.0, "speed": 42.5, "angle": 180.0, "user": "Player1", "sessionCode": 1234, "map": "Rata River", "color": "#FF5733"}
```

**Nota:** El sistema UDP añade campos `speed` y `angle` que no están en el MQTT original pero son útiles para visualización.

---

### 5. Cuenta Regresiva

| Option MQTT | Option UDP |
|------------|-----------|
| `321GO-3` | `321GO-3` |
| `321GO-2` | `321GO-2` |
| `321GO-1` | `321GO-1` |
| `321GO-GO` | `321GO-GO` |

**MQTT:**
```json
{"option": "321GO-3"}
```

**UDP:**
```json
{"option": "321GO-3", "user": "Player1", "sessionCode": 1234}
```

---

### 6. Estados Especiales

| Estado | Step | MQTT | UDP |
|--------|------|------|-----|
| Surrender | 1000 | `{"option": "c", "step": 1000, ...}` | Idéntico + sessionCode |
| Ready | 1001 | `{"option": "c", "step": 1001, ...}` | Idéntico + sessionCode |
| Abandon | 998 | `{"option": "c", "step": 998, ...}` | Idéntico + sessionCode |

---

## Cómo Usar

### Desde el Speedometer (MQTT)

El speedometer se conecta a un broker MQTT y publica en:
```
gw2speedometer/{session_id}
```

Para usar este sistema UDP, necesitarías un **bridge** que:
1. Se suscriba al topic MQTT
2. Reenvíe los mensajes al servidor UDP

### Desde Python (Directo UDP)

```python
import socket
import json

# Conectar al servidor UDP
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
host = "www.beetlerank.com"
port = 41234

# Enviar mensaje de posición
msg = {
    "option": "position",
    "x": 1234.56,
    "y": 987.65,
    "z": 100.0,
    "speed": 42.5,
    "angle": 180.0,
    "user": "MiJugador",
    "sessionCode": 1234,
    "map": "Rata River",
    "color": "#FF5733"
}

sock.sendto(json.dumps(msg, separators=(",", ":")).encode("utf-8"), (host, port))
```

### Demostración

Ejecutar el servidor y luego:

```bash
# Iniciar varios jugadores demo
start_mqtt_style_demo.bat

# O un solo jugador
start_mqtt_style_telemetry.bat --user MiJugador --session-code 1234
```

---

## Códigos de Step

| Step | Significado |
|------|-------------|
| 0 | Inicio de vuelta |
| 1-998 | Checkpoint normal |
| 999 | Vuelta completada |
| 998 | Abandono |
| 1000 | Surrender |
| 1001 | Ready |

---

## Notas de Implementación

1. **UDP no garantiza entrega**: Los mensajes pueden perderse. Para producción, considera TCP o MQTT.
2. **sessionCode reemplaza topic**: El campo `sessionCode` es obligatorio en UDP.
3. **Campos adicionales**: `speed` y `angle` son extensiones del sistema UDP para visualización.
4. **Puerto fijo**: El servidor siempre escucha en el puerto 41234.

---

## Ejemplo: Conexión Directa desde Speedometer

Si modificas el speedometer para usar UDP directamente (sin MQTT):

```python
"""
Ejemplo simple de envío de telemetría UDP
Compatible con Beetlerank Speed Suite v6.00.00
"""

import socket
import json

class TelemetryClient:
    def __init__(self, host="www.beetlerank.com", port=41234):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.host = host
        self.port = port
    
    def send(self, payload):
        """Envía un mensaje al servidor UDP."""
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.sock.sendto(data, (self.host, self.port))
    
    def start(self, user, session_code, lap=1):
        """Envía mensaje de inicio de vuelta."""
        self.send({
            "option": "s",
            "lap": lap,
            "step": 0,
            "time": 0,
            "user": user,
            "sessionCode": session_code
        })
    
    def checkpoint(self, user, session_code, step, lap=1, time=0):
        """Envía mensaje de checkpoint."""
        self.send({
            "option": "c",
            "step": step,
            "lap": lap,
            "time": time,
            "user": user,
            "sessionCode": session_code
        })
    
    def finish(self, user, session_code, lap=1, time=0):
        """Envía mensaje de finish de vuelta."""
        self.send({
            "option": "f",
            "lap": lap,
            "step": 999,
            "time": time,
            "user": user,
            "sessionCode": session_code
        })
    
    def position(self, user, session_code, x, y, z, speed=0, angle=0, lap=1, step=0, time=0, map="", color="#FFFFFF"):
        """Envía mensaje de posición."""
        self.send({
            "option": "position",
            "x": x,
            "y": y,
            "z": z,
            "speed": speed,
            "angle": angle,
            "lap": lap,
            "step": step,
            "time": time,
            "user": user,
            "sessionCode": session_code,
            "map": map,
            "color": color
        })
    
    def countdown(self, user, session_code, value):
        """Envía cuenta regresiva (3, 2, 1, GO)."""
        self.send({
            "option": f"321GO-{value}",
            "user": user,
            "sessionCode": session_code
        })
    
    def ready(self, user, session_code):
        """Envía estado ready."""
        self.send({
            "option": "c",
            "step": 1001,
            "time": 0,
            "lap": 1,
            "user": user,
            "sessionCode": session_code
        })
    
    def surrender(self, user, session_code):
        """Envía surrender/abandono."""
        self.send({
            "option": "c",
            "step": 1000,
            "time": 0,
            "lap": 1,
            "user": user,
            "sessionCode": session_code
        })

# Uso ejemplo
if __name__ == "__main__":
    client = TelemetryClient(host="127.0.0.1", port=41234)
    
    user = "MiJugador"
    session = 1234
    
    # Cuenta regresiva
    for i in ["3", "2", "1"]:
        client.countdown(user, session, i)
    client.countdown(user, session, "GO")
    
    # Listo
    client.ready(user, session)
    
    # Iniciar vuelta
    client.start(user, session, lap=1)
    
    # Enviar posición
    client.position(user, session, x=100, y=50, z=0, speed=25.5, angle=45, time=1.0, map="Rata River", color="#FF5733")
    
    # Checkpoint
    client.checkpoint(user, session, step=1, lap=1, time=10.5)
    
    # Finish
    client.finish(user, session, lap=1, time=60.0)
```

## Configuración del Servidor

El servidor escucha en dos puertos:

| Puerto | Protocolo | Uso |
|--------|------------|-----|
| 41234 | UDP | Mensajes de posición (frecuentes, no críticos) |
| 41235 | TCP | Mensajes críticos (start, checkpoint, finish, countdown) |

Para ejecutar el servidor:

```bash
cd server
npm install
node index.js
```

### Notas del Servidor

- **UDP** (41234): Para mensajes de posición que se envían frecuentemente. Si se pierde algún paquete no es crítico.
- **TCP** (41235): Para mensajes importantes (s, f, c, 321GO-*). El servidor envía ACK por cada mensaje recibido.
- El servidor automáticamente guarda el último estado de cada jugador y lo difunde por WebSocket.
