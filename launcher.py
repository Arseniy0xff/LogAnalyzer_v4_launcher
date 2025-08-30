import os
import sys
import json
import shutil
import zipfile
import subprocess
import webbrowser
from pathlib import Path

import requests
from tqdm import tqdm


# ========== Files and paths ==========
STATE_FILE = "launcher_state.json"
if getattr(sys, "frozen", False):
    # runing how PyInstaller EXE
    WORKDIR = Path(sys.executable).parent.resolve()
else:
    # Run from .py
    WORKDIR = Path(__file__).parent.resolve()
# ==================================


def load_local_state():
    """Reads local config/state. If not, returns empty."""
    path = WORKDIR / STATE_FILE
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_local_state(state: dict):
    """Saves local config/state."""
    path = WORKDIR / STATE_FILE
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def load_json_from_url(url):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Loading error {url}: {e}")
        return None


def download_with_progress(url, dst: Path):
    r = requests.get(url, stream=True, timeout=10)
    r.raise_for_status()
    total = int(r.headers.get("content-length", 0))
    with open(dst, "wb") as f, tqdm(total=total, unit="B", unit_scale=True, desc=dst.name) as bar:
        for chunk in r.iter_content(8192):
            if chunk:
                f.write(chunk)
                bar.update(len(chunk))


def merge_user_data(src: Path, dst: Path):
    if not src.exists():
        return
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


def install_update(cfg: dict, state: dict, raw_base: str):
    zip_name = cfg["build_name"]
    url = f"{raw_base}/{zip_name}"
    tmp_zip = WORKDIR / zip_name

    print(f"Loading build {zip_name}...")
    download_with_progress(url, tmp_zip)

    extract_dir = WORKDIR / zip_name.replace(".zip", "")

    # del old
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir()

    print("Unpacking...")
    with zipfile.ZipFile(tmp_zip, "r") as z:
        z.extractall(extract_dir)
    tmp_zip.unlink()

    # merging user data
    for rel in cfg.get("user_data_path", []):
        merge_user_data(WORKDIR / rel, extract_dir / rel)


    state.update({
        "version": cfg["version"],
        "critical_update": cfg["critical_update"],
        "install_path": str(extract_dir),
        "run_file": cfg["run_file"],
        "raw_base": raw_base
    })
    save_local_state(state)

    print("Update installed.")
    notes_url = f"https://arseniy0xff.github.io/LogAnalyzer_v4_builds/"
    webbrowser.open(notes_url)


def launch_file(path: Path):
    """
    Opens a file in an associated application,
    By installing CWD = folder where this file lies.
    """
    if not path.exists():
        raise FileNotFoundError(f"Не найден файл: {path}")

    cwd = str(path.parent)

    if sys.platform.startswith("win"):
        subprocess.Popen(
            ['cmd', '/c', 'start', '', str(path)],
            cwd=cwd,
            shell=True
        )

    elif sys.platform == "darwin":
        subprocess.Popen(
            ['open', str(path)],
            cwd=cwd
        )

    else:
        subprocess.Popen(
            ['xdg-open', str(path)],
            cwd=cwd
        )


def main():
    state = load_local_state()


    default_base = "https://github.com/Arseniy0xff/LogAnalyzer_v4_builds/raw/refs/heads/main/"
    raw_base = state.get("raw_base", default_base)


    cfg_url = f"{raw_base}/config.json"
    cfg = load_json_from_url(cfg_url)
    if not cfg:
        print("Offline or config error, used local state.")
        cfg = state

    remote_ver = cfg.get("version")
    local_ver = state.get("version")
    need_update = (local_ver != remote_ver)
    critical = cfg.get("critical_update", 0) == 1


    if need_update and (local_ver is None or critical):
        install_update(cfg, state, raw_base)
    elif need_update:
        ans = input(f"Update {local_ver} → {remote_ver}. Install? [y/n]: ").lower()
        if ans == "y":
            install_update(cfg, state, raw_base)
    else:
        print("You have last version.")


    install_path = Path(state.get("install_path", ""))
    run_file = state.get("run_file", "")
    exe = install_path / run_file
    try:
        print(f"Run {exe} ...")
        launch_file(exe)
    except Exception as e:
        print(f"Failed to start the application: {e}")


if __name__ == "__main__":
    main()
