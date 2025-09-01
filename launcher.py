import sys
import os
import json
import shutil
import zipfile
import subprocess
import webbrowser
from pathlib import Path

import requests
from tqdm import tqdm

# --------------------------- Define the working folder ---------------------------
if getattr(sys, "frozen", False):
    WORKDIR = Path(sys.executable).parent.resolve()
else:
    WORKDIR = Path(__file__).parent.resolve()

STATE_FILE = WORKDIR / "launcher_state.json"


# ------------------------ Loading and saving local state ------------------------
def load_local_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def save_local_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


# ------------------------ Loading JSON over HTTP ------------------------
def load_json_from_url(url: str, timeout: int = 10) -> dict | None:
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[!] Failed to load JSON from {url}: {e}")
        return None


# ------------------------ Getting an Asset URL from GitHub Releases ------------------------
def get_asset_download_url(owner: str, repo: str, tag: str, asset_name: str) -> str:
    return f"https://github.com/{owner}/{repo}/releases/download/{tag}/{asset_name}"


# ------------------------ Uploading file with progress indicator ------------------------
def download_with_progress(url: str, dst: Path, timeout: int = 10):
    resp = requests.get(url, stream=True, timeout=timeout)
    resp.raise_for_status()
    total = int(resp.headers.get("content-length", 0))
    with open(dst, "wb") as f, tqdm(
        total=total, unit="B", unit_scale=True, desc=dst.name
    ) as bar:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                bar.update(len(chunk))


# ------------------------ Merge user data ------------------------
def merge_user_data(src: Path, dst: Path):
    if not src.exists():
        return
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


# ------------------------ Installing or updating the assembly ------------------------
def install_update(cfg: dict, state: dict):
    owner     = cfg["repo_owner"]
    repo      = cfg["repo_name"]
    tag       = cfg["version"]          # version =  name GitHub tag
    zip_name  = cfg["build_name"]
    run_file  = cfg["run_file"]
    notes_file= cfg["update_notes_file"]
    user_paths= cfg.get("user_data_path", [])


    download_url = get_asset_download_url(owner, repo, tag, zip_name)
    tmp_zip = WORKDIR / zip_name

    print(f"→ Download the release `{tag}` asset `{zip_name}`...")
    download_with_progress(download_url, tmp_zip)


    extract_dir = WORKDIR / zip_name.replace(".zip", "")


    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir()

    print("→ Unpacking...")
    with zipfile.ZipFile(tmp_zip, "r") as zf:
        zf.extractall(extract_dir)
    tmp_zip.unlink()


    for rel in user_paths:
        merge_user_data(WORKDIR / rel, extract_dir / rel)


    state.update({
        "repo_owner":      owner,
        "repo_name":       repo,
        "version":         tag,
        "install_path":    str(extract_dir),
        "run_file":        run_file,
    })
    save_local_state(state)

    print("✔ The update has been installed.")

    webbrowser.open(f"https://{owner}.github.io/{repo}/")


# ------------------------ Run any file in its directory ------------------------
def launch_file(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"File is not found: {path}")
    cwd = str(path.parent)

    if sys.platform.startswith("win"):
        # In Windows, use cmd /c start to set the working directory
        subprocess.Popen(['cmd', '/c', 'start', '', str(path)], cwd=cwd, shell=True)
    elif sys.platform == "darwin":
        # macOS: open
        subprocess.Popen(['open', str(path)], cwd=cwd)
    else:
        # Linux/Unix: xdg-open
        subprocess.Popen(['xdg-open', str(path)], cwd=cwd)



def main():
    state = load_local_state()

    default_base = "https://github.com/Arseniy0xff/LogAnalyzer_v4_builds/raw/refs/heads/main/"
    raw_base = state.get("raw_base", default_base)
    cfg_url  = f"{raw_base}/config.json"

    cfg = load_json_from_url(cfg_url)
    if not cfg:
        print("[!] Offline or error in config. Launch local version.")
        cfg = state

    remote_ver  = cfg.get("version")
    local_ver   = state.get("version")
    need_update = (local_ver != remote_ver)
    critical    = cfg.get("critical_update", 0) == 1

    if need_update and (local_ver is None or critical):
        install_update(cfg, state)
    elif need_update:
        ans = input(f"Update available {local_ver} → {remote_ver}. Install? [y/n]: ").strip().lower()
        if ans == "y":
            install_update(cfg, state)
    else:
        print("✔ You have the latest version.")

    install_path = Path(state.get("install_path", ""))
    run_file     = state.get("run_file", "")
    target       = install_path / run_file

    try:
        print(f"→ Run {target} ...")
        launch_file(target)
    except Exception as e:
        print(f"[!] Failed to start the application: {e}")


if __name__ == "__main__":
    main()
