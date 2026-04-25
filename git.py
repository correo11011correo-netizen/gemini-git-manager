#!/usr/bin/env python3
import sys
import argparse
import urllib.request
import json
import os
import base64
import time
import hashlib
import tarfile
import shutil

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

def api_request(endpoint, token, method="GET", data=None, silent_404=False):
    url = f"https://api.github.com/{endpoint.lstrip('/')}"
    debug(f"API Req: {method} {url}")
    req = urllib.request.Request(url, method=method)
    if token: req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    if data:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(data).encode("utf-8")
    try:
        with urllib.request.urlopen(req) as res:
            return json.loads(res.read().decode()) if res.status != 204 else True
    except Exception as e:
        if hasattr(e, 'code') and e.code == 404 and silent_404: return None
        return None

def get_local_sha1(file_path):
    if not os.path.exists(file_path): return None
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
            header = f"blob {len(content)}\0".encode('utf-8')
            return hashlib.sha1(header + content).hexdigest()
    except: return None

def download_file(url, token, target_path):
    req = urllib.request.Request(url)
    if token: req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github.v3.raw")
    try:
        with urllib.request.urlopen(req) as res:
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with open(target_path, 'wb') as f:
                while True:
                    buf = res.read(65536)
                    if not buf: break
                    f.write(buf)
            return True
    except: return False

def cmd_pull(args):
    user, token = get_active_token()
    url = args.url.rstrip("/")
    parts = url.split('/')
    owner, repo = parts[-2], parts[-1].replace('.git', '')
    res_repo = api_request(f"repos/{owner}/{repo}", token)
    branch = args.branch if args.branch else (res_repo.get("default_branch", "main") if res_repo else "main")
    target_dir = args.directory if args.directory else repo
    print(f"[*] Sincronización Incremental: {owner}/{repo} (Rama: {branch})")
    ref_data = api_request(f"repos/{owner}/{repo}/git/ref/heads/{branch}", token)
    if not ref_data: return print("[!] Error obteniendo ref.")
    commit_sha = ref_data['object']['sha']
    tree_res = api_request(f"repos/{owner}/{repo}/git/trees/{commit_sha}?recursive=1", token)
    if not tree_res or "tree" not in tree_res: return print("[!] Error obteniendo árbol.")
    remote_files = [item for item in tree_res["tree"] if item["type"] == "blob"]
    to_download = []
    for item in remote_files:
        path = item["path"]
        local_path = os.path.join(target_dir, path)
        if get_local_sha1(local_path) != item["sha"]: to_download.append(item)
    if not to_download: return print("[✓] Todo al día.")
    print(f"[*] Actualizando {len(to_download)} archivos...")
    for i, item in enumerate(to_download):
        path = item["path"]
        file_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{commit_sha}/{urllib.parse.quote(path)}"
        local_path = os.path.join(target_dir, path)
        print(f"\r[>] [{i+1}/{len(to_download)}] {path[:40]}...", end="", flush=True)
        download_file(file_url, token, local_path)
    print("\n[✓] Listo.")

def cmd_push(args):
    user, token = get_active_token()
    if not token: return print("[!] No hay token configurado. Usa 'git setup'.")
    url = args.url.rstrip("/")
    parts = url.split('/')
    owner, repo = parts[-2], parts[-1].replace('.git', '')
    res_repo = api_request(f"repos/{owner}/{repo}", token)
    if not res_repo: return print("[!] Repo no encontrado.")
    branch = args.branch if args.branch else res_repo.get("default_branch", "main")
    target_dir = args.directory if args.directory else repo
    if not os.path.isdir(target_dir): return print(f"[!] Directorio {target_dir} no existe.")

    print(f"[*] Preparando Push a: {owner}/{repo} (Rama: {branch})")
    ref_data = api_request(f"repos/{owner}/{repo}/git/ref/heads/{branch}", token)
    if not ref_data: return print("[!] Error obteniendo ref.")
    commit_sha = ref_data['object']['sha']
    tree_res = api_request(f"repos/{owner}/{repo}/git/trees/{commit_sha}?recursive=1", token)
    if not tree_res: return print("[!] Error obteniendo árbol.")
    remote_files = {item["path"]: item["sha"] for item in tree_res.get("tree", []) if item["type"] == "blob"}

    tree_updates = []
    print("[*] Escaneando archivos locales y comparando...")
    for root, _, files in os.walk(target_dir):
        if '.git' in root or '.gemini' in root or '__pycache__' in root: continue
        for f in files:
            local_path = os.path.join(root, f)
            rel_path = os.path.relpath(local_path, target_dir).replace("\\", "/")
            local_sha = get_local_sha1(local_path)
            
            if remote_files.get(rel_path) != local_sha:
                with open(local_path, "rb") as lf:
                    content = lf.read()
                try:
                    content_str = content.decode('utf-8')
                    blob_data = {"content": content_str, "encoding": "utf-8"}
                except UnicodeDecodeError:
                    blob_data = {"content": base64.b64encode(content).decode('utf-8'), "encoding": "base64"}
                
                print(f"[>] Subiendo blob: {rel_path}...")
                blob_res = api_request(f"repos/{owner}/{repo}/git/blobs", token, method="POST", data=blob_data)
                if blob_res and 'sha' in blob_res:
                    tree_updates.append({
                        "path": rel_path,
                        "mode": "100644",
                        "type": "blob",
                        "sha": blob_res['sha']
                    })
                else:
                    print(f"[!] Error subiendo {rel_path}")

    if not tree_updates:
        return print("[✓] Todo está al día. No hay cambios locales para subir.")

    print("[*] Creando nuevo árbol...")
    new_tree_res = api_request(f"repos/{owner}/{repo}/git/trees", token, method="POST", data={
        "base_tree": tree_res["sha"],
        "tree": tree_updates
    })
    
    commit_msg = args.message if args.message else "Auto-commit from Gemini-Git"
    print(f"[*] Creando commit: '{commit_msg}'...")
    new_commit_res = api_request(f"repos/{owner}/{repo}/git/commits", token, method="POST", data={
        "message": commit_msg,
        "tree": new_tree_res["sha"],
        "parents": [commit_sha]
    })
    
    print("[*] Actualizando referencia en rama...")
    api_request(f"repos/{owner}/{repo}/git/refs/heads/{branch}", token, method="PATCH", data={
        "sha": new_commit_res["sha"]
    })
    print(f"[✓] Push exitoso. Commit: {new_commit_res['sha']}")


def cmd_info(args):
    user, token = get_active_token()
    u = api_request("user", token)
    r = api_request("rate_limit", token)
    if u: print(f"\n[ Perfil: {u['login']} ]\nRepos: {u['public_repos']}\nAPI: {r['resources']['core']['remaining']}/{r['resources']['core']['limit']}")

def setup_token():
    sys.stdout.write("Pega tu Token: "); sys.stdout.flush()
    token = sys.stdin.readline().strip()
    res = api_request("user", token)
    if res:
        save_token(res['login'], token)
        print(f"[✓] Hola {res['login']}")

def save_token(user, token):
    with open(ENV_FILE, "w") as f: f.write(f"{user}={token}\n")
    with open(CONFIG_FILE, "w") as f: json.dump({"active_user": user}, f)

def main():
    global DEBUG_MODE
    init_system()
    parser = argparse.ArgumentParser(prog="git")
    parser.add_argument("--debug", action="store_true")
    subparsers = parser.add_subparsers(dest="command")
    
    pull_p = subparsers.add_parser("pull")
    pull_p.add_argument("url")
    pull_p.add_argument("directory", nargs="?")
    pull_p.add_argument("-b", "--branch")
    
    push_p = subparsers.add_parser("push")
    push_p.add_argument("url")
    push_p.add_argument("directory", nargs="?")
    push_p.add_argument("-b", "--branch")
    push_p.add_argument("-m", "--message", default="Actualización desde Gemini-Git")
    
    subparsers.add_parser("info")
    subparsers.add_parser("setup")
    
    args = parser.parse_args()
    if args.debug: DEBUG_MODE = True
    
    if args.command == "pull": cmd_pull(args)
    elif args.command == "push": cmd_push(args)
    elif args.command == "info": cmd_info(args)
    elif args.command == "setup": setup_token()
    else: parser.print_help()

if __name__ == "__main__": main()
