# 🏁 Beetlerank Speed Suite v6.00.00

<div align="center">

![Beetlerank Speed Suite](https://user-images.githubusercontent.com/44058571/116699002-597dcc00-a9c5-11eb-8c08-e11e52794992.jpg)

**Professional racing tools for beetle races in Guild Wars 2**

[![Website](https://img.shields.io/badge/Website-beetlerank.com-red?style=for-the-badge)](https://beetlerank.com)
[![Python](https://img.shields.io/badge/Python-3.12+-blue?style=for-the-badge&logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-Open_Source-green?style=for-the-badge)](LICENSE)
[![Discord](https://img.shields.io/badge/Discord-Join-purple?style=for-the-badge&logo=discord)](https://discord.gg/beetlerank)

</div>

---

## 🚀 Quick Start

### Automatic Installation (Recommended)

1. **Download** the project from [GitHub releases](https://github.com/killer415tv/gw2_speedometer/archive/refs/heads/main.zip)
2. **Extract** the ZIP file to your desired location
3. **Run** `install.bat` (Windows) or `install.sh` (Linux/Mac)
4. **Launch** with `launch.bat` or `./launch.sh`

That's it! The installer will:
- ✅ Check Python installation
- ✅ Create virtual environment
- ✅ Install all dependencies
- ✅ Create launch scripts

### Launch Applications

After installation, you have multiple options:

- **🖥️ Main Launcher**: Run `launch.bat` for a complete GUI with all applications
- **⚡ Quick Speedometer**: Run `quick_speedometer.bat` for direct speedometer access
- **🔄 Update Dependencies**: Run `update.bat` to update all packages

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
- **Guild Wars 2** - Game must be running to use speedometer
- **Python 3.12.1** - Automatically installed by `install.bat`
- **Windows/Linux/Mac** - Cross-platform support

### First Launch
1. Start Guild Wars 2
2. Run `launch.bat` to open the main launcher  
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
- **Python**: 3.12 or higher (automatically handled by installer)
- **Memory**: ~100MB RAM usage
- **Storage**: ~200MB for full installation
- **Network**: Required for multiplayer and rankings

### Dependencies
All automatically installed by `install.bat`:
- Data Processing: `numpy`, `pandas`, `scipy`
- GUI: `tkinter`, `PySide6`, `pyqtgraph` 
- Input: `pynput` for keyboard/mouse handling
- Networking: `websocket-client`, `requests`
- Game Integration: `mumblelink` API for Guild Wars 2

### File Structure
```
gw2_speedometer/
├── launcher.py              # Main application launcher
├── speedometer.py           # Primary speedometer tool
├── telemetry_client.py     # TCP/UDP/WebSocket communication module
├── install.bat             # Windows installer
├── launch.bat              # Windows launcher  
├── quick_speedometer.bat   # Direct speedometer access
├── update.bat              # Dependency updater
├── logs/                   # Race data and telemetry
├── maps/                   # Custom track definitions
└── venv/                   # Python virtual environment
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

### Common Issues
- **Python Not Found**: Run installer as administrator
- **Dependencies Missing**: Execute `update.bat` to reinstall packages
- **Game Not Detected**: Ensure Guild Wars 2 is running before launching
- **Performance Issues**: Close unnecessary applications while racing
- **Multiplayer Connection Failed**: Check your internet connection and firewall settings

### Network Troubleshooting
The speedometer uses specific ports for multiplayer:
- **UDP 41234** - Position updates (can be blocked by firewalls)
- **TCP 41235** - Critical messages
- **WebSocket 3002** - Player snapshots

If you have connection issues, ensure these ports are not blocked.

### Getting Help
1. Check the detailed [INSTALL.md](gw2_speedometer_internal/INSTALL.md) guide for comprehensive troubleshooting
2. Use "🔧 Check Dependencies" in the launcher for diagnostic information
3. Visit [beetlerank.com](https://beetlerank.com) for community support
4. Report issues on GitHub with system information and error messages

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
