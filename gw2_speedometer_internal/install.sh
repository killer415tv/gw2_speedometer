#!/bin/bash

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Variables
VENV_DIR="venv"
PYTHON_MIN_VERSION="3.9"
PROJECT_NAME="GW2 Speedometer Suite"

echo -e "${BLUE}===============================================${NC}"
echo -e "${BLUE}    GW2 Speedometer Suite - Instalación${NC}"
echo -e "${BLUE}===============================================${NC}"
echo

# Función para verificar si un comando existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Función para comparar versiones
version_ge() {
    [ "$(printf '%s\n' "$2" "$1" | sort -V | head -n1)" = "$2" ]
}

# [1/6] Verificar Python
echo -e "${BLUE}[1/6] Verificando Python...${NC}"

# Buscar Python (python3, python, python3.9, etc.)
PYTHON_CMD=""
for cmd in python3 python python3.9 python3.10 python3.11; do
    if command_exists "$cmd"; then
        PYTHON_VERSION=$($cmd --version 2>&1 | cut -d' ' -f2)
        if version_ge "$PYTHON_VERSION" "$PYTHON_MIN_VERSION"; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}❌ ERROR: Python 3.9+ no encontrado${NC}"
    echo
    echo "Por favor instala Python 3.9 o superior:"
    echo "  Ubuntu/Debian: sudo apt update && sudo apt install python3 python3-pip python3-venv"
    echo "  CentOS/RHEL:   sudo yum install python3 python3-pip"
    echo "  macOS:         brew install python3"
    echo "  O descarga desde: https://www.python.org/downloads/"
    echo
    exit 1
fi

echo -e "${GREEN}✅ Python $PYTHON_VERSION encontrado (usando $PYTHON_CMD)${NC}"

# [2/6] Verificar pip
echo
echo -e "${BLUE}[2/6] Verificando pip...${NC}"
if ! $PYTHON_CMD -m pip --version >/dev/null 2>&1; then
    echo -e "${RED}❌ ERROR: pip no está disponible${NC}"
    echo "Instalando pip..."
    $PYTHON_CMD -m ensurepip --upgrade
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ ERROR: No se pudo instalar pip${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}✅ pip disponible${NC}"

# [3/6] Eliminar entorno virtual anterior
echo
echo -e "${BLUE}[3/6] Eliminando entorno virtual anterior (si existe)...${NC}"
if [ -d "$VENV_DIR" ]; then
    echo "Eliminando $VENV_DIR..."
    rm -rf "$VENV_DIR"
fi

# [4/6] Crear entorno virtual
echo
echo -e "${BLUE}[4/6] Creando entorno virtual...${NC}"
$PYTHON_CMD -m venv "$VENV_DIR"
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ ERROR: No se pudo crear el entorno virtual${NC}"
    echo
    echo "Puede que necesites instalar python3-venv:"
    echo "  Ubuntu/Debian: sudo apt install python3-venv"
    exit 1
fi
echo -e "${GREEN}✅ Entorno virtual creado en $VENV_DIR${NC}"

# [5/6] Activar entorno virtual e instalar dependencias
echo
echo -e "${BLUE}[5/6] Activando entorno virtual e instalando dependencias...${NC}"
source "$VENV_DIR/bin/activate"

# Actualizar pip en el entorno virtual
echo "Actualizando pip..."
python -m pip install --upgrade pip

# Instalar wheel para evitar problemas de compilación
echo "Instalando wheel..."
python -m pip install wheel

# Instalar dependencias principales
echo "Instalando dependencias principales..."
python -m pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ ERROR: No se pudieron instalar las dependencias${NC}"
    echo
    echo "Intentando instalación individual de paquetes críticos..."
    
    # Instalar paquetes uno por uno para mejor diagnóstico
    python -m pip install numpy==1.21.2
    python -m pip install pandas==1.3.2
    python -m pip install scipy==1.7.1
    python -m pip install pynput==1.7.3
    python -m pip install requests==2.26.0
    python -m pip install paho-mqtt==1.5.1
    python -m pip install websocket-client==1.3.3
    
    # Paquetes que pueden ser problemáticos - instalar sin versión específica
    echo "Instalando paquetes de GUI..."
    
    python -m pip install PySide6 || {
        echo -e "${YELLOW}⚠️ ADVERTENCIA: No se pudo instalar PySide6${NC}"
        echo "Algunas funciones 3D pueden no estar disponibles"
    }
    
    python -m pip install pyqtgraph || {
        echo -e "${YELLOW}⚠️ ADVERTENCIA: No se pudo instalar pyqtgraph${NC}"
        echo "Algunas funciones 3D pueden no estar disponibles"
    }
    
    python -m pip install pyopengl || {
        echo -e "${YELLOW}⚠️ ADVERTENCIA: No se pudo instalar pyopengl${NC}"
        echo "Algunas funciones 3D pueden no estar disponibles"
    }
    
    python -m pip install opensimplex || {
        echo -e "${YELLOW}⚠️ ADVERTENCIA: No se pudo instalar opensimplex${NC}"
        echo "Algunas funciones pueden no estar disponibles"
    }
    
    python -m pip install plotly || {
        echo -e "${YELLOW}⚠️ ADVERTENCIA: No se pudo instalar plotly${NC}"
        echo "Funciones de gráficos avanzados pueden no estar disponibles"
    }
    
    echo
    echo -e "${YELLOW}⚠️ Instalación completada con advertencias${NC}"
    echo "El speedometer principal debería funcionar correctamente"
    echo "Algunas funciones 3D avanzadas pueden no estar disponibles"
else
    echo -e "${GREEN}✅ Dependencias instaladas correctamente${NC}"
fi

# [6/6] Crear scripts de lanzamiento
echo
echo -e "${BLUE}[6/6] Creando scripts de lanzamiento...${NC}"

# Crear launcher principal
cat > launch.sh << 'EOF'
#!/bin/bash
echo "Iniciando GW2 Speedometer Suite..."
cd "$(dirname "$0")"
source venv/bin/activate
python launcher.py
if [ $? -ne 0 ]; then
    echo "Presiona Enter para continuar..."
    read
fi
EOF

# Crear script de lanzamiento rápido del speedometer
cat > quick_speedometer.sh << 'EOF'
#!/bin/bash
echo "Iniciando Speedometer..."
cd "$(dirname "$0")"
source venv/bin/activate
python speedometer.py
echo "Presiona Enter para continuar..."
read
EOF

# Crear script de actualización
cat > update.sh << 'EOF'
#!/bin/bash
echo "Actualizando dependencias..."
cd "$(dirname "$0")"
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt --upgrade
echo "Actualización completada"
echo "Presiona Enter para continuar..."
read
EOF

# Hacer scripts ejecutables
chmod +x launch.sh
chmod +x quick_speedometer.sh
chmod +x update.sh

echo -e "${GREEN}✅ Scripts de lanzamiento creados${NC}"

echo
echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}          ✅ INSTALACIÓN COMPLETADA${NC}"
echo -e "${GREEN}===============================================${NC}"
echo
echo "Scripts disponibles:"
echo "  • ./launch.sh              - Launcher principal"
echo "  • ./quick_speedometer.sh   - Speedometer directo"
echo "  • ./update.sh              - Actualizar dependencias"
echo
echo "Para iniciar el programa:"
echo "  1. Ejecuta ./launch.sh para el launcher completo"
echo "  2. O ejecuta ./quick_speedometer.sh para inicio rápido"
echo
echo "IMPORTANTE:"
echo "- Siempre usa estos scripts para ejecutar el programa"
echo "- NO ejecutes los archivos .py directamente"
echo "- El entorno virtual se activa automáticamente"
echo

# Preguntar si quiere ejecutar el programa ahora
echo -n "¿Quieres ejecutar el launcher ahora? (s/n): "
read choice
if [ "$choice" = "s" ] || [ "$choice" = "S" ]; then
    echo
    echo "Iniciando launcher..."
    ./launch.sh
else
    echo
    echo "Ejecuta './launch.sh' cuando quieras usar el programa"
fi

echo
echo -e "${BLUE}===============================================${NC}" 