"""
Módulo de Telemetría UDP/TCP para Beetlerank Speed Suite v6

Este módulo reemplaza las comunicaciones MQTT por UDP/TCP:
- UDP (puerto 41234): Para mensajes de posición frecuentes
- TCP (puerto 41235): Para mensajes críticos (start, checkpoint, finish, countdown)
- WebSocket (wss://www.beetlerank.com:3002): Para recibir snapshots de multijugador
"""

import socket
import json
import threading
import time


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
        try:
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.settimeout(5.0)
            self.tcp_socket.connect((self.host, self.tcp_port))
            self.tcp_connected = True
            print(f"TCP connected to {self.host}:{self.tcp_port}")
        except Exception as e:
            print(f"TCP connection failed: {e}")
            self.tcp_connected = False
    
    def _receive_tcp_loop(self):
        """Hilo para recibir mensajes del servidor por TCP."""
        buffer = b""
        
        while self.running:
            try:
                if self.tcp_socket and self.tcp_connected:
                    # Usar select para timeout
                    self.tcp_socket.setblocking(False)
                    try:
                        data = self.tcp_socket.recv(4096)
                        if data:
                            buffer += data
                            
                            # Procesar mensajes completos (separados por newline)
                            while b"\n" in buffer:
                                line, buffer = buffer.split(b"\n", 1)
                                try:
                                    message = json.loads(line.decode("utf-8"))
                                    if self.on_message_callback:
                                        self.on_message_callback(message)
                                except json.JSONDecodeError:
                                    pass
                    except BlockingIOError:
                        pass
                time.sleep(0.1)
            except Exception as e:
                if self.running:
                    print(f"TCP receive error: {e}")
                    time.sleep(1)
                    # Reintentar conexión
                    self._connect_tcp()
    
    def disconnect(self):
        """Cierra las conexiones y detiene los hilos."""
        self.running = False
        
        if self.tcp_socket:
            try:
                self.tcp_socket.close()
            except:
                pass
        
        if self.udp_socket:
            try:
                self.udp_socket.close()
            except:
                pass
    
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
        if not self.tcp_connected:
            self._connect_tcp()
        
        if self.tcp_socket and self.tcp_connected:
            try:
                # Enviar datos con newline como delimitador
                self.tcp_socket.sendall(data + b"\n")
            except Exception as e:
                print(f"TCP send error: {e}")
                self.tcp_connected = False
    
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
        
        if self.udp_socket:
            try:
                self.udp_socket.close()
            except:
                pass
        
        if self.tcp_server:
            try:
                self.tcp_server.close()
            except:
                pass
    
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
                        except json.JSONDecodeError:
                            pass
                except socket.timeout:
                    break
        except Exception as e:
            print(f"TCP client error: {e}")
        finally:
            client_socket.close()
    
    def _handle_message(self, message):
        """Procesa un mensaje recibido."""
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
    
    def start(self):
        """Inicia la conexión WebSocket."""
        if self.running:
            return
            
        self.running = True
        
        # Importar aquí para evitar problemas si no está instalado
        try:
            from websocket import create_connection, WebSocketException
            self._connect()
        except ImportError:
            print("ERROR: websocket-client not installed")
            print("Please run: pip install websocket-client")
            self.running = False
    
    def _connect(self):
        """Conecta al servidor WebSocket."""
        try:
            from websocket import create_connection, WebSocketException
            self.ws_client = create_connection(self.ws_url, timeout=5)
            print(f"WebSocket connected to {self.ws_url}")
            
            # Iniciar hilo de recepción
            self.ws_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.ws_thread.start()
            
        except Exception as e:
            print(f"WebSocket connection error: {e}")
            self.running = False
            # Reintentar en 5 segundos
            threading.Timer(5, self._retry_connection).start()
    
    def _retry_connection(self):
        """Reintenta la conexión WebSocket."""
        if self.running:
            self._connect()
    
    def _receive_loop(self):
        """Bucle de recepción de mensajes WebSocket."""
        while self.running and self.ws_client:
            try:
                message = self.ws_client.recv()
                if message:
                    data = json.loads(message)
                    self._handle_message(data)
            except Exception as e:
                if self.running:
                    print(f"WebSocket receive error: {e}")
                    # Reintentar conexión
                    self.ws_client = None
                    threading.Timer(5, self._retry_connection).start()
                    break
                
    def _handle_message(self, message):
        """Procesa un mensaje recibido del servidor."""
        msg_type = message.get("type", "")
        
        if msg_type == "snapshot":
            # Filtrar por session_code si está configurado
            if self.session_code:
                session_codes = message.get("sessionCodes", [])
                if self.session_code not in session_codes:
                    return
            
            if self.snapshot_callback:
                self.snapshot_callback(message)
    
    def stop(self):
        """Detiene la conexión WebSocket."""
        self.running = False
        
        if self.ws_client:
            try:
                self.ws_client.close()
            except:
                pass
            self.ws_client = None
    
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