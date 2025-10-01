from flask import Blueprint, render_template, request, redirect, url_for, current_app
from pathlib import Path
from services.files import save_file, list_active_uploads, clear_completed_statuses

ui_bp = Blueprint("ui", __name__)


@ui_bp.route("/favicon.ico")
def favicon():
    """Browsers request /favicon.ico by default; respond empty to avoid group folder creation."""
    return "", 204


@ui_bp.route("/")
def index():
    """Landing page listing all available groups."""
    upload_root = Path(current_app.config["UPLOAD_FOLDER"])
    groups = [d.name for d in upload_root.iterdir() if d.is_dir()]
    return render_template("index.html", groups=groups)

@ui_bp.route("/<group>/", methods=["GET", "POST"])
def upload_page(group):
    folder = Path(current_app.config["UPLOAD_FOLDER"]) / group
    folder.mkdir(parents=True, exist_ok=True)

    if request.method == "POST":
        f = request.files.get("file")
        if f and f.filename:
            save_file(group, f)
            return redirect(url_for("ui.upload_page", group=group))

    files = [f.name for f in folder.iterdir() if f.is_file()]
    return render_template(
        "upload.html",
        group=group,
        files=files,
    )


@ui_bp.route("/<group>/status")
def group_status(group):
    statuses = list_active_uploads(group)
    interval = int(current_app.config.get("HEARTBEAT_INTERVAL", 30))
    has_active = any(s.get("status") == "in_progress" for s in statuses)
    refresh_seconds = interval if has_active else None
    cleared = request.args.get("cleared")
    if cleared is not None:
        try:
            cleared = int(cleared)
        except ValueError:
            cleared = None
    return render_template(
        "status.html",
        group=group,
        statuses=statuses,
        refresh_seconds=refresh_seconds,
        cleared=cleared,
    )


@ui_bp.route("/<group>/status/clear", methods=["POST"])
def clear_status(group):
    count = clear_completed_statuses(group)
    return redirect(url_for("ui.group_status", group=group, cleared=count))
