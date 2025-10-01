from flask import Blueprint, render_template, request, redirect, url_for, current_app
from pathlib import Path
from services.files import save_file

ui_bp = Blueprint("ui", __name__)

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
    return render_template("upload.html", group=group, files=files)
