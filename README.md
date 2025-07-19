# 🏁 Beetlerank Speed Suite v2.06.28

<div align="center">

![Beetlerank Speed Suite](https://user-images.githubusercontent.com/44058571/116699002-597dcc00-a9c5-11eb-8c08-e11e52794992.jpg)

**Professional racing tools for beetle races in Guild Wars 2**

[![Website](https://img.shields.io/badge/Website-beetlerank.com-red?style=for-the-badge)](https://beetlerank.com)
[![Python](https://img.shields.io/badge/Python-3.9+-blue?style=for-the-badge&logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-Open_Source-green?style=for-the-badge)](LICENSE)

</div>

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

## 🗺️ Example maps

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
- **Python 3.9+** - Automatically installed by `install.bat`
- **Windows/Linux/Mac** - Cross-platform support

### First Launch
1. Start Guild Wars 2
2. Run `launch.bat` to open the main launcher  
3. Click "🔧 Check Dependencies" to verify everything is working
4. Launch "🏎️ Speedometer" to start racing
5. Select your map and configure settings

### Multiplayer Racing
1. Open speedometer and select your map/laps
2. Enter the same room code as your friends (e.g., "1111")
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
- **Python**: 3.9 or higher (automatically handled by installer)
- **Memory**: ~100MB RAM usage
- **Storage**: ~200MB for full installation
- **Network**: Optional for multiplayer and rankings

### Dependencies
All automatically installed by `install.bat`:
- Data Processing: `numpy`, `pandas`, `scipy`
- GUI: `tkinter`, `PySide2`, `pyqtgraph` 
- Input: `pynput` for keyboard/mouse handling
- Networking: `websocket-client`, `paho-mqtt`, `requests`
- Game Integration: `mumblelink` API for Guild Wars 2

### File Structure
```
gw2_speedometer/
├── launcher.py              # Main application launcher
├── speedometer.py           # Primary speedometer tool
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

### Getting Help
1. Check the detailed [INSTALL.md](INSTALL.md) guide for comprehensive troubleshooting
2. Use "🔧 Check Dependencies" in the launcher for diagnostic information
3. Visit [beetlerank.com](https://beetlerank.com) for community support
4. Report issues on GitHub with system information and error messages

---

## 📺 Demo Videos

**Racing Gameplay:**
- [Beetle Racing Demo](https://www.youtube.com/watch?v=LxknXO3uT70)
- [Advanced Techniques](https://www.youtube.com/watch?v=_npJtLIhm4U)
- [Spanish Tutorial](https://www.youtube.com/watch?v=_6Pdw_SvgXc)

---

## ⚖️ Legal & Safety

**100% Legal and Safe**
- Uses official Guild Wars 2 MumbleLink API
- No game modifications or addons
- Read-only access to position data
- ArenaNet approved methodology

**Privacy Focused**
- No personal data collection
- Optional online features
- Local data storage by default
- Transparent open-source code

---

## 🤝 Contributing

This is an open-source project welcoming contributions:
- 🐛 **Bug Reports** - Help improve stability
- 🗺️ **Map Creation** - Design new racing tracks  
- 🌍 **Translations** - Localize for your language
- 💻 **Code Contributions** - Enhance features and performance

---

## 🏆 Community & Rankings

Join the racing community at **[beetlerank.com](https://beetlerank.com)**:
- 📊 Global leaderboards and rankings
- 🏁 Tournament announcements  
- 🗺️ Custom map sharing
- 💬 Racing community discussions
- 📈 Personal progress tracking

---

<div align="center">

**Ready to race? Download now and join the Guild Wars 2 beetle racing community!**

[🚀 Download Latest Release](https://github.com/killer415tv/gw2_speedometer/archive/refs/heads/main.zip) | [🌐 Visit Beetlerank.com](https://beetlerank.com) | [📋 Installation Guide](INSTALL.md)

</div>

