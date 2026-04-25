#!/usr/bin/env python3
import sys
import argparse
import urllib.request
import json
import os
import tarfile
import shutil
import base64

BASE_DIR = os.path.expanduser("~/.gemini-git")
ENV_FILE = os.path.join(BASE_DIR, ".env")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

def init_system():
    os.makedirs(BASE_DIR, exist_ok=True)
    if not os.path.exists(ENV_FILE):
        with open(ENV_FILE, "w") as f: f.write("# Gemini-Git Users\n")
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f: json.dump({"active_user": None}, f)

def get_config():
    with open(CONFIG_FILE, "r") as f: return json.load(f)

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
    config = get_config()
    active_user = config.get("active_user")
    return active_user, get_tokens().get(active_user)

def api_request(endpoint, token, method="GET", data=None):
    url = f"https://api.github.com/{endpoint.lstrip('/')}"
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
        print(f"[!] Error: {e}")
        return None

def cmd_upload(args):
    user, token = get_active_token()
    if not token: return print("[!] Ejecuta 'git setup' primero.")
    
    if not os.path.exists(args.file):
        return print(f"[!] El archivo {args.file} no existe.")

    with open(args.file, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf-8")

    path = args.path if args.path else os.path.basename(args.file)
    print(f"[*] Subiendo {path} a {user}/{args.repo}...")
    
    # Intentar obtener el SHA si el archivo ya existe (para actualizar)
    res_get = api_request(f"repos/{user}/{args.repo}/contents/{path}", token)
    sha = res_get.get("sha") if res_get and isinstance(res_get, dict) else None

    payload = {
        "message": args.msg or f"Upload {path} via Gemini-Git",
        "content": content,
        "branch": "main"
    }
    if sha: payload["sha"] = sha

    res = api_request(f"repos/{user}/{args.repo}/contents/{path}", token, method="PUT", data=payload)
    if res: print(f"[✓] Archivo subido: {path}")

def cmd_create(args):
    user, token = get_active_token()
    if not token: return print("[!] Ejecuta 'git setup'.")
    res = api_request("user/repos", token, method="POST", data={"name": args.name, "auto_init": True})
    if res: print(f"[✓] Repo creado: {res.get('html_url')}")

def main():
    init_system()
    parser = argparse.ArgumentParser(prog="git")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("setup")
    
    # Create
    create_p = subparsers.add_parser("create")
    create_p.add_argument("name")

    # Upload
    upload_p = subparsers.add_parser("upload")
    upload_p.add_argument("file")
    upload_p.add_argument("repo")
    upload_p.add_argument("--path", help="Ruta en el repo")
    upload_p.add_argument("-m", "--msg", help="Mensaje de commit")

    # Clone
    clone_p = subparsers.add_parser("clone")
    clone_p.add_argument("url")

    args = parser.parse_args()
    if args.command == "create": cmd_create(args)
    elif args.command == "upload": cmd_upload(args)
    elif args.command == "setup": # (Llamar a interactive_setup de antes)
        pass 
    # ... resto de comandos ...

if __name__ == "__main__": main()
