# 🚀 Installation Guide - Beetlerank Speed Suite

## 📋 Automatic Installation (Recommended)

### Windows
1. **Download the project** from GitHub as ZIP and extract it
2. **Run** `install.bat` as administrator
3. **Follow the instructions** on screen
4. **Launch the program** with `launch.bat`

### Linux/Mac
1. **Download the project** from GitHub as ZIP and extract it
2. **Open terminal** in the project folder
3. **Execute**: `chmod +x install.sh && ./install.sh`
4. **Launch the program** with `./launch.sh`

---

## 🔧 Manual Installation

### Prerequisites
- **Python 3.12 or higher** ([Download here](https://www.python.org/downloads/))
- **Git** (optional)

### Detailed Steps

#### 1. Get the Code
```bash
# Option A: With Git
git clone https://github.com/killer415tv/gw2_speedometer.git
cd gw2_speedometer

# Option B: Direct download
# Download the ZIP from GitHub and extract
```

#### 2. Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

#### 3. Install Dependencies
```bash
# Complete installation (recommended)
pip install -r requirements.txt

# Minimal installation (basic speedometer only)
pip install numpy pandas scipy pynput requests paho-mqtt websocket-client
```

#### 4. Run Applications
```bash
# Complete launcher
python launcher.py

# Direct speedometer
python speedometer.py
```

---

## 🚨 Troubleshooting

### Error: "Python not found"
**Windows:**
- Reinstall Python from [python.org](https://python.org)
- ✅ **CHECK** "Add Python to PATH" during installation

**Linux:**
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install python3 python3-pip python3-venv

# CentOS/RHEL
sudo yum install python3 python3-pip
```

**macOS:**
```bash
# With Homebrew
brew install python3

# Or download from python.org
```

### Error: "No module named XXX"
```bash
# Activate virtual environment and reinstall
# Windows
venv\Scripts\activate
pip install -r requirements.txt

# Linux/Mac
source venv/bin/activate
pip install -r requirements.txt
```

### Issues with PySide2/PyQt
```bash
# Try alternatives
pip uninstall PySide2
pip install PyQt5

# Or use without 3D GUI
pip install --no-deps pyqtgraph
```

### Permission Errors (Linux/Mac)
```bash
# Give permissions to scripts
chmod +x *.sh
chmod +x install.sh
```

### WebSocket Connection Issues
```bash
# Ensure correct websocket package
pip uninstall websocket websocket-client
pip install websocket-client

# Test the import
python -c "from websocket import WebSocketApp; print('Success')"
```

---

## 📱 Different Ways to Run

### 1. Complete Launcher (Recommended)
```bash
# Windows
launch.bat

# Linux/Mac
./launch.sh
```
- ✅ Graphical interface with all applications
- ✅ Automatic process management
- ✅ Dependency verification

### 2. Direct Speedometer
```bash
# Windows
quick_speedometer.bat

# Linux/Mac
./quick_speedometer.sh
```
- ✅ Faster startup
- ✅ Main application only

### 3. Individual Applications
```bash
# Activate virtual environment first
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate

python speedometer.py                    # Main speedometer
python checkpoints.py                    # 3D checkpoint viewer
python ghost_online.py                   # Ghost system
python ghost_online_relative_to_user.py  # Relative ghost system
python vectors.py                        # Vector visualizer
python RACINGcheckpointcreator.py        # Racing checkpoint creator
python JPcheckpointcreator.py            # Jumping puzzle creator
python map_realtime.py                   # Real-time map
python map_realtime_multiplayer.py       # Multiplayer map
python forzaHorizon.py                   # Forza Horizon style display
python web3DPlotter.py                   # 3D web plotter
```

---

## 🔄 Updates

### Update Dependencies
```bash
# Windows
update.bat

# Linux/Mac
./update.sh

# Manual
pip install -r requirements.txt --upgrade
```

### Update Code
```bash
# With Git
git pull origin main

# Manual
# Download new version and replace files
```

---

## 🎮 Post-Installation Setup

### 1. Configure Guild Wars 2
- ✅ Start Guild Wars 2
- ✅ Game must be **running** to use the speedometer

### 2. First Execution
1. Execute `launch.bat` (Windows) or `./launch.sh` (Linux/Mac)
2. Click on "🔧 Check Dependencies" 
3. If everything is green ✅, you're ready!

### 3. Configure Speedometer
1. Launch "🏎️ Speedometer" from the launcher
2. Configure your preferences in the menu
3. Select your map in the checkpoint system

---

## 🎯 Application Details

### Main Applications

#### 🏎️ Speedometer
**Primary racing tool with complete HUD**
- Real-time speed, acceleration, angle measurements
- Multi-lap support with automatic checkpoints
- Configurable display elements
- Integration with beetlerank.com rankings

**Launch**: Click "Speedometer" in launcher or run `speedometer.py`

#### 👻 Ghost System
**Race against your best times**
- Load previous race logs as ghost opponents
- Online ghost sharing and competitions
- Personal best tracking
- Visual representation of optimal racing lines

**Launch**: 
- `ghost_online.py` - Standard ghost mode
- `ghost_online_relative_to_user.py` - Relative positioning ghost

#### 👁️ Checkpoint Viewer  
**3D visualization of race tracks**
- Preview course layout before racing
- Understand optimal racing lines
- Checkpoint placement analysis
- Interactive 3D navigation

**Launch**: Click "Checkpoint Viewer" or run `checkpoints.py`

#### 📐 Vector Visualizer
**Advanced movement analysis**
- Real-time velocity vectors
- Direction and angle measurements  
- Performance optimization tools
- Technical racing analysis

**Launch**: Click "Vector Visualizer" or run `vectors.py`

### Creation Tools

#### 🏁 Racing Checkpoint Creator
**Design custom race tracks**
- Place checkpoints for racing circuits
- Define start/finish lines
- Export tracks for community sharing
- Test track layouts

**Launch**: Click "Checkpoint Creator (Racing)" or run `RACINGcheckpointcreator.py`

#### 🧗 Jumping Puzzle Creator  
**Build jumping puzzle checkpoints**
- Create checkpoint sequences for puzzles
- Define progression paths
- Export puzzle definitions
- Community puzzle sharing

**Launch**: Click "Checkpoint Creator (Jumping Puzzles)" or run `JPcheckpointcreator.py`

### Visualization Tools

#### 🗺️ Real-time Map
**Live position tracking**
- See your current position on map
- Navigation assistance
- Exploration tracking
- Route planning

**Launch**: Click "Real-time Map" or run `map_realtime.py`

#### 🌐 Multiplayer Map
**Multi-player position sharing**
- See friends' positions in real-time
- Group coordination for events
- Multiplayer race tracking
- Social exploration

**Launch**: Click "Multiplayer Map" or run `map_realtime_multiplayer.py`

---

## 📦 Project Structure
```
gw2_speedometer/
├── launcher.py                        # 🚀 Main launcher
├── speedometer.py                     # 🏎️ Primary speedometer
├── install.bat/.sh                    # 🔧 Automatic installers
├── launch.bat/.sh                     # ▶️ Launch scripts
├── quick_speedometer.bat/.sh          # ⚡ Direct speedometer
├── update.bat/.sh                     # 🔄 Dependency updaters
├── requirements.txt                   # 📋 Dependencies
├── venv/                              # 🐍 Virtual environment (auto-created)
├── logs/                              # 📊 Race logs and telemetry
├── maps/                              # 🗺️ Custom maps and tracks
├── maps_old_folder/                   # 📁 Legacy map collection
├── fonts/                             # 🔤 Custom fonts for display
├── oldversions/                       # 📜 Legacy application versions
├── apps/                              # 📱 Additional applications
└── installer/                         # 🛠️ Legacy installation tools
```

---

## ⚙️ Advanced Configuration

### Environment Variables
```bash
# Optional performance tweaks
export PYTHONPATH="${PYTHONPATH}:/path/to/gw2_speedometer"
export GW2_SPEEDOMETER_CONFIG="/path/to/custom/config"
```

### Custom Maps
1. Place `.csv` map files in the `maps/` folder
2. Follow the naming convention: `MAPNAME.csv`
3. Use the checkpoint creators to generate proper format
4. Maps automatically appear in the speedometer selection

### Network Configuration
- **Default WebSocket**: `beetlerank.com:1234`
- **MQTT Broker**: Configurable in speedometer settings
- **HTTP API**: Uses standard HTTPS for rankings upload

---

## 🆘 Support & Diagnostics

### Diagnostic Tools
The launcher includes built-in diagnostic tools:

1. **Dependency Checker** - Verifies all packages are installed
2. **Connection Tester** - Tests network connectivity to services  
3. **Guild Wars 2 Detector** - Confirms game integration is working
4. **Performance Monitor** - Shows system resource usage

### Log Files
Check these locations for troubleshooting:
- **Race Logs**: `logs/` folder
- **Error Logs**: Console output when running from terminal
- **Config Files**: `config.txt`, `cup.txt`

### Getting Help
1. **Check Dependencies**: Use the launcher's built-in checker
2. **Review Logs**: Look for error messages in console output  
3. **Community Support**: Visit [beetlerank.com](https://beetlerank.com)
4. **GitHub Issues**: Report bugs with system information

### System Information for Bug Reports
When reporting issues, include:
- 🖥️ Operating system and version
- 🐍 Python version (`python --version`)  
- 📋 Complete error message
- 🎮 Guild Wars 2 version and region
- 🌐 Network configuration (if relevant)

---

## ✅ Installation Verification

### Quick Test
After installation, verify everything works:
1. ✅ `launch.bat` runs without errors
2. ✅ Launcher GUI appears with all applications listed
3. ✅ "Check Dependencies" shows all green checkmarks  
4. ✅ Speedometer launches and shows interface
5. ✅ With GW2 running, speedometer displays live data

### Performance Check
- Memory usage should be ~100MB total
- CPU usage should be minimal (<5%) when idle
- Network usage only when uploading times or multiplayer

---

## 🏁 Ready to Race!

Once installation is complete:
1. **Start Guild Wars 2**
2. **Run the launcher** (`launch.bat` or `./launch.sh`)
3. **Launch Speedometer** from the GUI
4. **Select your track** and start racing!
5. **Join the community** at [beetlerank.com](https://beetlerank.com)

---

<div align="center">

**Happy Racing! 🏆**

For more information visit [beetlerank.com](https://beetlerank.com)

</div> 