#!/usr/bin/env python3
"""
Скрипт для деплоя модели на Qubu через API.

Использование:
  python deploy_qubu.py [--push-lfs] [--deploy]

Опции:
  --push-lfs    Загрузить GGUF в репозиторий Qubu через Git LFS
  --deploy      Обновить конфигурацию и запустить деплой через API
  --status      Проверить статус текущего деплоя
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error

# =============================================================================
# Конфигурация
# =============================================================================

QUBU_API_BASE = "https://qubu.ai/api"
QUBU_API_TOKEN = os.environ.get("QUBU_API_TOKEN", "")
QUBU_MODEL_ID = os.environ.get("QUBU_MODEL_ID", "c9827a6f-be25-40ea-8f80-a71275248188")

QUBU_GIT_USER = "REDACTED_USERNAME"
QUBU_GIT_TOKEN = os.environ.get("QUBU_GIT_TOKEN", "")
QUBU_GIT_URL = (
    f"https://{QUBU_GIT_USER}:{QUBU_GIT_TOKEN}@"
    f"git.qubu.ai/{QUBU_GIT_USER}/"
    f"ml_model-intellektualniy-tyutor-na-osnove-otkrytykh-bolshikh-yazykovykh-modelei-dlya-spo.git"
)

GGUF_URL = (
    "https://huggingface.co/bartowski/Mistral-Small-24B-Instruct-2501-GGUF/"
    "resolve/main/Mistral-Small-24B-Instruct-2501-Q4_K_M.gguf"
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def api_request(method: str, path: str, data: dict = None) -> dict:
    """Make API request to Qubu."""
    url = f"{QUBU_API_BASE}{path}"
    headers = {
        "Authorization": f"Bearer {QUBU_API_TOKEN}",
        "Content-Type": "application/json",
    }

    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"API Error {e.code}: {error_body}")
        return {"error": str(e), "status_code": e.code}
    except Exception as e:
        print(f"Request failed: {e}")
        return {"error": str(e)}


def get_service_code() -> str:
    """Read service_gguf.py content."""
    path = os.path.join(SCRIPT_DIR, "service_gguf.py")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def get_bentofile() -> str:
    """Read bentofile.yaml content."""
    path = os.path.join(SCRIPT_DIR, "bentofile.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def get_startup_script() -> str:
    """Read startup_script.sh content."""
    path = os.path.join(SCRIPT_DIR, "startup_script.sh")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def push_to_lfs(repo_dir: str = "./qubu-model-repo"):
    """Clone Qubu repo, setup LFS, download GGUF, push."""
    print("=" * 60)
    print("STEP 1: Cloning Qubu repository")
    print("=" * 60)

    if os.path.isdir(os.path.join(repo_dir, ".git")):
        print(f"Repository exists at {repo_dir}, pulling...")
        subprocess.run(["git", "pull", "origin", "main"],
                       cwd=repo_dir, check=False)
    else:
        print(f"Cloning to {repo_dir}...")
        subprocess.run(["git", "clone", QUBU_GIT_URL, repo_dir], check=True)

    print()
    print("=" * 60)
    print("STEP 2: Setting up Git LFS")
    print("=" * 60)
    subprocess.run(["git", "lfs", "install"], cwd=repo_dir, check=True)
    subprocess.run(["git", "lfs", "track", "*.gguf"], cwd=repo_dir, check=True)
    subprocess.run(["git", "add", ".gitattributes"], cwd=repo_dir, check=False)

    print()
    print("=" * 60)
    print("STEP 3: Downloading GGUF model (~15 GB)")
    print("=" * 60)
    gguf_path = os.path.join(repo_dir, "Mistral-Small-24B-Instruct-2501-Q4_K_M.gguf")
    if not os.path.exists(gguf_path):
        print("Downloading... (this may take 15-30 minutes)")
        subprocess.run([
            "wget", "-c", "-O", gguf_path, GGUF_URL
        ], check=True)
        size = os.path.getsize(gguf_path) / (1024 ** 3)
        print(f"Downloaded: {size:.1f} GB")
    else:
        size = os.path.getsize(gguf_path) / (1024 ** 3)
        print(f"GGUF already exists: {size:.1f} GB")

    print()
    print("=" * 60)
    print("STEP 4: Copying project files")
    print("=" * 60)

    # Copy service file
    src = os.path.join(SCRIPT_DIR, "service_gguf.py")
    dst = os.path.join(repo_dir, "service_gguf.py")
    if os.path.exists(src):
        subprocess.run(["cp", src, dst], check=True)
        print("  - service_gguf.py")

    # Copy bentofile
    src = os.path.join(SCRIPT_DIR, "bentofile.yaml")
    dst = os.path.join(repo_dir, "bentofile.yaml")
    if os.path.exists(src):
        subprocess.run(["cp", src, dst], check=True)
        print("  - bentofile.yaml")

    # Copy requirements
    src = os.path.join(SCRIPT_DIR, "requirements_gguf.txt")
    dst = os.path.join(repo_dir, "requirements.txt")
    if os.path.exists(src):
        subprocess.run(["cp", src, dst], check=True)
        print("  - requirements.txt")

    print()
    print("=" * 60)
    print("STEP 5: Committing and pushing to Qubu")
    print("=" * 60)
    subprocess.run(["git", "add", "-A"], cwd=repo_dir, check=True)
    subprocess.run([
        "git", "commit", "-m",
        "Deploy: GGUF Q4_K_M model + llama-cpp-python service"
    ], cwd=repo_dir, check=False)
    print("Pushing via Git LFS (15 GB, may take 15-30 min)...")
    subprocess.run(["git", "push", "origin", "main"], cwd=repo_dir, check=True)

    print()
    print("=" * 60)
    print("SUCCESS! Files pushed to Qubu repository.")
    print("=" * 60)


def deploy_via_api():
    """Update inference config and trigger deploy via Qubu API."""
    print("=" * 60)
    print("Updating inference config via API")
    print("=" * 60)

    code = get_service_code()
    bentofile = get_bentofile()
    startup_script = get_startup_script()

    config = {
        "code": code,
        "requirements": "bentoml>=1.2.0",
        "env": f"MODEL_PATH=/workspace/model\nN_CTX=2048\nN_GPU_LAYERS=-1",
        "startup_script": startup_script,
        "bentofile": bentofile,
    }

    result = api_request(
        "PUT",
        f"/models/{QUBU_MODEL_ID}/inference/config",
        config,
    )

    if "error" in result:
        print(f"Failed to update config: {result}")
        return False

    print(f"Config updated: {json.dumps(result, indent=2)[:200]}...")

    print()
    print("=" * 60)
    print("Triggering deploy")
    print("=" * 60)

    result = api_request(
        "POST",
        f"/models/{QUBU_MODEL_ID}/inference/proxy",
    )

    if "error" in result:
        print(f"Failed to trigger deploy: {result}")
        return False

    print(f"Deploy triggered: {json.dumps(result, indent=2)[:300]}...")

    return True


def check_status():
    """Check current deploy status."""
    result = api_request(
        "GET",
        f"/models/{QUBU_MODEL_ID}/inference/proxy",
    )
    print(json.dumps(result, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description="Deploy AI Tutor to Qubu")
    parser.add_argument("--push-lfs", action="store_true",
                        help="Push GGUF to Qubu via Git LFS")
    parser.add_argument("--deploy", action="store_true",
                        help="Update config and trigger deploy via API")
    parser.add_argument("--status", action="store_true",
                        help="Check deploy status")
    parser.add_argument("--repo-dir", default="./qubu-model-repo",
                        help="Local path for Qubu git repo")

    args = parser.parse_args()

    if not any([args.push_lfs, args.deploy, args.status]):
        parser.print_help()
        sys.exit(1)

    if args.push_lfs:
        push_to_lfs(args.repo_dir)

    if args.deploy:
        deploy_via_api()

    if args.status:
        check_status()


if __name__ == "__main__":
    main()
