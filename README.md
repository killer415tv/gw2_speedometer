# 🏁 Beetlerank Speed Suite v6.0.2

<div align="center">

![Beetlerank Speed Suite](https://user-images.githubusercontent.com/44058571/116699002-597dcc00-a9c5-11eb-8c08-e11e52794992.jpg)

**Professional racing tools for beetle races in Guild Wars 2**

[![Website](https://img.shields.io/badge/Website-beetlerank.com-red?style=for-the-badge)](https://beetlerank.com)
[![Platform](https://img.shields.io/badge/Platform-Windows_10%2F11-blue?style=for-the-badge&logo=windows)](#-quick-start)
[![License](https://img.shields.io/badge/License-Open_Source-green?style=for-the-badge)](LICENSE)
[![Discord](https://img.shields.io/badge/Discord-Join-purple?style=for-the-badge&logo=discord)](https://discord.gg/beetlerank)

</div>

---

## 🚀 Quick Start

**Windows 10 / 11 (64-bit) only.** Linux and macOS are **not supported** (the tools read Guild Wars 2 through the Windows MumbleLink API).
You do **not** need to install Python, use the command line, edit PATH or have administrator rights.

1. **Download** the project: [main.zip](https://github.com/killer415tv/gw2_speedometer/archive/refs/heads/main.zip)
2. **Extract the whole zip** to a folder with a short path, e.g. `C:\GW2Speedometer` (right click → *Extract All*). Do not run it from inside the zip.
3. **Double-click `launch.bat`**.

That's all. The **first time** `launch.bat`:

- downloads `uv` (a small Python manager, ~15 MB) and a private copy of **Python 3.12** (~30 MB);
- creates a virtual environment in the `venv` folder and installs all the libraries (PySide6-Essentials, numpy, pandas, scipy...);
- needs an **internet connection** and downloads roughly **200 MB** (approximate; PySide6-Essentials is the big part), using about **1 GB** of disk. It can take several minutes;
- then starts the launcher.

Everything is stored **inside the project folder** (`tools\` and `venv\`). Nothing is installed system-wide and your own Python (if any) is not touched or used. To uninstall, delete the folder.

Next runs start immediately. Keep the black console window open while you use the program (closing it closes the program).

### Other ways to start

| Command | What it does |
|---------|--------------|
| `launch.bat` | Opens the main launcher (all tools) |
| `launch.bat speedometer` (or `quick_speedometer.bat`) | Opens the speedometer directly |
| `launch.bat qt` (or `quick_qt.bat`) | Opens the speedometer with the **new HUD (experimental)**, see below |
| `launch.bat reinstall` | Rebuilds the environment from scratch (use it if something is broken) |
| `install.bat` | Old name, kept as an alias of `launch.bat` |

### New HUD (experimental) / HUD nuevo (experimental)

An optional, redesigned HUD drawn with Qt on top of the game. The speedometer, the checkpoints, the logs, the uploads and the multiplayer are **exactly the same**: the new HUD only *shows* the values the speedometer already measures. Without the option nothing changes.

**How to start it**

- `quick_qt.bat` or `launch.bat qt`, or
- in the launcher: **Speedometer (new HUD)** (run only one of the two speedometer cards at a time).

**Requirements**

- Guild Wars 2 in **Windowed** or **Windowed Fullscreen** mode (Options → Graphics → Display mode). In exclusive **Fullscreen** Windows does not let other windows draw on top of the game, so the HUD is not visible.
- Windows 10/11 with desktop composition (always on). The PySide6-Essentials library is already installed by `launch.bat`.
- Display scaling (125 %, 150 %…) and several monitors are supported; the HUD uses the primary monitor.

**What it shows**: speed and acceleration, lap time, lap x/y, checkpoint x/y, delta and splits against your best lap of this session (or the time in `<map>_records.csv` for one-lap maps), map name, best time and record. `--` means there is no reference yet. The online ghost keeps running in its own window.

**Keys** (they work while the game has the focus)

| Key | Action |
|-----|--------|
| `Ctrl+Shift+M` | Map selector (type to search, ↑↓ + Enter to choose, Esc to close). The choice goes through the same code as the speedometer's map menus |
| `Ctrl+Shift+O` | Show/hide the optional widgets (splits, next checkpoint, minimap) |

The HUD also adds a tray icon (map selector, optional widgets, close the new HUD).

**Safety net**: the HUD is a separate process and lets mouse clicks pass through to the game. If it is closed or crashes, the speedometer keeps measuring and the classic HUD comes back automatically.

**Advanced options** (from a console in `gw2_speedometer_internal`): `..\venv\Scripts\python.exe speedometer.py --qt-hud --hud-show=splits,nextcp,minimap`. Other options: `--hud-anchor=center`, `--hud-scale=1.2`, `--hud-opacity=0.9`, `--hud-fps=30` (less CPU), `--hud-offline` (map list without internet), `--hud-select-map` (open the selector at start). Setting the environment variable `GW2_QT_HUD=1` is the same as `--qt-hud`.

### Updating

1. Download the new zip and extract it **over** the old folder (or into a new one). Your `logs\` and your settings in `gw2_speedometer_internal\config.txt` are in the folder: back up `config.txt` first if you do not want it overwritten.
2. Run `launch.bat`. If `requirements.txt` changed, the libraries are updated automatically; otherwise it starts directly.

If you use Git instead of the zip: `git pull`, then `launch.bat`.

---

## 🏎️ Features

<img width="949" height="679" alt="image" src="https://github.com/user-attachments/assets/991a615a-15fd-499c-b353-1343c77cef9c" />

### Core Racing Tools
- **📊 Advanced Speedometer** - Real-time speed, acceleration, and angle measurements
- **👻 Ghost Mode** - Race against your best times with online rankings
- **🗺️ Real-time Maps** - Live position tracking with multiplayer support
- **📐 Vector Analysis** - Direction vectors and velocity visualization
- **⏱️ Checkpoint System** - Multi-lap support with automatic logging

### Professional Analysis
- **🎯 3D Visualizer** - Complete 3D representation of your race logs
- **📈 Performance Tracking** - Detailed statistics and improvement tracking
- **🎮 Multiplayer Racing** - Real-time competition with friends
- **🏁 Custom Checkpoints** - Create your own race tracks and jumping puzzles

### Modern Interface
- **🖥️ Unified Launcher** - Manage all applications from one place
- **🌐 Web Integration** - Direct connection to beetlerank.com
- **📱 Responsive Design** - Clean, modern interface with gradient styling
- **🔧 Dependency Manager** - Automatic verification and troubleshooting

---

## 🌐 Multiplayer Communication System

The Speed Suite v6 uses a modern **TCP/UDP/WebSocket** communication architecture to connect players in real-time races. This replaces the legacy MQTT protocol for better performance and reliability.

### Network Architecture

```
┌─────────────────┐      UDP       ┌─────────────────┐     WebSocket      ┌─────────────────┐
│   Speedometer   │ ───────────────│     Server      │ ──────────────────│   Dashboard    │
│ (TCP/UDP Client)│   41234/UDP    │beetlerank.com  │    3002/WSS       │ (Web Browser)  │
└─────────────────┘                └─────────────────┘                   └─────────────────┘
        │                              │                                    │
        │ TCP 41235                    │                                    │
        └──────────────────────────────┴────────────────────────────────────┘
```

### Connection Details

| Protocol | Host | Port | Purpose |
|----------|------|------|---------|
| **UDP** | www.beetlerank.com | 41234 | High-frequency position updates (every 30ms) |
| **TCP** | www.beetlerank.com | 41235 | Critical messages (start, checkpoint, finish, countdown) |
| **WebSocket** | wss://www.beetlerank.com | 3002 | Receiving real-time snapshots of all players |

### Message Types

The system uses JSON messages for all communication. Here are the supported message types:

#### 1. Position Messages (UDP - Port 41234)
```json
{
    "option": "position",
    "x": 26564.776,
    "y": -737.263,
    "z": -324.002,
    "speed": 31.44,
    "angle": 319.34,
    "user": "Player1",
    "sessionCode": 1234,
    "map": "Rata River",
    "color": "#FF5733",
    "lap": 1,
    "step": 0
}
```

#### 2. Start Race Message (TCP - Port 41235)
```json
{
    "option": "s",
    "lap": 1,
    "step": 0,
    "time": 0,
    "user": "Player1",
    "sessionCode": 1234
}
```

#### 3. Checkpoint Message (TCP - Port 41235)
```json
{
    "option": "c",
    "step": 5,
    "lap": 1,
    "time": 45.2,
    "user": "Player1",
    "sessionCode": 1234
}
```

#### 4. Finish Message (TCP - Port 41235)
```json
{
    "option": "f",
    "lap": 1,
    "step": 999,
    "time": 125.5,
    "user": "Player1",
    "sessionCode": 1234
}
```

#### 5. Countdown Messages (TCP - Port 41235)
```json
{"option": "321GO-3", "user": "Player1", "sessionCode": 1234}
{"option": "321GO-2", "user": "Player1", "sessionCode": 1234}
{"option": "321GO-1", "user": "Player1", "sessionCode": 1234}
{"option": "321GO-GO", "user": "Player1", "sessionCode": 1234}
```

### Step Codes

| Step Value | Meaning |
|------------|---------|
| 0 | Race Start / Lap Start |
| 1-998 | Normal Checkpoint |
| 999 | Lap Complete / Finish |
| 998 | Abandon |
| 1000 | Surrender |
| 1001 | Ready |

### Multiplayer Snapshot (WebSocket)

When connected via WebSocket, you receive snapshots containing all active players:

```json
{
    "type": "snapshot",
    "serverTimeMs": 1774365377334,
    "activeCount": 3,
    "totalCount": 5,
    "sessionCodes": [1234, 5678],
    "users": [
        {
            "user": "Player1",
            "sessionCode": 1234,
            "x": 26564.776,
            "y": -737.263,
            "z": -324.002,
            "speed": 31.44,
            "angle": 319.34,
            "option": "position",
            "lap": 1,
            "step": 5,
            "time": 45.2,
            "map": "Rata River",
            "color": "#FF5733",
            "active": true,
            "ageMs": 42.42
        }
    ]
}
```

---

## 🎮 How Multiplayer Racing Works

### Starting a Race

1. **Open Speedometer** - Launch the speedometer from the main launcher
2. **Configure Race** - Select your map, number of laps, and session ID (room code)
3. **Start Multiplayer** - Click the multiplayer button to connect to the server
4. **Wait for Players** - Other players join using the same session ID

### Race Flow

```
[1. JOIN]     All players enter the same session code (e.g., "1234")
     ↓
[2. READY]   Each player clicks "Ready" when prepared
     ↓
[3. COUNTDOWN] Host clicks "Start Race" → 3... 2... 1... GO!
     ↓
[4. RACE]    Automatic timing starts at first checkpoint
     ↓
[5. FINISH]  Times recorded when completing final lap
```

### Real-time Features

- **Live Position Tracking** - See all players on the map in real-time
- **Checkpoint Notifications** - Watch friends hit checkpoints
- **Leaderboard Updates** - Rankings update live during the race
- **Countdown Sync** - Everyone sees the same start countdown

---

## 🗺️ Example Maps

### 🏛️ Guild Halls
- **GWTC** - Guild Wars Tournaments Championship
- **HUR** - Full run and 2-lap variants
- **RACE** - Temple of Speed, Hillclimb, Downhill, Full Mountain
- **SoTD** - Spirits of the Dragon course
- **OLLO** - Speedfall and Drift Heaven
- **UAoT** - United Arts Speedway
- **INDI** - Maguuma Expressway and Shambhala Ascent
- **LRS** - Jokos Descent
- **VAW** - Ratzfatz (multiple paths)
- **BREAK-A-BONE** - Technical challenge course
- **Yuru Camp** - Izu Peninsula Trip and Hot Pot circuit

### 🌍 Tyria Open World
- **Diessa Plateau** - Classic speedway
- **Snowden Drifts** - Winter wonderland racing
- **Gendarran Fields** - Rolling hills circuit  
- **Brisbane Wildlands** - Forest adventure track
- **Grothmar Valley** - Charr territory racing
- **Infinite Leap** - Precision jumping course

### 🏁 DRFT Championship Series
#### Easy Cup (12 tracks)
- Fractal Actual Speedway, Wayfar Out, Summers Sunset
- Mossheart Memory, Roller Coaster Canyon, Centurion Circuit
- Dredgehaunt Cliffs, Icy Rising Ramparts, Toxic Turnpike
- Celedon Circle, Lions Summer Sights, Sandswept Shore Sprint

#### Medium Cup (9 tracks)  
- Estuary of Twilight, Thermo Reactor Escape, Jade Scouting Tour
- Haiju Flying Circus, Skyline Zip Trip, Survival Swamp
- Shae no Moor Lady in White, Inquest Isle Invasion

#### Hard Cup (8 tracks)
- Jormags Jumpscare, Triple Trek series (Amber, Cobalt, Crimson, Medley)
- Seitung Super Tour, Kaineng Zippy Loop, Echovalds Gloomy Roads
- Beachin Crabwalk

### 🦅 Griffon Racing
- **Verdant Brink Hunt** - Canopy navigation challenge
- **Crystal Oasis** - Desert soaring (Expert & Master)
- **Desert Highlands** - Mountain flying (Expert & Master) 
- **Path of Fire Maps** - Complete griffon racing series
- **Flying Circus** - Advanced aerial maneuvers

### 🧗 Jumping Puzzles
- Morgan's Spiral, Spekks Laboratory, Chaos Crystal Cavern
- Khan-Ur's Gauntlet, Asuran Djinn JP, Abaddon's Ascent
- Mad King's Clock Tower, Obsidian Sanctum

### 🎉 Special Events
- **Dragon Bash** - Festival racing circuit
- **Mad King's Raceway** - Halloween special
- **Lunar New Year** - Canthan celebration track

---

## 🎮 Getting Started

### Prerequisites
- **Guild Wars 2** - Game must be running to use the speedometer
- **Windows 10/11 (64-bit)** - Linux/macOS are not supported
- **Internet** - needed for the first run, and for multiplayer and rankings

### First Launch
1. Start Guild Wars 2
2. Double-click `launch.bat` to open the main launcher
3. Click "🔧 Check Dependencies" to verify everything is working
4. Launch "🏎️ Speedometer" to start racing
5. Select your map and configure settings

### Multiplayer Racing
1. Open speedometer and select your map/laps
2. Enter the same room code as your friends (e.g., "1234")
3. Click "Join" to connect to the multiplayer session
4. Hit "Ready" to signal you're prepared to race  
5. One person clicks "Start Race" to begin countdown
6. Racing begins automatically at the first checkpoint

---

## 📱 Application Suite

The launcher provides access to all tools:

| Application | Description | Use Case |
|------------|-------------|-----------|
| 🏎️ **Speedometer** | Main racing HUD with full telemetry | Primary racing tool |
| 👁️ **Checkpoint Viewer** | 3D visualization of race tracks | Course preview and analysis |
| 👻 **Ghost System** | Race against personal bests | Time improvement and competition |
| 📐 **Vector Visualizer** | Real-time movement analysis | Advanced technique study |
| 🏁 **Racing Creator** | Design custom race tracks | Community track creation |
| 🧗 **JP Creator** | Build jumping puzzle checkpoints | Puzzle course design |
| 🗺️ **Real-time Map** | Live position tracking | Navigation and exploration |
| 🌐 **Multiplayer Map** | Multi-player position sharing | Group coordination |

---

## 🔧 Technical Information

### Requirements
- **OS**: Windows 10/11, 64-bit
- **Python**: nothing to install - `launch.bat` provides a private Python 3.12 (managed by [uv](https://github.com/astral-sh/uv)). The libraries in `requirements.txt` need Python 3.12 (`numpy<2`)
- **Memory**: ~100MB RAM usage
- **Storage**: ~1GB for the full installation (mostly PySide6-Essentials)
- **Network**: Required for the first installation, multiplayer and rankings

### Dependencies
Installed automatically by `launch.bat` from `gw2_speedometer_internal/requirements.txt`:
- Data Processing: `numpy`, `pandas`, `scipy`
- GUI: `tkinter` (bundled with Python), `PySide6` (PySide6-Essentials package), `pyqtgraph`
- Input: `pynput` for keyboard/mouse handling
- Networking: `websocket-client`, `requests`
- Game Integration: `mumblelink` API for Guild Wars 2
- Optional (not installed by default): `plotly` for `web3DPlotter.py`, see `gw2_speedometer_internal/requirements-optional.txt`
- Development only: `requirements-dev.txt` (pytest, ruff); run the tests with `python -m pytest`

### File Structure
```
gw2_speedometer/
├── launch.bat                       # Installer + launcher (double-click this)
├── install.bat                      # Alias of launch.bat (old name)
├── quick_speedometer.bat            # Alias: launch.bat speedometer
├── gw2_speedometer_internal/
│   ├── launcher.py                  # Main application launcher
│   ├── speedometer.py               # Primary speedometer tool
│   ├── telemetry_client.py          # TCP/UDP/WebSocket communication module
│   ├── requirements.txt             # Python dependencies
│   ├── requirements-optional.txt    # Optional (plotly for web3DPlotter.py)
│   ├── logs/                        # Race data and telemetry
│   └── maps/                        # Custom track definitions
├── tools/                           # Created on first run: uv, Python 3.12, download cache
└── venv/                            # Created on first run: virtual environment
```

---

## 🌟 Advanced Features

### Data Analysis
- **CSV Export** - Full telemetry data for external analysis
- **3D Plotting** - Visualize racing lines and optimal paths
- **Performance Metrics** - Speed, acceleration, angle analysis
- **Comparison Tools** - Compare runs against personal bests

### Customization
- **Custom Maps** - Import community-created tracks
- **Personalized HUD** - Configure display elements
- **Color Themes** - Match your personal style
- **Keybind Settings** - Customize controls

### Integration
- **Beetlerank.com** - Automatic time uploads and global rankings
- **LiveSplit** - Integration with speedrunning timer
- **OBS Support** - Racing overlay for streaming
- **API Access** - Developer tools for advanced users

---

## 🆘 Troubleshooting

### Installation problems
- **"program files not found"**: you ran `launch.bat` from inside the zip. Extract the whole zip first.
- **Download fails / no internet / proxy**: the first run needs access to `github.com` (uv and Python are downloaded from there) and to `pypi.org`/`files.pythonhosted.org` (libraries). Check your connection and run `launch.bat` again; finished downloads are cached in `tools\uv-cache`.
- **Antivirus or Windows SmartScreen blocks something**: `launch.bat` downloads `uv.exe` and Python into `tools\`, and some security software flags unsigned downloaded programs. If Windows shows *"Windows protected your PC"* for `launch.bat`, click *More info → Run anyway* (the script is plain text: you can open it with Notepad and read it). Add the project folder as an exclusion in your antivirus if it quarantines files, then run `launch.bat reinstall`.
- **Strange characters or a very long path**: move the folder to a short plain path such as `C:\GW2Speedometer`. Network paths (`\\server\share`) are not supported.
- **Something is broken after an update or a moved folder**: run `launch.bat reinstall`. If it still fails, delete the `venv` and `tools` folders and run `launch.bat` again.
- **Offline PC**: download `uv-x86_64-pc-windows-msvc.zip` from the [uv releases](https://github.com/astral-sh/uv/releases) on another computer and put `uv.exe` into `tools\uv\`. Python and the libraries still need internet.

### Using the program
- **Game Not Detected**: Ensure Guild Wars 2 is running before launching
- **Performance Issues**: Close unnecessary applications while racing
- **Multiplayer Connection Failed**: Check your internet connection and firewall settings (see below)

### Network Troubleshooting
The speedometer uses specific ports for multiplayer (outbound connections to `www.beetlerank.com`):
- **UDP 41234** - Position updates (can be blocked by firewalls)
- **TCP 41235** - Critical messages
- **WSS 3002** - Player snapshots (WebSocket over TLS)

If you have connection issues, ensure these ports are not blocked.

### Getting Help
1. Use "🔧 Check Dependencies" in the launcher for diagnostic information
2. Visit [beetlerank.com](https://beetlerank.com) for community support
3. Report issues on GitHub with your Windows version and the error messages shown in the console window

---

## 🇪🇸 Resumen en español

**Solo Windows 10/11 de 64 bits.** Linux y macOS no están soportados.

1. Descarga el [zip](https://github.com/killer415tv/gw2_speedometer/archive/refs/heads/main.zip) y **descomprímelo entero** en una carpeta con ruta corta (por ejemplo `C:\GW2Speedometer`).
2. Haz **doble clic en `launch.bat`**. No hace falta instalar Python, ni permisos de administrador, ni tocar el PATH.
3. La **primera vez** descarga uv, un Python 3.12 privado y las librerías (unos **200 MB**, ~1 GB en disco, necesita **internet** y puede tardar varios minutos). Todo queda **dentro de la carpeta** (`tools\` y `venv\`); para desinstalar, borra la carpeta. Las siguientes veces arranca directamente.
4. **Actualizar**: descarga el zip nuevo y descomprímelo sobre la carpeta (haz copia de `gw2_speedometer_internal\config.txt` si no quieres perder tu configuración), y ejecuta `launch.bat`; si cambian los requisitos se actualizan solos.
5. **Problemas**: `launch.bat reinstall` reconstruye el entorno. Si el antivirus o SmartScreen bloquea algo, permite la carpeta del proyecto ("Más información → Ejecutar de todas formas"). Si falla la descarga, revisa internet/proxy. Evita rutas largas o con caracteres raros.
6. **Puertos del multijugador** (conexiones salientes a `www.beetlerank.com`): 41234/UDP, 41235/TCP y 3002/WSS.

### HUD nuevo (experimental)

HUD rediseñado y opcional, dibujado con Qt encima del juego. La medición, los checkpoints, los logs, las subidas y el multijugador son **exactamente los mismos**: el HUD nuevo solo *muestra* lo que ya mide el speedometer. Sin la opción no cambia nada.

- **Arrancar**: `quick_qt.bat` o `launch.bat qt`, o en el launcher **Speedometer (new HUD)** (no abras las dos tarjetas de speedometer a la vez).
- **Requisitos**: GW2 en modo **Ventana** o **Ventana a pantalla completa** (Opciones → Gráficos → Modo de pantalla). En **Pantalla completa** exclusiva Windows no deja dibujar encima del juego y el HUD no se ve. Windows 10/11; PySide6-Essentials ya lo instala `launch.bat`. Soporta escalado de pantalla (125 %, 150 %…); usa el monitor principal.
- **Muestra**: velocidad, aceleración, tiempo de vuelta, vuelta x/y, checkpoint x/y, delta y parciales contra tu mejor vuelta de la sesión (o el tiempo de `<mapa>_records.csv` en mapas de una vuelta), nombre del mapa, mejor tiempo y récord. `--` = todavía no hay referencia. El ghost online sigue en su propia ventana.
- **Teclas** (funcionan con el juego en primer plano): `Ctrl+Shift+M` abre el selector de mapas (escribe para buscar, ↑↓ + Enter para elegir, Esc para cerrar; usa el mismo código que los menús del speedometer). `Ctrl+Shift+O` muestra/oculta los widgets opcionales (parciales, siguiente checkpoint, minimapa). También hay un icono en la bandeja del sistema.
- **Red de seguridad**: el HUD es un proceso aparte y deja pasar los clics al juego. Si se cierra o falla, el speedometer sigue midiendo y vuelve el HUD clásico.
- **Opciones avanzadas** (consola en `gw2_speedometer_internal`): `..\venv\Scripts\python.exe speedometer.py --qt-hud --hud-show=splits,nextcp,minimap`; también `--hud-anchor=center`, `--hud-scale=1.2`, `--hud-opacity=0.9`, `--hud-fps=30` (menos CPU), `--hud-offline`, `--hud-select-map`. La variable de entorno `GW2_QT_HUD=1` equivale a `--qt-hud`.

---

## 📺 Demo Videos

**Racing Gameplay:**
- [Beetle Racing Demo](https://www.youtube.com/watch?v=LxknXO3uT70)
- [Advanced Techniques](https://www.youtube.com/watch?v=_npJtLIhm4U)

---

## 📄 License

This project is open source. See LICENSE file for details.

---

## 🙏 Acknowledgments

- Guild Wars 2 community for track designs
- Beetlerank.com for server infrastructure
- All contributors and beta testers
