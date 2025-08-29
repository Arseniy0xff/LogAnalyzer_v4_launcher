# Python GitHub Auto-Updater Launcher

A simple launcher written in Python that checks for updates on GitHub, downloads and installs new builds, merges user data, and launches the main application automatically.

---

## Features

- Loads remote configuration (`config.json`) from a GitHub repository.
- Compares local and remote versions and handles:
  - First-time installs
  - Critical updates (forced)
  - Optional updates with user confirmation
- Downloads ZIP builds with progress bar using `tqdm`.
- Merges user data folders into each new build without data loss.
- Saves all important settings and state in a local JSON file.
- Opens release notes in the default browser after updating.
- Launches any file type by OS association or custom logic for scripts.
- Works offline by falling back to the last known local state.
- Configurable remote base URL stored alongside launcher state.

---

## Prerequisites

- Python 3.6 or newer
- `requests` library
- `tqdm` library

Install dependencies with:

```bash
pip install requests tqdm
```

---

## Installation

1. Clone or download this repository.
2. Ensure `launcher.py` and `launcher_state.json` (auto-generated) are in the same folder.
3. Run the launcher:

   ```bash
   python launcher.py
   ```

---

## Configuration

On first run the launcher will create `launcher_state.json` with default values:

```json
{
  "raw_base": "https://raw.githubusercontent.com/owner/build_proj/main",
  "version": null,
  "critical_update": 0,
  "install_path": null,
  "run_file": null,
  "user_data_path": ["user_data/"]
}
```

- `raw_base`  
  Base URL for raw GitHub content. Change this to point to your repo or branch.

- `version`  
  Last installed version of the application.

- `critical_update`  
  Flag for forced updates (1 = forced, 0 = optional).

- `install_path`  
  Local folder where the ZIP build is extracted.

- `run_file`  
  Relative path inside `install_path` to the main executable or script.

- `user_data_path`  
  List of folders to preserve and merge on each update.

You can edit `launcher_state.json` manually to customize the repository URL or adjust paths.

---

## Usage

1. Run `launcher.py` (or the compiled EXE).
2. The launcher fetches `config.json` from `raw_base`.
3. It compares remote `version` to local.  
4. If update is needed:
   - Forced updates install automatically.
   - Optional updates prompt `[y/n]` in the console.
5. ZIP build is downloaded with a progress bar and extracted into `install_path`.
6. User data folders are merged on top of the new build.
7. `launcher_state.json` is updated with the new state.
8. Default browser opens the release notes URL.
9. The main application (`run_file`) is launched via OS file associations.

---

## Packaging as a Single EXE

To bundle the launcher into one executable with PyInstaller:

```bash
pip install pyinstaller
pyinstaller --onefile launcher.py
```

Modify the working directory logic in `launcher.py` to handle frozen builds:

```python
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).parent.resolve()
else:
    APP_DIR = Path(__file__).parent.resolve()
```

Use `APP_DIR` for all file reads, downloads, and writes so the EXE stores state next to itself.

