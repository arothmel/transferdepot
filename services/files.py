import os
import json
import time
from datetime import datetime
from pathlib import Path
from flask import current_app
from werkzeug.utils import secure_filename

# --- helpers ---
def _groups_file_path() -> Path:
    return Path(current_app.config["GROUPS_FILE"])

def _upload_root() -> Path:
    return Path(current_app.config["UPLOAD_FOLDER"])


def _status_root() -> Path:
    return Path(current_app.config["STATUS_FOLDER"])


def _retention_seconds(group: str) -> int:
    overrides = current_app.config.get("RETENTION_OVERRIDES", {})
    default_days = int(current_app.config.get("RETENTION_DEFAULT_DAYS", 28))
    days = overrides.get(group, default_days)
    if days is None:
        return 0
    try:
        days = int(days)
    except (TypeError, ValueError):
        days = default_days
    return max(days, 0) * 24 * 60 * 60


def _heartbeat_retention_seconds(group: str) -> int:
    base = int(current_app.config.get("HEARTBEAT_RETENTION", 180))
    return max(base, _retention_seconds(group))


def _now_ts() -> float:
    return time.time()


def _iso_utc(ts: float) -> str:
    return datetime.utcfromtimestamp(ts).strftime("%Y-%m-%dT%H:%M:%SZ")


def _format_bytes(value: int) -> str:
    return f"{value:,} bytes"


def _format_ago(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)}s"
    minutes, secs = divmod(int(seconds), 60)
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins}m"


def cleanup_expired_files(group: str):
    retention = _retention_seconds(group)
    if retention <= 0:
        return

    now = _now_ts()
    target_dir = _upload_root() / group
    status_dir = _status_root() / group

    if target_dir.exists():
        for path in list(target_dir.iterdir()):
            if not path.is_file():
                continue
            try:
                age = now - path.stat().st_mtime
            except OSError:
                continue
            if age > retention:
                try:
                    path.unlink()
                except OSError:
                    continue
                status_path = status_dir / f"{path.name}.json"
                if status_path.exists():
                    try:
                        status_path.unlink()
                    except OSError:
                        pass


class UploadHeartbeat:
    def __init__(self, group: str, filename: str):
        self.group = group
        self.filename = filename
        cfg = current_app.config
        self.interval = int(cfg.get("HEARTBEAT_INTERVAL", 30))
        self.status_dir = _status_root() / group
        self.status_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.status_dir / f"{filename}.json"
        self.last_write = 0.0
        self.data = {
            "group": group,
            "file": filename,
            "status": "pending",
            "bytes_written": 0,
            "total_bytes": None,
            "started_ts": None,
            "updated_ts": None,
        }

    def start(self, total_bytes=None):
        ts = _now_ts()
        self.data.update({
            "status": "in_progress",
            "bytes_written": 0,
            "total_bytes": total_bytes,
            "started_ts": ts,
            "updated_ts": ts,
        })
        self._write(force=True)

    def pulse(self, bytes_written_delta: int):
        self.data["bytes_written"] += bytes_written_delta
        ts = _now_ts()
        self.data["updated_ts"] = ts
        self._write(force=False)

    def complete(self):
        ts = _now_ts()
        self.data.update({
            "status": "completed",
            "completed_ts": ts,
            "updated_ts": ts,
        })
        self._write(force=True)

    def fail(self, error_message: str):
        ts = _now_ts()
        self.data.update({
            "status": "failed",
            "error": error_message,
            "updated_ts": ts,
        })
        self._write(force=True)

    def _write(self, force: bool):
        now = self.data.get("updated_ts", _now_ts())
        if not force and (now - self.last_write) < self.interval:
            return
        tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        payload = dict(self.data, updated_iso=_iso_utc(self.data["updated_ts"]))
        tmp_path.write_text(json.dumps(payload))
        tmp_path.replace(self.path)
        self.last_write = now

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
    cleanup_expired_files(group)
    g = _upload_root() / group
    if not g.exists():
        return []
    return [f.name for f in g.iterdir() if f.is_file()]

def save_file(group, file_storage, chunk_size=None):
    """Stream an uploaded file to UPLOAD_FOLDER/<group>/<filename> and return the path."""
    if chunk_size is None:
        chunk_size = int(current_app.config.get("UPLOAD_CHUNK_SIZE", 8 * 1024 * 1024))

    target_dir = _upload_root() / group
    target_dir.mkdir(parents=True, exist_ok=True)

    safe = secure_filename(file_storage.filename)
    dest = target_dir / safe
    temp_dest = dest.with_suffix(dest.suffix + ".part")

    heartbeat = UploadHeartbeat(group, safe)
    total_bytes = getattr(file_storage, "content_length", None)
    heartbeat.start(total_bytes=total_bytes)

    # Python 3.6 safe streaming
    bytes_written = 0
    try:
        with open(temp_dest, "wb") as out:
            while True:
                chunk = file_storage.stream.read(chunk_size)
                if not chunk:
                    break
                out.write(chunk)
                bytes_written += len(chunk)
                heartbeat.pulse(len(chunk))

        os.replace(temp_dest, dest)
        heartbeat.complete()
    except Exception as exc:
        heartbeat.fail(str(exc))
        if temp_dest.exists():
            temp_dest.unlink()
        raise

    return str(dest)


def list_active_uploads(group: str):
    cleanup_expired_files(group)
    root = _status_root() / group
    if not root.exists():
        return []

    now = _now_ts()
    retention = _heartbeat_retention_seconds(group)
    statuses = []

    for path in sorted(root.glob("*.json")):
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        updated_ts = data.get("updated_ts") or data.get("updated_ts".upper())
        if updated_ts is None:
            updated_ts = now
        age = now - updated_ts

        status = data.get("status", "unknown")
        file_name = data.get("file", path.stem)
        file_path = _upload_root() / group / file_name

        if status == "completed" and age > retention:
            try:
                path.unlink()
            except OSError:
                pass
            continue

        if status != "in_progress" and not file_path.exists() and age > retention:
            try:
                path.unlink()
            except OSError:
                pass
            continue

        total = data.get("total_bytes") or 0
        written = data.get("bytes_written", 0)
        percent = None
        if total:
            percent = int((written / float(total)) * 100)

        started_ts = data.get("started_ts")
        completed_ts = data.get("completed_ts")
        heartbeat_interval = int(current_app.config.get("HEARTBEAT_INTERVAL", 30)) or 1
        duration_display = None
        if started_ts and completed_ts:
            duration = max(0, completed_ts - started_ts)
            rounded = max(
                heartbeat_interval,
                int(round(duration / heartbeat_interval)) * heartbeat_interval,
            )
            duration_display = _format_ago(rounded)
        elif started_ts and status == "in_progress":
            elapsed = max(0, now - started_ts)
            rounded = max(
                heartbeat_interval,
                int(round(elapsed / heartbeat_interval)) * heartbeat_interval,
            )
            duration_display = _format_ago(rounded)

        completed_ts = data.get("completed_ts")
        completed_iso = _iso_utc(completed_ts) if completed_ts else None

        statuses.append({
            "file": file_name,
            "status": status,
            "bytes_written": written,
            "total_bytes": total,
            "percent": percent,
            "updated_ts": updated_ts,
            "updated_iso": data.get("updated_iso", _iso_utc(updated_ts)),
            "age_display": _format_ago(age),
            "bytes_display": _format_bytes(written),
            "total_display": _format_bytes(total) if total else None,
            "completed_iso": completed_iso,
            "started_ts": started_ts,
            "started_iso": _iso_utc(started_ts) if started_ts else None,
            "duration_display": duration_display,
            "error": data.get("error"),
        })

    return statuses


def clear_completed_statuses(group: str) -> int:
    root = _status_root() / group
    if not root.exists():
        return 0

    cleared = 0
    for path in root.glob("*.json"):
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if data.get("status") == "in_progress":
            continue
        try:
            path.unlink()
            cleared += 1
        except OSError:
            continue
    return cleared
