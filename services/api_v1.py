from flask import Blueprint, request, current_app, jsonify, send_from_directory
import os
import datetime

api_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")

# Health check
@api_bp.route("/healthz", methods=["GET"])
def healthz():
    return jsonify(ok=True), 200

# ---- Streamed upload handler ----
def handle_stream_upload(group):
    # Validate group (in real use, load from groups.json)
    # For now, allow all group names
    f = request.files.get("file")
    filename = f.filename if f and getattr(f, "filename", None) else "upload.bin"
    safe = os.path.basename(filename)

    dest_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], group)
    os.makedirs(dest_dir, exist_ok=True)

    tmp = os.path.join(dest_dir, f"{safe}.part")
    final = os.path.join(dest_dir, safe)

    chunk = 1024 * 1024  # 1 MB
    stream = getattr(f, "stream", f) if f else request.stream

    with open(tmp, "wb") as out:
        while True:
            buf = stream.read(chunk)
            if not buf:
                break
            out.write(buf)

    os.replace(tmp, final)
    return jsonify(ok=True, group=group, file=safe), 200

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

    return send_from_directory(folder, safe, as_attachment=True)
