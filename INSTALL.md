# 🚀 Guía de Instalación - GW2 Speedometer Suite

## 📋 Instalación Automática (Recomendada)

### Windows
1. **Descarga el proyecto** desde GitHub como ZIP y descomprímelo
2. **Ejecuta** `install.bat` como administrador
3. **Sigue las instrucciones** en pantalla
4. **Lanza el programa** con `launch.bat`

### Linux/Mac
1. **Descarga el proyecto** desde GitHub como ZIP y descomprímelo
2. **Abre terminal** en la carpeta del proyecto
3. **Ejecuta**: `chmod +x install.sh && ./install.sh`
4. **Lanza el programa** con `./launch.sh`

---

## 🔧 Instalación Manual

### Requisitos Previos
- **Python 3.9 o superior** ([Descargar aquí](https://www.python.org/downloads/))
- **Git** (opcional)

### Pasos Detallados

#### 1. Obtener el Código
```bash
# Opción A: Con Git
git clone https://github.com/tu-usuario/gw2_speedometer.git
cd gw2_speedometer

# Opción B: Descarga directa
# Descarga el ZIP desde GitHub y descomprime
```

#### 2. Crear Entorno Virtual
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

#### 3. Instalar Dependencias
```bash
# Instalación completa (recomendada)
pip install -r requirements.txt

# Instalación mínima (solo speedometer básico)
pip install numpy pandas scipy pynput requests paho-mqtt websocket-client
```

#### 4. Ejecutar
```bash
# Launcher completo
python launcher.py

# Solo speedometer
python speedometer.py
```

---

## 🚨 Solución de Problemas

### Error: "Python no encontrado"
**Windows:**
- Reinstala Python desde [python.org](https://python.org)
- ✅ **MARCA** "Add Python to PATH" durante la instalación

**Linux:**
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install python3 python3-pip python3-venv

# CentOS/RHEL
sudo yum install python3 python3-pip
```

**macOS:**
```bash
# Con Homebrew
brew install python3

# O descarga desde python.org
```

### Error: "No module named XXX"
```bash
# Activa el entorno virtual y reinstala
# Windows
venv\Scripts\activate
pip install -r requirements.txt

# Linux/Mac
source venv/bin/activate
pip install -r requirements.txt
```

### Problemas con PySide2/PyQt
```bash
# Intenta alternativas
pip uninstall PySide2
pip install PyQt5

# O usa sin GUI 3D
pip install --no-deps pyqtgraph
```

### Error de Permisos (Linux/Mac)
```bash
# Dar permisos a los scripts
chmod +x *.sh
chmod +x install.sh
```

---

## 📱 Diferentes Formas de Ejecutar

### 1. Launcher Completo (Recomendado)
```bash
# Windows
launch.bat

# Linux/Mac
./launch.sh
```
- ✅ Interfaz gráfica con todas las aplicaciones
- ✅ Gestión automática de procesos
- ✅ Verificación de dependencias

### 2. Speedometer Directo
```bash
# Windows
quick_speedometer.bat

# Linux/Mac
./quick_speedometer.sh
```
- ✅ Inicio más rápido
- ✅ Solo la aplicación principal

### 3. Aplicaciones Individuales
```bash
# Activar entorno virtual primero
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate

python speedometer.py          # Speedometer principal
python checkpoints.py          # Visor de checkpoints 3D
python ghost_online.py         # Sistema de ghost
python vectors.py              # Visualizador de vectores
python RACINGcheckpointcreator.py  # Creador de checkpoints (carreras)
python JPcheckpointcreator.py  # Creador de checkpoints (jumping puzzles)
```

---

## 🔄 Actualización

### Actualizar Dependencias
```bash
# Windows
update.bat

# Linux/Mac
./update.sh

# Manual
pip install -r requirements.txt --upgrade
```

### Actualizar Código
```bash
# Con Git
git pull origin main

# Manual
# Descarga la nueva versión y reemplaza archivos
```

---

## 🎮 Configuración Post-Instalación

### 1. Configurar Guild Wars 2
- ✅ Inicia Guild Wars 2
- ✅ El juego debe estar **ejecutándose** para usar el speedometer

### 2. Primera Ejecución
1. Ejecuta `launch.bat` (Windows) o `./launch.sh` (Linux/Mac)
2. Haz clic en "🔧 Verificar Dependencias" 
3. Si todo está verde ✅, ¡estás listo!

### 3. Configurar Speedometer
1. Lanza "🏎️ Speedometer" desde el launcher
2. Configura tus preferencias en el menú
3. Selecciona tu mapa en el sistema de checkpoints

---

## 📦 Estructura del Proyecto
```
gw2_speedometer/
├── launcher.py              # 🚀 Launcher principal
├── speedometer.py           # 🏎️ Speedometer principal
├── install.bat/.sh          # 🔧 Instaladores automáticos
├── launch.bat/.sh           # ▶️ Scripts de ejecución
├── requirements.txt         # 📋 Dependencias
├── venv/                    # 🐍 Entorno virtual (se crea automáticamente)
├── logs/                    # 📊 Logs de carreras
├── maps/                    # 🗺️ Mapas personalizados
└── installer/               # 🛠️ Herramientas de instalación legacy
```

---

## 🆘 Soporte

### ¿Necesitas Ayuda?
1. **Revisa** esta guía completa
2. **Ejecuta** el verificador de dependencias en el launcher
3. **Consulta** los logs de error en la consola
4. **Busca** tu error en la sección de problemas comunes

### Información del Sistema
Para reportar problemas, incluye:
- 🖥️ Sistema operativo y versión
- 🐍 Versión de Python (`python --version`)
- 📋 Mensaje de error completo
- 🎮 Versión de Guild Wars 2

---

## ✅ Verificación de Instalación Exitosa

Si la instalación fue correcta, deberías poder:
- ✅ Ejecutar `launch.bat` sin errores
- ✅ Ver el launcher con todas las aplicaciones listadas
- ✅ Verificar dependencias muestra todo en verde
- ✅ Lanzar el speedometer y ver la interfaz
- ✅ El speedometer muestra datos cuando GW2 está ejecutándose

¡Disfruta de tus carreras de escarabajos! 🏁 