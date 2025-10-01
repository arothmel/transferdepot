import os, json, shutil
from pathlib import Path
from flask import current_app
from werkzeug.utils import secure_filename

# --- helpers ---
def _groups_file_path() -> Path:
    return Path(current_app.config.get("GROUPS_FILE") or os.getenv("TD_GROUPS_FILE", "groups.json"))

def _upload_root() -> Path:
    return Path(current_app.config["UPLOAD_FOLDER"])

# --- groups ---
def load_groups():
    p = _groups_file_path()
    if not p.exists():
        raise FileNotFoundError(f"Groups file not found: {p}")
    with p.open("r") as f:
        return json.load(f)

def save_groups(groups):
    p = _groups_file_path()
    p.write_text(json.dumps(groups, indent=2))

def list_groups():
    return load_groups()

# --- files ---
def list_files(group: str):
    g = _upload_root() / group
    if not g.exists():
        return []
    return [f.name for f in g.iterdir() if f.is_file()]

def save_file(group, file_storage, chunk_size=None):
    """Stream an uploaded file to UPLOAD_FOLDER/<group>/<filename> and return the path."""
    if chunk_size is None:
        chunk_size = int(os.getenv("TD_CHUNK_SIZE", 8 * 1024 * 1024))  # default 8 MiB

    target_dir = _upload_root() / group
    target_dir.mkdir(parents=True, exist_ok=True)

    safe = secure_filename(file_storage.filename)
    dest = target_dir / safe

    # Python 3.6 safe streaming
    with open(dest, "wb") as out:
        while True:
            chunk = file_storage.stream.read(chunk_size)
            if not chunk:
                break
            out.write(chunk)

    return str(dest)
