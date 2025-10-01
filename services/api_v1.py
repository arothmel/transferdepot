from flask import Blueprint, request, current_app, jsonify, send_from_directory
import os
import datetime
from services.files import save_file

api_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")

# Health check
@api_bp.route("/healthz", methods=["GET"])
def healthz():
    return jsonify(ok=True), 200

# ---- Streamed upload handler ----
def handle_stream_upload(group):
    file_storage = request.files.get("file")
    if not file_storage or not getattr(file_storage, "filename", None):
        return jsonify(error="missing file payload"), 400

    saved_path = save_file(group, file_storage)
    file_name = os.path.basename(saved_path)
    return jsonify(ok=True, group=group, file=file_name), 200

# Upload route
@api_bp.route("/upload/<group>", methods=["POST"])
def upload_v1(group):
    return handle_stream_upload(group)

# List files in a group
@api_bp.route("/files/<group>", methods=["GET"])
def list_files(group):
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], group)
    if not os.path.isdir(folder):
        return jsonify(error=f"invalid group '{group}'"), 400

    files = []
    for name in sorted(os.listdir(folder)):
        full = os.path.join(folder, name)
        if os.path.isfile(full):
            st = os.stat(full)
            files.append({
                "name": name,
                "size": st.st_size,
                "mtime": datetime.datetime.fromtimestamp(st.st_mtime).isoformat(),
                "url": f"/api/v1/files/{group}/{name}"
            })
    return jsonify(group=group, files=files)

# Download a file
@api_bp.route("/files/<group>/<path:fname>", methods=["GET"])
def download(group, fname):
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], group)
    safe = os.path.basename(fname)
    full = os.path.join(folder, safe)

    if not os.path.isfile(full):
        return jsonify(error=f"file '{fname}' not found"), 404

    # Serve inline so text files open in-browser; clients can force download via browser controls
    return send_from_directory(folder, safe, as_attachment=False)
