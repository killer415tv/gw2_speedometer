"""
Módulo de Telemetría UDP/TCP para Beetlerank Speed Suite v6

Este módulo reemplaza las comunicaciones MQTT por UDP/TCP:
- UDP (puerto 41234): Para mensajes de posición frecuentes
- TCP (puerto 41235): Para mensajes críticos (start, checkpoint, finish, countdown)
- WebSocket (wss://www.beetlerank.com:3002): Para recibir snapshots de multijugador
"""

import socket
import json
import logging
import random
import threading
import time

try:
    from websocket import WebSocketTimeoutException
except ImportError:  # websocket-client missing: MultiplayerListener reports it on start()
    WebSocketTimeoutException = socket.timeout

log = logging.getLogger(__name__)

# Reconnection backoff (seconds): doubles after every failed attempt up to the max.
TCP_RECONNECT_MIN_DELAY = 2.0
TCP_RECONNECT_MAX_DELAY = 30.0
WS_RECONNECT_MIN_DELAY = 2.0
WS_RECONNECT_MAX_DELAY = 60.0


def _backoff_delay(failures, min_delay, max_delay):
    """Exponential backoff: min_delay * 2**(failures-1), capped at max_delay."""
    failures = max(1, int(failures))
    return min(max_delay, min_delay * (2 ** min(failures - 1, 30)))


def _safe_close(sock, what):
    """Close a socket-like object; a failure is logged, never raised."""
    if sock is None:
        return
    try:
        sock.close()
    except Exception as exc:
        log.debug("Error closing %s: %s", what, exc)


# Configuración del servidor (valores fijos)
TELEMETRY_HOST = "www.beetlerank.com"
TELEMETRY_UDP_PORT = 41234
TELEMETRY_TCP_PORT = 41235
TELEMETRY_WS_PORT = 3002
TELEMETRY_WS_URL = f"wss://{TELEMETRY_HOST}:{TELEMETRY_WS_PORT}"

# Opciones que van por TCP (críticos - requieren ACK)
TCP_OPTIONS = ["s", "f", "c", "321GO-GO", "321GO-3", "321GO-2", "321GO-1"]

# Opciones que van por UDP (frecuentes - no críticos)
UDP_OPTIONS = ["position"]


class TelemetryClient:
    """
    Cliente de telemetría para comunicaciones multiplayer.
    
    Uso:
        client = TelemetryClient()
        client.connect("player1", "session123")
        
        # Enviar posición (UDP)
        client.send_position(x=100, y=50, z=0, speed=25.5, angle=45)
        
        # Enviar start (TCP)
        client.send_start(lap=1)
        
        # Enviar checkpoint (TCP)
        client.send_checkpoint(step=5, lap=1, time=45.2)
        
        # Enviar finish (TCP)
        client.send_finish(lap=1, time=125.5)
    """
    
    def __init__(self, host=TELEMETRY_HOST, udp_port=TELEMETRY_UDP_PORT, tcp_port=TELEMETRY_TCP_PORT):
        self.host = host
        self.udp_port = udp_port
        self.tcp_port = tcp_port
        
        # Socket UDP (para envíos frecuentes)
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Socket TCP (para mensajes críticos)
        self.tcp_socket = None
        self.tcp_connected = False
        
        # Datos de sesión
        self.username = ""
        self.session_code = ""
        
        # Callback para mensajes recibidos
        self.on_message_callback = None
        
        # Hilo para recibir mensajes TCP
        self.receive_thread = None
        self.running = False

        # Reconexión TCP con backoff (monotonic timestamp del próximo intento)
        self._tcp_failures = 0
        self._tcp_next_attempt = 0.0
        self._tcp_lock = threading.Lock()
    
    def connect(self, username, session_code):
        """
        Configura la conexión con el nombre de usuario y código de sesión.
        
        Args:
            username: Nombre del jugador
            session_code: Código de sesión de la carrera
        """
        self.username = username
        self.session_code = session_code
        
        # Conectar TCP para mensajes críticos
        self._connect_tcp()
        
        # Iniciar hilo de recepción
        self.running = True
        self.receive_thread = threading.Thread(target=self._receive_tcp_loop, daemon=True)
        self.receive_thread.start()
    
    def _connect_tcp(self):
        """Establece la conexión TCP con el servidor."""
        with self._tcp_lock:
            if self.tcp_connected and self.tcp_socket:
                return  # otro hilo ya reconectó
            self._connect_tcp_locked()

    def _connect_tcp_locked(self):
        _safe_close(self.tcp_socket, "TCP socket")
        self.tcp_socket = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket = sock
            sock.settimeout(5.0)
            sock.connect((self.host, self.tcp_port))
            self.tcp_connected = True
            self._tcp_failures = 0
            self._tcp_next_attempt = 0.0
            print(f"TCP connected to {self.host}:{self.tcp_port}")
        except Exception as e:
            self.tcp_connected = False
            _safe_close(self.tcp_socket, "TCP socket")
            self.tcp_socket = None
            self._tcp_failures += 1
            delay = _backoff_delay(
                self._tcp_failures, TCP_RECONNECT_MIN_DELAY, TCP_RECONNECT_MAX_DELAY
            )
            self._tcp_next_attempt = time.monotonic() + delay
            log.warning(
                "TCP connection failed (attempt %d): %s - retrying in %.0fs",
                self._tcp_failures, e, delay,
            )

    def _mark_tcp_disconnected(self, reason):
        """Marca la conexión TCP como caída y programa un reintento con backoff."""
        log.warning("TCP connection lost: %s", reason)
        self.tcp_connected = False
        _safe_close(self.tcp_socket, "TCP socket")
        self.tcp_socket = None
        # Primer reintento rápido; si falla, _connect_tcp aplica el backoff.
        self._tcp_next_attempt = time.monotonic() + TCP_RECONNECT_MIN_DELAY

    def _dispatch_line(self, line):
        """Decodifica una línea JSON recibida y llama al callback sin propagar errores."""
        try:
            message = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as e:
            log.warning("Ignoring malformed TCP message: %s", e)
            return
        if not isinstance(message, dict):
            log.warning("Ignoring TCP message that is not a JSON object")
            return
        if self.on_message_callback:
            try:
                self.on_message_callback(message)
            except Exception:
                log.exception("Error in TCP message callback")

    def _receive_tcp_loop(self):
        """Hilo para recibir mensajes del servidor por TCP (y reconectar si cae)."""
        buffer = b""

        while self.running:
            if not (self.tcp_socket and self.tcp_connected):
                # Reintento en este hilo (no bloquea la UI), respetando el backoff.
                if time.monotonic() >= self._tcp_next_attempt:
                    buffer = b""
                    self._connect_tcp()
                time.sleep(0.1)
                continue

            try:
                self.tcp_socket.setblocking(False)
                data = self.tcp_socket.recv(4096)
            except BlockingIOError:
                data = None
            except Exception as e:
                if self.running:
                    self._mark_tcp_disconnected(e)
                continue

            if data == b"":
                if self.running:
                    self._mark_tcp_disconnected("closed by server")
                continue
            if data:
                buffer += data
                # Procesar mensajes completos (separados por newline)
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    self._dispatch_line(line)
            time.sleep(0.1)

    def disconnect(self):
        """Cierra las conexiones y detiene los hilos."""
        self.running = False
        
        _safe_close(self.tcp_socket, "TCP socket")
        _safe_close(self.udp_socket, "UDP socket")
    
    def _should_use_tcp(self, option):
        """Determina si el mensaje debe enviarse por TCP."""
        # Si la opción contiene "321GO" va por TCP
        if "321GO" in option:
            return True
        
        # Si es una de las opciones definidas como TCP
        if option in TCP_OPTIONS:
            return True
        
        return False
    
    def _add_session_info(self, data):
        """Añade la información de sesión al mensaje."""
        data["user"] = self.username
        if self.session_code:
            data["sessionCode"] = self.session_code
        return data
    
    def send(self, data):
        """
        Envía un mensaje al servidor, eligiendo automáticamente UDP o TCP.
        
        Args:
            data: Diccionario con los datos del mensaje
        """
        # Añadir info de sesión
        data = self._add_session_info(data)
        
        # Convertir a JSON
        json_data = json.dumps(data, separators=(",", ":")).encode("utf-8")
        
        # Elegir protocolo según el tipo de mensaje
        option = data.get("option", "")
        
        if self._should_use_tcp(option):
            self._send_tcp(json_data)
        else:
            self._send_udp(json_data)
    
    def _send_udp(self, data):
        """Envía datos por UDP."""
        try:
            self.udp_socket.sendto(data, (self.host, self.udp_port))
        except Exception as e:
            print(f"UDP send error: {e}")
    
    def _send_tcp(self, data):
        """Envía datos por TCP con ACK."""
        if not self.tcp_connected and time.monotonic() >= self._tcp_next_attempt:
            self._connect_tcp()
        
        if self.tcp_socket and self.tcp_connected:
            try:
                # Enviar datos con newline como delimitador
                self.tcp_socket.sendall(data + b"\n")
            except Exception as e:
                self._mark_tcp_disconnected(f"send error: {e}")
        else:
            log.debug("TCP not connected: message dropped (reconnect pending)")
    
    # Métodos de conveniencia para tipos específicos de mensajes
    
    def send_start(self, lap=1, step=0, time=0):
        """Envía mensaje de inicio de vuelta."""
        self.send({
            "option": "s",
            "lap": lap,
            "step": step,
            "time": time
        })
    
    def send_finish(self, lap=1, step=999, time=0):
        """Envía mensaje de finish de vuelta."""
        self.send({
            "option": "f",
            "lap": lap,
            "step": step,
            "time": time
        })
    
    def send_checkpoint(self, step, lap=1, time=0):
        """Envía mensaje de checkpoint."""
        self.send({
            "option": "c",
            "step": step,
            "lap": lap,
            "time": time
        })
    
    def send_position(self, x, y, z, speed=0, angle=0, lap=1, step=0, time=0, map="", color="#FFFFFF"):
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
            "map": map,
            "color": color
        })
    
    def send_countdown(self, value):
        """
        Envía mensaje de cuenta regresiva.
        
        Args:
            value: "3", "2", "1", "GO"
        """
        option = f"321GO-{value}"
        if value == "GO":
            option = "321GO-GO"
        
        self.send({"option": option})
    
    def send_ready(self):
        """Envía estado de listo (ready)."""
        self.send({
            "option": "c",
            "step": 1001,
            "time": 0,
            "lap": 1
        })
    
    def send_surrender(self):
        """Envía estado de abandono (surrender)."""
        self.send({
            "option": "c",
            "step": 1000,
            "time": 0,
            "lap": 1
        })
    
    def set_message_callback(self, callback):
        """Establece un callback para mensajes recibidos."""
        self.on_message_callback = callback


class TelemetryListener:
    """
    Receptor de telemetría UDP/TCP para recibir datos de otros jugadores.
    
    Uso:
        def on_position(data):
            print(f"Position: {data['user']} at {data['x']}, {data['y']}")
        
        listener = TelemetryListener()
        listener.set_position_callback(on_position)
        listener.start()
    """
    
    def __init__(self, session_code=None, options=None, udp_port=TELEMETRY_UDP_PORT, tcp_port=TELEMETRY_TCP_PORT):
        self.session_code = session_code
        self.options = options or ["position"]  # Default to position messages
        self.udp_port = udp_port
        self.tcp_port = tcp_port
        
        self.udp_socket = None
        self.tcp_server = None
        self.running = False
        
        # Callbacks
        self.position_callback = None
        self.start_callback = None
        self.finish_callback = None
        self.checkpoint_callback = None
        self.countdown_callback = None
        self.other_callback = None
    
    def _should_process_message(self, message):
        """
        Determina si el mensaje debe ser procesado según session_code y options.
        
        Returns:
            bool: True si el mensaje debe procesarse
        """
        # Filtrar por session_code si está configurado
        if self.session_code:
            msg_session = message.get("sessionCode", "")
            if msg_session != self.session_code:
                return False
        
        # Filtrar por options si está configurado
        if self.options:
            option = message.get("option", "")
            if option not in self.options:
                return False
        
        return True
    
    def start(self):
        """Inicia los servidores de escucha."""
        self.running = True
        
        # Iniciar servidor UDP
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.bind(("", self.udp_port))
        self.udp_socket.settimeout(1.0)
        
        # Hilo UDP
        self.udp_thread = threading.Thread(target=self._udp_loop, daemon=True)
        self.udp_thread.start()
        
        # Hilo TCP servidor
        self.tcp_thread = threading.Thread(target=self._tcp_server_loop, daemon=True)
        self.tcp_thread.start()
    
    def stop(self):
        """Detiene los servidores."""
        self.running = False
        
        _safe_close(self.udp_socket, "UDP listener socket")
        _safe_close(self.tcp_server, "TCP listener socket")
    
    def _udp_loop(self):
        """Bucle de recepción UDP."""
        while self.running:
            try:
                data, addr = self.udp_socket.recvfrom(4096)
                message = json.loads(data.decode("utf-8"))
                self._handle_message(message)
            except socket.timeout:
                pass
            except Exception as e:
                if self.running:
                    print(f"UDP receive error: {e}")
    
    def _tcp_server_loop(self):
        """Bucle del servidor TCP."""
        self.tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.tcp_server.bind(("", self.tcp_port))
            self.tcp_server.listen(5)
            self.tcp_server.settimeout(1.0)
            
            while self.running:
                try:
                    client_socket, addr = self.tcp_server.accept()
                    thread = threading.Thread(
                        target=self._handle_tcp_client,
                        args=(client_socket,),
                        daemon=True
                    )
                    thread.start()
                except socket.timeout:
                    pass
                except Exception as e:
                    if self.running:
                        print(f"TCP server error: {e}")
        except Exception as e:
            print(f"TCP server bind error: {e}")
    
    def _handle_tcp_client(self, client_socket):
        """Maneja un cliente TCP conectado."""
        buffer = b""
        
        try:
            client_socket.settimeout(5.0)
            
            while self.running:
                try:
                    data = client_socket.recv(4096)
                    if not data:
                        break
                    
                    buffer += data
                    
                    # Procesar mensajes completos
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        try:
                            message = json.loads(line.decode("utf-8"))
                            self._handle_message(message)
                        except (UnicodeDecodeError, ValueError) as e:
                            log.warning("Ignoring malformed TCP message: %s", e)
                        except Exception:
                            log.exception("Error handling TCP message")
                except socket.timeout:
                    break
        except Exception as e:
            print(f"TCP client error: {e}")
        finally:
            client_socket.close()
    
    def _handle_message(self, message):
        """Procesa un mensaje recibido."""
        if not isinstance(message, dict):
            log.warning("Ignoring message that is not a JSON object")
            return
        # Verificar si el mensaje debe ser procesado
        if not self._should_process_message(message):
            return
        
        option = message.get("option", "")
        
        if option == "position":
            if self.position_callback:
                self.position_callback(message)
        elif option == "s":
            if self.start_callback:
                self.start_callback(message)
        elif option == "f":
            if self.finish_callback:
                self.finish_callback(message)
        elif option == "c":
            step = message.get("step", 0)
            if step in [1000, 1001]:
                # Ready/Surrender
                if self.checkpoint_callback:
                    self.checkpoint_callback(message)
            elif self.checkpoint_callback:
                self.checkpoint_callback(message)
        elif "321GO" in option:
            if self.countdown_callback:
                self.countdown_callback(message)
        elif self.other_callback:
            self.other_callback(message)
    
    def set_position_callback(self, callback):
        """Establece callback para mensajes de posición."""
        self.position_callback = callback
    
    def set_start_callback(self, callback):
        """Establece callback para mensajes de inicio."""
        self.start_callback = callback
    
    def set_finish_callback(self, callback):
        """Establece callback para mensajes de finish."""
        self.finish_callback = callback
    
    def set_checkpoint_callback(self, callback):
        """Establece callback para mensajes de checkpoint."""
        self.checkpoint_callback = callback
    
    def set_countdown_callback(self, callback):
        """Establece callback para mensajes de cuenta regresiva."""
        self.countdown_callback = callback
    
    def set_other_callback(self, callback):
        """Establece callback para otros mensajes."""
        self.other_callback = callback


class MultiplayerListener:
    """
    Receptor de telemetría por WebSocket para recibir datos de otros jugadores.
    
    Se conecta a wss://www.beetlerank.com:3002 y recibe snapshots con las posiciones
    de todos los jugadores activos en las sesiones.
    
    Uso:
        def on_snapshot(data):
            for user in data['users']:
                print(f"{user['user']}: x={user['x']}, y={user['y']}")
        
        listener = MultiplayerListener()
        listener.set_snapshot_callback(on_snapshot)
        listener.start()
    """
    
    def __init__(self, session_code=None, ws_url=TELEMETRY_WS_URL):
        self.session_code = session_code  # Filtrar por sesión específica (opcional)
        self.ws_url = ws_url
        
        self.running = False
        self.ws_client = None
        self.ws_thread = None
        
        # Callbacks
        self.snapshot_callback = None

        # Reconexión con backoff
        self._lock = threading.Lock()
        self._retry_timer = None
        self._failures = 0
    
    def start(self):
        """Inicia la conexión WebSocket (sin bloquear: conecta en segundo plano)."""
        if self.running:
            return
            
        self.running = True
        self._failures = 0
        self._schedule_connect(0)

    def _open_connection(self):
        """Abre la conexión WebSocket (separado para poder sustituirlo en tests)."""
        # Importar aquí para evitar problemas si no está instalado
        from websocket import create_connection
        return create_connection(self.ws_url, timeout=5)

    def _schedule_connect(self, delay):
        """Programa un intento de conexión en un hilo temporizador (no bloquea)."""
        with self._lock:
            if not self.running:
                return
            timer = threading.Timer(delay, self._connect)
            timer.daemon = True
            self._retry_timer = timer
            timer.start()

    def _next_retry_delay(self):
        """Backoff exponencial acotado, con algo de jitter para no sincronizar clientes."""
        delay = _backoff_delay(
            self._failures, WS_RECONNECT_MIN_DELAY, WS_RECONNECT_MAX_DELAY
        )
        return delay + random.uniform(0, delay * 0.2)

    def _connect(self):
        """Conecta al servidor WebSocket; si falla, reintenta con backoff."""
        if not self.running:
            return
        try:
            ws = self._open_connection()
        except ImportError:
            log.error("websocket-client not installed (pip install websocket-client)")
            self.running = False
            return
        except Exception as e:
            self._failures += 1
            delay = self._next_retry_delay()
            # No spamear: aviso en el 1er fallo y luego cada 10; el resto a nivel debug
            level = logging.WARNING if self._failures % 10 == 1 else logging.DEBUG
            log.log(
                level,
                "WebSocket connection error (attempt %d): %s - retrying in %.0fs",
                self._failures, e, delay,
            )
            self._schedule_connect(delay)
            return

        with self._lock:
            if not self.running:  # stop() llegó mientras conectábamos
                _safe_close(ws, "WebSocket")
                return
            self.ws_client = ws
            self._failures = 0
            self.ws_thread = threading.Thread(
                target=self._receive_loop, args=(ws,), daemon=True
            )
            self.ws_thread.start()
        print(f"WebSocket connected to {self.ws_url}")
    
    def _receive_loop(self, ws):
        """Bucle de recepción de mensajes WebSocket."""
        while self.running:
            try:
                message = ws.recv()
            except WebSocketTimeoutException:
                continue  # sin mensajes en este intervalo: no es un fallo
            except Exception as e:
                if self.running:
                    _safe_close(ws, "WebSocket")
                    with self._lock:
                        current = self.ws_client is ws
                        if current:
                            self.ws_client = None
                    if current:  # a stale loop (replaced by a newer connection) must not reconnect
                        log.warning("WebSocket receive error: %s - reconnecting", e)
                        self._failures = 1
                        self._schedule_connect(self._next_retry_delay())
                break

            if not message:
                continue
            try:
                data = json.loads(message)
                if isinstance(data, dict):
                    self._handle_message(data)
                else:
                    log.warning("Ignoring WebSocket message that is not a JSON object")
            except ValueError as e:
                log.warning("Ignoring malformed WebSocket message: %s", e)
            except Exception:
                log.exception("Error handling WebSocket message")
                
    def _handle_message(self, message):
        """Procesa un mensaje recibido del servidor."""
        msg_type = message.get("type", "")
        
        if msg_type == "snapshot":
            # Filtrar por session_code si está configurado
            if self.session_code:
                session_codes = message.get("sessionCodes", [])
                if not isinstance(session_codes, (list, tuple, set)):
                    return
                if self.session_code not in session_codes:
                    return
            
            if self.snapshot_callback:
                self.snapshot_callback(message)
    
    def stop(self):
        """Detiene la conexión WebSocket y cancela reintentos pendientes."""
        with self._lock:
            self.running = False
            if self._retry_timer:
                self._retry_timer.cancel()
                self._retry_timer = None
            ws, self.ws_client = self.ws_client, None
        _safe_close(ws, "WebSocket")
    
    def set_snapshot_callback(self, callback):
        """
        Establece callback para mensajes de snapshot.
        
        Args:
            callback: Función que recibe el diccionario con datos del snapshot
        """
        self.snapshot_callback = callback


# Funciones de compatibilidad con el código anterior

def create_telemetry_client(username, session_code):
    """
    Crea y configura un cliente de telemetría.
    
    Args:
        username: Nombre del usuario
        session_code: Código de sesión
    
    Returns:
        TelemetryClient configurado
    """
    client = TelemetryClient()
    client.connect(username, session_code)
    return client


def send_telemetry_message(data, username, session_code):
    """
    Envía un mensaje de telemetría directamente.
    
    Args:
        data: Diccionario con los datos del mensaje
        username: Nombre del usuario
        session_code: Código de sesión
    """
    client = TelemetryClient()
    client.connect(username, session_code)
    client.send(data)
    client.disconnect()


# Ejemplo de uso
if __name__ == "__main__":
    print("Telemetry Client - Beetlerank Speed Suite v6")
    print(f"Server: {TELEMETRY_HOST}")
    print(f"UDP Port: {TELEMETRY_UDP_PORT}")
    print(f"TCP Port: {TELEMETRY_TCP_PORT}")
    print(f"WebSocket URL: {TELEMETRY_WS_URL}")
    print()
    
    # Ejemplo de uso
    client = TelemetryClient()
    client.connect("TestPlayer", "1234")
    
    # Enviar posición
    client.send_position(x=100, y=50, z=0, speed=25.5, angle=45, map="Rata River", color="#FF5733")
    
    # Enviar start
    client.send_start(lap=1)
    
    # Enviar checkpoint
    client.send_checkpoint(step=5, lap=1, time=45.2)
    
    # Enviar finish
    client.send_finish(lap=1, time=125.5)
    
    # Cuenta regresiva
    for i in ["3", "2", "1"]:
        client.send_countdown(i)
    client.send_countdown("GO")
    
    # Estados
    client.send_ready()
    client.send_surrender()
    
    client.disconnect()
    print("Test completed!")