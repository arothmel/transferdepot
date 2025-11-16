import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from flask import (
    Blueprint,
    jsonify,
    request,
    render_template,
    current_app,
    send_file,
    abort,
    make_response,
    url_for,
    redirect,
)

from .files import list_active_uploads, list_files, list_groups, list_recent_transfers
# Local, dependency-free helpers so we can run on RHEL8 without sh1retools
try:  # Prefer psutil if present, but fall back to lightweight probes
    import psutil  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    psutil = None


def get_system_stats():
    """Return a small system stats dict without external deps.

    Matches the rough shape expected by the admin/miniops template. Works with
    psutil when available; otherwise returns a minimal payload.
    """

    stats = {
        "cpu_percent": None,
        "memory_percent": None,
        "disk_percent": None,
        "load_avg": None,
        "boot_time": None,
    }

    if psutil:
        try:
            stats.update(
                cpu_percent=psutil.cpu_percent(interval=0.1),
                memory_percent=psutil.virtual_memory().percent,
            )
            try:
                stats["disk_percent"] = psutil.disk_usage("/").percent
            except Exception:
                pass
            try:
                stats["load_avg"] = os.getloadavg()[0]
            except Exception:
                pass
            try:
                stats["boot_time"] = psutil.boot_time()
            except Exception:
                pass
            return stats
        except Exception:
            # fall back to basic stats below
            pass

    # Minimal fallback using stdlib only
    try:
        stats["load_avg"] = os.getloadavg()[0]
    except Exception:
        pass
    return stats


def is_valid_pdf(path: str) -> bool:
    """Lightweight PDF validation.

    We only require basic structure checks so we can run offline without qpdf.
    """

    try:
        with open(path, "rb") as f:
            header = f.read(5)
            if header != b"%PDF-":
                return False
            f.seek(-6, os.SEEK_END)
            trailer = f.read().strip()
            return trailer.endswith(b"%%EOF")
    except Exception:
        return False


DEFAULT_ONCALL_DIR = "/home/tux/sh1re/transferdepot-001/artifacts/ONCALL"
DEFAULT_ONCALL_FILE = "oncall_board.pdf"

admin_api_bp = Blueprint("admin_api", __name__, url_prefix="/api/v1/admin")
admin_ui_bp = Blueprint("admin_ui", __name__, url_prefix="/admin")


@admin_api_bp.route("/healthz")
def admin_healthz():
    return jsonify(ok=True, time=time.strftime("%Y-%m-%d %H:%M:%S"))


@admin_api_bp.route("/telemetry", methods=["GET"])
def telemetry():
    try:
        with open("/run/transferdepot/bwatch.json") as f:
            data = json.load(f)

        fields = request.args.get("fields")
        if fields:
            keys = [k.strip() for k in fields.split(",") if k.strip()]
            data = {k: v for k, v in data.items() if k in keys}

        return jsonify(ok=True, **data)
    except Exception as exc:
        return (
            jsonify(
                ok=False,
                error=str(exc),
                time=time.strftime("%Y-%m-%d %H:%M:%S"),
            ),
            500,
        )


def _group_summaries(upload_root: Path):
    summaries = []
    if not upload_root.exists():
        return summaries

    for group_path in sorted(p for p in upload_root.iterdir() if p.is_dir()):
        files = list_files(group_path.name)
        latest_ts = None
        latest_name = None
        for name in files:
            full = group_path / name
            try:
                mtime = full.stat().st_mtime
            except OSError:
                continue
            if latest_ts is None or mtime > latest_ts:
                latest_ts = mtime
                latest_name = name

        summaries.append(
            {
                "group": group_path.name,
                "file_count": len(files),
                "latest_file": latest_name,
                "last_updated": datetime.fromtimestamp(latest_ts).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                if latest_ts
                else "-",
                "last_updated_ts": latest_ts,
            }
        )

    summaries.sort(key=lambda entry: entry.get("last_updated_ts") or 0, reverse=True)
    for summary in summaries:
        summary.pop("last_updated_ts", None)

    return summaries


def _normalize_groups(raw_groups):
    groups = []
    if isinstance(raw_groups, dict):
        groups.extend(raw_groups.keys())
    elif isinstance(raw_groups, list):
        for entry in raw_groups:
            if isinstance(entry, str):
                groups.append(entry)
            elif isinstance(entry, dict):
                name = entry.get("name") or entry.get("group")
                if name:
                    groups.append(name)

    normalized = []
    for name in groups:
        if not name:
            continue
        normalized_name = str(name).strip().upper()
        if normalized_name:
            normalized.append(normalized_name)

    # keep sorted unique list
    return sorted(set(normalized))


@admin_ui_bp.route("/health")
def admin_health_page():
    cfg = current_app.config
    upload_root = Path(cfg["UPLOAD_FOLDER"])
    status_root = Path(cfg["STATUS_FOLDER"])
    summaries = _group_summaries(upload_root)

    active_uploads = []
    cutoff = time.time() - (24 * 60 * 60)
    for summary in summaries:
        statuses = list_active_uploads(summary["group"])
        for status in statuses:
            updated_ts = status.get("updated_ts") or 0
            if updated_ts >= cutoff:
                active_uploads.append({"group": summary["group"], **status})

    active_uploads.sort(key=lambda s: s.get("updated_ts") or 0, reverse=True)

    transfers = list_recent_transfers(hours=24)

    oncall_dir = cfg.get("ONCALL_DIR") or os.getenv("TD_ONCALL_DIR") or DEFAULT_ONCALL_DIR
    oncall_file = cfg.get("ONCALL_FILE") or os.getenv("TD_ONCALL_FILE") or DEFAULT_ONCALL_FILE
    oncall_path = _resolve_oncall_path(oncall_dir, oncall_file)
    oncall_url = None
    if oncall_path is not None:
        oncall_url = url_for("admin_ui.admin_oncall_document", filename=oncall_file)

    return render_template(
        "admin/health.html",
        upload_root=str(upload_root),
        status_root=str(status_root),
        heartbeat_interval=cfg.get("HEARTBEAT_INTERVAL"),
        retention_default=cfg.get("RETENTION_DEFAULT_DAYS"),
        retention_overrides=cfg.get("RETENTION_OVERRIDES", {}),
        summaries=summaries,
        active_uploads=active_uploads,
        transfers=transfers,
        oncall_url=oncall_url,
        api_health_url="/api/v1/admin/healthz",
    )


@admin_ui_bp.route("/dev-api")
def admin_dev_api_page():
    base_url = request.host_url.rstrip("/")
    groups = []
    groups_error = None
    try:
        raw_groups = list_groups()
        groups = _normalize_groups(raw_groups)
    except Exception as exc:
        groups_error = str(exc)

    example_group = groups[0] if groups else "TTCS"
    example_filename = "sample.bin"
    return render_template(
        "admin/dev_api.html",
        base_url=base_url,
        example_group=example_group,
        groups=groups,
        groups_error=groups_error,
        example_filename=example_filename,
    )


@admin_ui_bp.route("/groups_admin", methods=["GET", "POST"])
def groups_admin():
    groups = []
    error = None

    try:
        raw_groups = list_groups()
        groups = _normalize_groups(raw_groups)
    except Exception as exc:
        error = str(exc)
        groups = []

    if request.method == "POST":
        new_group = request.form.get("group_name", "").strip().upper()
        if new_group:
            groups_to_write = list(groups)
            if new_group not in groups_to_write:
                groups_to_write.append(new_group)
            target = Path(current_app.config["GROUPS_FILE"])
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(sorted(groups_to_write), indent=2))
                return redirect(url_for("admin_ui.groups_admin"))
            except Exception as exc:
                error = str(exc)

    groups_file = str(Path(current_app.config["GROUPS_FILE"]))

    return render_template(
        "admin/groups_admin.html",
        groups=groups,
        groups_file=groups_file,
        error=error,
    )


@admin_ui_bp.route("/miniops")
def admin_miniops():
    stats = {}
    error = None
    try:
        stats = get_system_stats()
    except Exception as exc:
        error = str(exc)

    return render_template("admin/miniops.html", stats=stats, error=error)


@admin_ui_bp.route("/oncall")
def admin_oncall_status():
    cfg = current_app.config
    oncall_dir = cfg.get("ONCALL_DIR") or os.getenv("TD_ONCALL_DIR") or DEFAULT_ONCALL_DIR
    oncall_file = cfg.get("ONCALL_FILE") or os.getenv("TD_ONCALL_FILE") or DEFAULT_ONCALL_FILE

    target = _resolve_oncall_path(oncall_dir, oncall_file)
    status = "missing"
    pdf_url = None
    error = None
    last_updated_iso = None
    is_stale = False

    if target:
        try:
            stat = target.stat()
            last_updated_iso = datetime.fromtimestamp(stat.st_mtime).isoformat()
            is_stale = (time.time() - stat.st_mtime) > (14 * 24 * 60 * 60)

            if is_valid_pdf(str(target)):
                status = "valid"
                pdf_url = url_for("admin_ui.admin_oncall_document", filename=oncall_file)
                if is_stale:
                    status = "stale"
            else:
                status = "invalid"
        except Exception as exc:
            status = "error"
            error = str(exc)

    return render_template(
        "admin/oncall.html",
        status=status,
        pdf_path=str(target) if target else None,
        pdf_url=pdf_url,
        oncall_file=oncall_file,
        configured_oncall_dir=oncall_dir,
        last_updated_iso=last_updated_iso,
        is_stale=is_stale,
        error=error,
    )


@admin_ui_bp.route("/oncall/<path:filename>")
def admin_oncall_document(filename):
    cfg = current_app.config
    oncall_dir = cfg.get("ONCALL_DIR") or os.getenv("TD_ONCALL_DIR") or DEFAULT_ONCALL_DIR
    oncall_file = cfg.get("ONCALL_FILE") or os.getenv("TD_ONCALL_FILE") or DEFAULT_ONCALL_FILE

    if filename != oncall_file:
        abort(404)

    target = _resolve_oncall_path(oncall_dir, oncall_file)
    if target is None:
        abort(404)

    response = make_response(
        send_file(str(target), mimetype="application/pdf", as_attachment=False)
    )
    response.headers["Content-Disposition"] = f'inline; filename="{oncall_file}"'
    response.headers["Cache-Control"] = "no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


# Public helper retained for other modules/tests
def get_group_summaries(upload_path):
    return _group_summaries(Path(upload_path))


def _resolve_oncall_path(oncall_dir: Optional[str], oncall_file: str) -> Optional[Path]:
    """Return the on-call PDF path if it exists, otherwise None.

    Only a single configured path is considered; no fallbacks.
    """

    if not oncall_dir:
        return None

    target = Path(oncall_dir) / oncall_file
    return target if target.is_file() else None
