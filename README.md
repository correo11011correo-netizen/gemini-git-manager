# Gemini-Git 🚀

Herramienta Git nativa y liviana optimizada para Agentes IA y entornos sin el cliente Git completo preinstalado. Utiliza directamente la API de GitHub.

## Características
- **Independiente:** Solo requiere Python 3 y librerías estándar. No necesita binarios de Git.
- **Sincronización Inteligente:** Realiza `pull` y `push` incrementales comprobando los hashes (SHA1) de los archivos, transfiriendo solo lo necesario.
- **Seguro:** Administra Tokens de Acceso Personal (PAT) de GitHub para operar de forma segura con repositorios públicos y privados.
- **IA-Ready:** Diseñado con formatos de salida limpios para ser integrado fácilmente en flujos de trabajo automatizados.

## Instalación
```bash
./install.sh
source ~/.bashrc
```

## Comandos Disponibles

### `git setup`
Inicia el asistente para configurar tu Token de Acceso Personal de GitHub.
```bash
git setup
```

### `git pull <url> [directorio] [-b rama]`
Descarga y sincroniza de forma incremental un repositorio remoto al directorio local. Si no se especifica directorio, usa el nombre del repo.
```bash
git pull https://github.com/usuario/repo
git pull https://github.com/usuario/repo mi_carpeta_local -b develop
```

### `git push <url> [directorio] [-b rama] [-m "mensaje"]`
Analiza los archivos locales, los compara con el repositorio remoto y sube (push) únicamente los archivos modificados o nuevos creando un nuevo commit.
```bash
git push https://github.com/usuario/repo
git push https://github.com/usuario/repo . -m "Actualizando estilos y scripts"
```

### `git info`
Muestra información de la cuenta asociada al Token activo y el estado de límite de peticiones (rate limit) de la API de GitHub.
```bash
git info
```

### Comandos Locales (Nuevos)
Gemini-Git ahora actúa como un "wrapper" inteligente. Si los siguientes comandos estándar son invocados, intentará usar el binario `git` real del sistema para gestionar repositorios locales, manteniendo intacta su capacidad de comunicación nativa con la API de GitHub:
- `git init` - Inicializa un repositorio local.
- `git add` - Añade archivos al índice.
- `git commit` - Registra cambios en el repositorio.
- `git status` - Muestra el estado del árbol de trabajo.
- `git log` - Muestra el historial de commits.
- `git config` - Obtiene y establece opciones del repositorio o globales.
