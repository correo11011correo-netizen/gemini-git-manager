# Gemini-Git: Manual de Usuario

**Gemini-Git** es una herramienta de terminal nativa, independiente y altamente portable, diseñada para interactuar con la API de GitHub sin necesidad de tener el cliente tradicional de Git instalado. Es ideal para entornos controlados, servidores sin Git, o para Agentes de IA.

---

## 🚀 Características Principales

*   **Multicuenta:** Guarda y gestiona múltiples Tokens de Acceso Personal (PAT) de GitHub.
*   **Sin Dependencias:** Solo requiere Python 3 estándar (sin `pip install`).
*   **Gestión de GitHub:** Crea repositorios y activa GitHub Pages directamente desde la terminal.
*   **Clonación Inteligente:** Descarga repositorios en formato `.tar.gz` (más rápido que `git clone` tradicional para descargas de un solo uso), con barras de progreso detalladas.

---

## 🛠️ Comandos Disponpios

### 1. Gestión de Sesión y Autenticación

El sistema requiere un **Personal Access Token (PAT)** de GitHub con permisos de `repo` para crear repositorios y leer repositorios privados.

*   `git setup`
    Inicia el asistente interactivo para registrar un nuevo token. El sistema validará el token y detectará automáticamente el nombre de usuario asociado.

*   `git users`
    Muestra la lista de cuentas guardadas en el sistema. El usuario activo (el que se usará para los comandos) estará marcado con un asterisco (`*`).

### 2. Operaciones de Código

*   `git clone <url_del_repositorio> [carpeta_destino]`
    Descarga y extrae el repositorio.
    *Ejemplo:* `git clone https://github.com/usuario/repo mi-carpeta`

### 3. Gestión de Repositorios (API)

*   `git create <nombre_del_repositorio> [-d "Descripción"] [--private]`
    Crea un nuevo repositorio directamente en tu cuenta de GitHub. Por defecto, inicializa el repositorio con un archivo `README.md`.
    *Ejemplo (Público):* `git create mi-app -d "Aplicación web genial"`
    *Ejemplo (Privado):* `git create mi-secreto --private`

*   `git pages <nombre_del_repositorio> [--branch nombre_rama]`
    Habilita el servicio de alojamiento estático **GitHub Pages** para el repositorio especificado.
    *Ejemplo:* `git pages mi-app` (Activa Pages usando la raíz de la rama `main`).
    *Ejemplo:* `git pages mi-app --branch gh-pages` (Usa una rama específica).

---

## 📁 Archivos de Configuración

La herramienta guarda su información de forma local y segura en la carpeta del usuario:

*   **Ruta Base:** `~/.gemini-git/`
*   **`.env`:** Archivo de texto plano donde se asocian los usuarios con sus tokens. *(Nunca compartas este archivo)*.
*   **`config.json`:** Guarda el estado actual de la aplicación (ej. qué usuario es el `active_user`).

## 💡 Notas para Agentes de IA

Si eres un agente automatizado utilizando esta herramienta:
1. Asegúrate de que el token esté configurado antes de invocar comandos que requieran autenticación (`create`, `pages`).
2. Los comandos devuelven salidas limpias empezando con `[✓]` para éxito y `[!]` para errores, facilitando el parseo de respuestas.
