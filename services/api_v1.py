from flask import Blueprint, request, current_app, jsonify, send_from_directory
import os
import datetime
from services.files import save_file, list_recent_transfers


def _parse_time_arg(value):
    """Return a UNIX timestamp for the provided query arg or None if invalid."""
    if not value:
        return None

    value = value.strip()
    if not value:
        return None

    try:
        return float(value)
    except ValueError:
        pass

    cleaned = value
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"

    try:
        dt = datetime.datetime.fromisoformat(cleaned)
    except ValueError:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)

    return dt.timestamp()

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

    since_raw = request.args.get("since")
    until_raw = request.args.get("until")
    limit = request.args.get("limit", type=int)

    since_ts = _parse_time_arg(since_raw)
    until_ts = _parse_time_arg(until_raw)

    files = []
    for name in os.listdir(folder):
        full = os.path.join(folder, name)
        if os.path.isfile(full):
            st = os.stat(full)
            mtime = st.st_mtime

            if since_ts is not None and mtime < since_ts:
                continue
            if until_ts is not None and mtime > until_ts:
                continue

            files.append({
                "name": name,
                "size": st.st_size,
                "mtime": datetime.datetime.fromtimestamp(mtime, datetime.timezone.utc).isoformat(),
                "url": f"/api/v1/files/{group}/{name}",
                "_mtime": mtime,
            })

    files.sort(key=lambda entry: entry.get("_mtime", 0), reverse=True)

    if limit is not None and limit >= 0:
        files = files[:limit]

    for entry in files:
        entry.pop("_mtime", None)

    response = {
        "group": group,
        "files": files,
        "count": len(files),
    }

    applied_filters = {}
    if since_raw:
        applied_filters["since"] = since_raw
    if until_raw:
        applied_filters["until"] = until_raw
    if limit is not None:
        applied_filters["limit"] = limit
    if applied_filters:
        response["filters"] = applied_filters

    return jsonify(response)

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
@api_bp.route("/admin/transfers", methods=["GET"])
def admin_transfers():
    hours = request.args.get("hours", default=24, type=float)
    hours = max(hours, 0) if hours is not None else 24
    transfers = list_recent_transfers(hours=hours)
    return jsonify(count=len(transfers), hours=hours, transfers=transfers)
