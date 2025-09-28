import os
import json
from pathlib import Path
from werkzeug.utils import secure_filename

# If env not set, use groups.json in current dir
GROUPS_FILE = os.getenv("TD_GROUPS_FILE", "groups.json")

# Root folder where uploaded files are stored
UPLOAD_ROOT = os.getenv("TD_UPLOAD_FOLDER", "files")

def load_groups():
    """Read groups.json and return a list of groups."""
    try:
        return json.loads(Path(GROUPS_FILE).read_text("utf-8"))
    except Exception:
        # Fallback if file missing or invalid
        return ["TTCS", "MDA", "RS2", "ODMP", "PAV"]

def save_groups(groups):
    """Write a new list of groups to groups.json."""
    Path(GROUPS_FILE).write_text(json.dumps(groups, indent=2))

def list_groups():
    """Return the list of groups (used by API routes)."""
    return load_groups()

def list_files(group):
    """Return list of files in a given group directory."""
    group_path = Path(UPLOAD_ROOT) / group
    if not group_path.exists():
        return []
    return [f.name for f in group_path.iterdir() if f.is_file()]

def save_file(group, file_storage):
    """Save an uploaded file into UPLOAD_ROOT/<group>/ and return the path."""
    group_path = Path(UPLOAD_ROOT) / group
    group_path.mkdir(parents=True, exist_ok=True)

    safe = secure_filename(file_storage.filename)
    dest = group_path / safe
    file_storage.save(str(dest))

    return str(dest)
