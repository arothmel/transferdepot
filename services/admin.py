import json
import time
from datetime import datetime
from pathlib import Path

from flask import Blueprint, jsonify, request, render_template, current_app

from .files import list_active_uploads, list_files

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
            }
        )

    return summaries


@admin_ui_bp.route("/health")
def admin_health_page():
    cfg = current_app.config
    upload_root = Path(cfg["UPLOAD_FOLDER"])
    status_root = Path(cfg["STATUS_FOLDER"])
    summaries = _group_summaries(upload_root)

    active_uploads = []
    for summary in summaries:
        statuses = list_active_uploads(summary["group"])
        for status in statuses:
            active_uploads.append({"group": summary["group"], **status})

    active_uploads.sort(key=lambda s: (s.get("status") != "in_progress", s.get("file")))

    return render_template(
        "admin/health.html",
        upload_root=str(upload_root),
        status_root=str(status_root),
        heartbeat_interval=cfg.get("HEARTBEAT_INTERVAL"),
        retention_default=cfg.get("RETENTION_DEFAULT_DAYS"),
        retention_overrides=cfg.get("RETENTION_OVERRIDES", {}),
        summaries=summaries,
        active_uploads=active_uploads,
        api_health_url="/api/v1/admin/healthz",
    )


@admin_ui_bp.route("/dev-api")
def admin_dev_api_page():
    base_url = request.host_url.rstrip("/")
    example_group = "TTCS"
    example_filename = "sample.bin"
    return render_template(
        "admin/dev_api.html",
        base_url=base_url,
        example_group=example_group,
        example_filename=example_filename,
    )


# Public helper retained for other modules/tests
def get_group_summaries(upload_path):
    return _group_summaries(Path(upload_path))
