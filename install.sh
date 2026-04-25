#!/bin/bash

# --- Configuración ---
INSTALL_DIR="$HOME/.gemini-git"
BIN_DIR="$HOME/bin"
GIT_SCRIPT_URL="https://raw.githubusercontent.com/correo11011correo-netizen/gemini-git-manager/main/git.py"

echo "================================================="
echo "   INSTALADOR UNIVERSAL GEMINI-GIT (MULTI-ARCH)"
echo "================================================="

# 1. Detección de Sistema y Arquitectura
echo "[*] Analizando entorno de hardware y sistema..."
OS=$(uname -s)
ARCH=$(uname -m)

echo "  -> Sistema Operativo: $OS"
echo "  -> Arquitectura:      $ARCH"

# Normalizar arquitectura para uso futuro
case "$ARCH" in
    x86_64|amd64) ARCH_NORMAL="x86_64" ;;
    aarch64|arm64) ARCH_NORMAL="arm64" ;;
    armv7l|armhf)  ARCH_NORMAL="arm32" ;;
    *)             ARCH_NORMAL="unknown" ;;
esac

# 2. Detección de Gestor de Paquetes
PKG_MANAGER=""
if command -v apt-get &> /dev/null; then PKG_MANAGER="apt"
elif command -v yum &> /dev/null; then PKG_MANAGER="yum"
elif command -v dnf &> /dev/null; then PKG_MANAGER="dnf"
elif command -v pacman &> /dev/null; then PKG_MANAGER="pacman"
elif command -v apk &> /dev/null; then PKG_MANAGER="apk" # Alpine Linux
elif command -v pkg &> /dev/null; then PKG_MANAGER="pkg" # Termux/FreeBSD
elif command -v brew &> /dev/null; then PKG_MANAGER="brew" # macOS
fi

echo "  -> Gestor detectado:  ${PKG_MANAGER:-Ninguno/Desconocido}"

# 3. Verificar e Instalar Python 3
echo "[*] Comprobando dependencias (Python 3)..."
if ! command -v python3 &> /dev/null; then
    echo "[!] Python 3 no encontrado. Intentando instalación automática..."
    
    if [ -z "$PKG_MANAGER" ]; then
        echo "[ERROR] No se detectó un gestor de paquetes soportado. Instala Python 3 manualmente."
        exit 1
    fi

    # Intentar instalar según el gestor
    case "$PKG_MANAGER" in
        apt)   sudo apt-get update && sudo apt-get install -y python3 ;;
        yum)   sudo yum install -y python3 ;;
        dnf)   sudo dnf install -y python3 ;;
        pacman)sudo pacman -Sy --noconfirm python ;;
        apk)   sudo apk add python3 ;;
        pkg)   pkg install -y python ;; # Termux no usa sudo por defecto
        brew)  brew install python3 ;;
    esac

    # Verificar si la instalación fue exitosa
    if ! command -v python3 &> /dev/null; then
        echo "[ERROR] Falló la instalación automática de Python. Instálalo manualmente."
        exit 1
    fi
else
    echo "[✓] Python 3 detectado: $(python3 --version 2>&1)"
fi

# 4. Verificar conectividad con GitHub
echo "[*] Verificando conexión con GitHub API..."
if ! curl -s --head https://api.github.com | head -n 1 | grep "200" &> /dev/null; then
    echo "[!] Advertencia: No se puede alcanzar la API de GitHub. Revisa tu red."
fi

# 5. Preparar directorios y binarios
echo "[*] Desplegando archivos en $BIN_DIR..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"

if [ -f "/home/userland/bin/git" ]; then
    cp "/home/userland/bin/git" "$BIN_DIR/git"
else
    echo "  -> Descargando última versión de GitHub..."
    curl -s -L -o "$BIN_DIR/git" "$GIT_SCRIPT_URL"
fi

chmod +x "$BIN_DIR/git"

# 6. Configurar PATH
echo "[*] Asegurando variables de entorno..."
SHELL_RC=""
if [[ "$SHELL" == *"zsh"* ]]; then SHELL_RC="$HOME/.zshrc"
elif [[ "$SHELL" == *"bash"* ]]; then SHELL_RC="$HOME/.bashrc"
else SHELL_RC="$HOME/.profile" # Fallback para sh/dash
fi

if ! grep -q "$BIN_DIR" "$SHELL_RC" 2>/dev/null; then
    echo "export PATH=\"\$HOME/bin:\$PATH\"" >> "$SHELL_RC"
    echo "[✓] PATH añadido a $SHELL_RC"
fi

# 7. Finalización
echo "================================================="
echo "[✓] INSTALACIÓN COMPLETADA EXITOSAMENTE"
echo "================================================="
echo "-> Sistema: $OS ($ARCH_NORMAL)"
echo ""
echo "Para activar la herramienta ahora, ejecuta:"
echo "  source $SHELL_RC"
echo ""

# Ejecutar setup si no hay configuración previa
if [ ! -f "$INSTALL_DIR/.env" ]; then
    echo "[i] Iniciando asistente de configuración inicial..."
    export PATH="$BIN_DIR:$PATH"
    git setup
fi
