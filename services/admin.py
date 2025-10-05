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
)

from .files import list_active_uploads, list_files, list_groups, list_recent_transfers


ONCALL_DIR_CANDIDATES = [
    Path("/home/tux/transferdepot-001/artifacts/ONCALL"),
    Path("/home/tux/sh1re/transferdepot-001/artifacts/ONCALL"),
]

DEFAULT_ONCALL_DIR = str(ONCALL_DIR_CANDIDATES[0])
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
        if isinstance(raw_groups, dict):
            groups = sorted(raw_groups.keys())
        else:
            for entry in raw_groups or []:
                if isinstance(entry, str):
                    groups.append(entry)
                elif isinstance(entry, dict):
                    name = entry.get("name") or entry.get("group")
                    if name:
                        groups.append(name)
        groups = sorted(set(groups))
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
    """Return the first existing on-call PDF path, considering fallbacks."""

    candidates = []
    if oncall_dir:
        candidates.append(Path(oncall_dir))

    for fallback in ONCALL_DIR_CANDIDATES:
        if not oncall_dir or Path(oncall_dir) != fallback:
            candidates.append(fallback)

    for base in candidates:
        target = base / oncall_file
        if target.is_file():
            return target

    return None
