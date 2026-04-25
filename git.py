#!/usr/bin/env python3
import sys
import argparse
import urllib.request
import json
import os
import tarfile
import shutil
import base64
import time

BASE_DIR = os.path.expanduser("~/.gemini-git")
ENV_FILE = os.path.join(BASE_DIR, ".env")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
DEBUG_MODE = False

def debug(msg):
    if DEBUG_MODE:
        sys.stdout.write(f"\033[90m[DEBUG] {msg}\033[0m\n")
        sys.stdout.flush()

def init_system():
    os.makedirs(BASE_DIR, exist_ok=True)
    if not os.path.exists(ENV_FILE):
        with open(ENV_FILE, "w") as f: f.write("# Gemini-Git Users\n")
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f: json.dump({"active_user": None}, f)

def get_tokens():
    tokens = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    user, token = line.strip().split("=", 1)
                    tokens[user] = token
    return tokens

def get_active_token():
    try:
        config = json.load(open(CONFIG_FILE))
        active_user = config.get("active_user")
        return active_user, get_tokens().get(active_user)
    except: return None, None

def format_size(bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024: return f"{bytes:.2f} {unit}"
        bytes /= 1024
    return f"{bytes:.2f} TB"

def progress_bar(current, total, prefix='', start_time=None):
    if DEBUG_MODE: return

    bar_length = 30
    speed_str = ""
    if start_time:
        elapsed = time.time() - start_time
        if elapsed > 0:
            speed = current / elapsed
            speed_str = f" @ {format_size(speed)}/s"

    if total > 0:
        percent = (current / total) * 100
        if percent > 100: percent = 100.0
        if current > total: current = total

        filled_length = int(bar_length * current // total)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        sys.stdout.write(f'\r{prefix} |{bar}| {percent:3.1f}% [{format_size(current)}/{format_size(total)}]{speed_str}')
    else:
        spinner = ['-', '\\', '|', '/'][int(time.time() * 4) % 4]
        sys.stdout.write(f'\r{prefix} {spinner} [{format_size(current)}]{speed_str}')
    
    sys.stdout.flush()

def api_request(endpoint, token, method="GET", data=None, silent_404=False):
    url = f"https://api.github.com/{endpoint.lstrip('/')}"
    debug(f"API Request: {method} {url}")
    req = urllib.request.Request(url, method=method)
    if token: 
        req.add_header("Authorization", f"token {token}")
        debug("Auth token included.")
    req.add_header("Accept", "application/vnd.github.v3+json")
    if data:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(data).encode("utf-8")
        debug(f"Payload size: {len(req.data)} bytes")
    try:
        with urllib.request.urlopen(req) as res:
            debug(f"Response HTTP {res.status}")
            return json.loads(res.read().decode()) if res.status != 204 else True
    except urllib.error.HTTPError as e:
        if e.code == 404 and silent_404: 
            debug("404 Obtenido (Silenciado intencionalmente)")
            return None
        print(f"\n[!] API Error ({e.code}): {e.reason}")
        debug(f"HTTPError Full read: {e.read().decode()}")
        return None
    except Exception as e:
        print(f"\n[!] Error: {e}")
        debug(f"Excepcion de red: {e}")
        return None

def push_file_to_github(local_file, repo, remote_path, user, token, message=None):
    with open(local_file, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf-8")
    
    res_get = api_request(f"repos/{user}/{repo}/contents/{remote_path}", token, silent_404=True)
    sha = res_get.get("sha") if res_get and isinstance(res_get, dict) else None

    payload = {
        "message": message or f"Gemini-Git: Subido {remote_path}",
        "content": content,
        "branch": "main"
    }
    if sha: payload["sha"] = sha

    return api_request(f"repos/{user}/{repo}/contents/{remote_path}", token, method="PUT", data=payload)

def cmd_clone(args):
    user, token = get_active_token()
    url = args.url.rstrip("/")
    parts = url.split('/')
    owner, repo = parts[-2], parts[-1].replace('.git', '')
    debug(f"Parsed URL -> Owner: {owner}, Repo: {repo}")
    
    res_repo = api_request(f"repos/{owner}/{repo}", token)
    branch = args.branch if args.branch else (res_repo.get("default_branch", "main") if res_repo else "main")
    estimated_total = (res_repo.get("size", 0) * 1024) if res_repo else 0
    debug(f"Branch: {branch}, API Size Estimate: {estimated_total} bytes")

    target_dir = args.directory if args.directory else f"{repo}_{branch}"
    if os.path.exists(target_dir):
        return print(f"[!] Error: La carpeta '{target_dir}' ya existe.")

    print(f"[*] Clonando: {owner}/{repo} (Rama: {branch})")
    tar_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.tar.gz"
    debug(f"Tarball URL: {tar_url}")
    
    try:
        req = urllib.request.Request(tar_url)
        if token: req.add_header('Authorization', f'token {token}')
        with urllib.request.urlopen(req) as res:
            cl = res.info().get('Content-Length')
            debug(f"Header Content-Length: {cl}")
            total_size = int(cl) if cl else estimated_total
            if not cl: debug("Warning: Usando estimacion de tamaño de la API.")
            
            tar_path = f"{repo}_{branch}_tmp.tar.gz"
            downloaded = 0
            start_time = time.time()
            
            if DEBUG_MODE: print(f"[*] Descargando a {tar_path}...")
            
            with open(tar_path, 'wb') as f:
                while True:
                    buf = res.read(32768)
                    if not buf: break
                    downloaded += len(buf)
                    f.write(buf)
                    if not DEBUG_MODE:
                        progress_bar(downloaded, total_size, prefix='[>] Descarga', start_time=start_time)
            
            if not DEBUG_MODE: print("\n[*] Extrayendo archivos...")
            else: print(f"[*] Extrayendo a {target_dir}...")
            
            with tarfile.open(tar_path, "r:gz") as tar:
                members = tar.getmembers()
                total_files = len(members)
                debug(f"Total files in tar: {total_files}")
                temp_extract = f"{repo}_{branch}_extract"
                os.makedirs(temp_extract, exist_ok=True)
                for i, m in enumerate(members):
                    tar.extract(m, path=temp_extract)
                    if not DEBUG_MODE and (i % 10 == 0 or i == total_files - 1):
                        progress_bar(i + 1, total_files, prefix='[>] Extracción')
                
                if not DEBUG_MODE: print("\n[*] Finalizando...")
                root = os.path.join(temp_extract, os.listdir(temp_extract)[0])
                if os.path.exists(target_dir): shutil.rmtree(target_dir)
                shutil.move(root, target_dir)
                shutil.rmtree(temp_extract)
                os.remove(tar_path)
                debug("Cleaned up temp files.")
        print(f"[✓] Clonación exitosa: {os.path.abspath(target_dir)}")
    except Exception as e:
        print(f"\n[!] Error durante clonacion: {e}")

def cmd_sync(args):
    user, token = get_active_token()
    if not token: return print("[!] Requiere setup.")
    base_dir = args.directory
    if not os.path.isdir(base_dir): return print(f"[!] '{base_dir}' no es un directorio.")
    
    print(f"[*] Sincronizando directorio '{base_dir}' con {user}/{args.repo}...")
    uploaded_count = 0
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for file in files:
            if file.startswith('.'): continue
            local_path = os.path.join(root, file)
            remote_path = os.path.relpath(local_path, base_dir).replace('\\', '/')
            print(f"  -> Subiendo: {remote_path} ...", end="", flush=True)
            res = push_file_to_github(local_path, args.repo, remote_path, user, token)
            if res:
                print(" [OK]")
                uploaded_count += 1
            else:
                print(" [ERROR]")
    print(f"\n[✓] Sincronización completa: {uploaded_count} archivos subidos.")

def cmd_info(args):
    user, token = get_active_token()
    if not token: return print("[!] No hay cuenta activa. Usa 'git setup'.")
    print(f"[*] Obteniendo información de cuenta de GitHub...")
    user_data = api_request("user", token)
    rate_data = api_request("rate_limit", token)
    if user_data and rate_data:
        print(f"\n[ Perfil Activo ]")
        print(f"  Usuario:   {user_data.get('login')}")
        print(f"  Nombre:    {user_data.get('name', 'N/A')}")
        print(f"  Repos:     {user_data.get('public_repos')} públicos")
        core = rate_data.get("resources", {}).get("core", {})
        print(f"\n[ Límites de API ]")
        print(f"  Restantes: {core.get('remaining')} de {core.get('limit')} peticiones por hora.")

def cmd_cat(args):
    user, token = get_active_token()
    if not token: return print("[!] Requiere setup.")
    res = api_request(f"repos/{user}/{args.repo}/contents/{args.path}", token, silent_404=True)
    if not res: return print(f"[!] Archivo no encontrado en GitHub.")
    if "content" in res:
        decoded = base64.b64decode(res["content"]).decode("utf-8")
        print(f"\n--- {args.path} ({user}/{args.repo}) ---\n")
        print(decoded)
        print("\n" + "-"*40)
    else:
        print("[!] No se pudo leer el archivo.")

def cmd_branches(args):
    user, token = get_active_token()
    repo_path = args.repo.replace("https://github.com/", "").rstrip("/")
    print(f"[*] Obteniendo ramas de {repo_path}...")
    res = api_request(f"repos/{repo_path}/branches", token)
    if res:
        print("\nRamas encontradas:")
        for b in res: print(f" - {b['name']}")

def cmd_create(args):
    user, token = get_active_token()
    if not token: return print("[!] Ejecuta 'git setup'.")
    res = api_request("user/repos", token, method="POST", data={"name": args.name, "auto_init": True})
    if res: print(f"[✓] Repo creado: {res.get('html_url')}")

def cmd_upload(args):
    user, token = get_active_token()
    if not os.path.exists(args.file): return print("[!] Archivo no existe.")
    remote_path = args.path if args.path else os.path.basename(args.file)
    print(f"[*] Subiendo {remote_path}...")
    if push_file_to_github(args.file, args.repo, remote_path, user, token, args.msg):
        print(f"[✓] Archivo subido.")

def setup_token():
    print("\n" + "="*50)
    print("         GEMINI-GIT: ASISTENTE DE ACCESO")
    print("="*50)
    sys.stdout.write("Pega tu GitHub Token: ")
    sys.stdout.flush()
    token = sys.stdin.readline().strip()
    if not token: return print("[!] Cancelado.")
    print(f"[*] Validando token con GitHub...")
    res = api_request("user", token)
    username = res.get("login") if res else None
    if username:
        tokens = get_tokens()
        tokens[username] = token
        with open(ENV_FILE, "w") as f:
            f.write("# Gemini-Git Users\n")
            for u, t in tokens.items(): f.write(f"{u}={t}\n")
        config = {"active_user": username}
        with open(CONFIG_FILE, "w") as f: json.dump(config, f)
        print(f"\n[✓] ¡Bienvenido {username}! Token activado.")
    else:
        print("\n[!] Token inválido.")

def main():
    global DEBUG_MODE
    init_system()
    parser = argparse.ArgumentParser(prog="git")
    parser.add_argument("--debug", action="store_true", help="Activar RAW logs para debug")
    subparsers = parser.add_subparsers(dest="command")
    
    subparsers.add_parser("setup")
    subparsers.add_parser("info")
    
    c = subparsers.add_parser("clone")
    c.add_argument("url")
    c.add_argument("directory", nargs="?")
    c.add_argument("-b", "--branch")
    
    b = subparsers.add_parser("branches")
    b.add_argument("repo")

    s = subparsers.add_parser("sync")
    s.add_argument("directory")
    s.add_argument("repo")
    
    cat = subparsers.add_parser("cat")
    cat.add_argument("repo")
    cat.add_argument("path")

    cr = subparsers.add_parser("create")
    cr.add_argument("name")

    up = subparsers.add_parser("upload")
    up.add_argument("file")
    up.add_argument("repo")
    up.add_argument("--path")
    up.add_argument("-m", "--msg")

    args = parser.parse_args()
    if args.debug:
        DEBUG_MODE = True
        print("[*] Gemini-Git ejecutándose en modo DEBUG (Raw Logs)")
    
    if args.command == "clone": cmd_clone(args)
    elif args.command == "sync": cmd_sync(args)
    elif args.command == "info": cmd_info(args)
    elif args.command == "branches": cmd_branches(args)
    elif args.command == "cat": cmd_cat(args)
    elif args.command == "create": cmd_create(args)
    elif args.command == "upload": cmd_upload(args)
    elif args.command == "setup": setup_token()
    else: parser.print_help()

if __name__ == "__main__": main()
