from flask import Blueprint, jsonify, request
import os
import json
import time

admin_bp = Blueprint("api_v1_admin", __name__, url_prefix="/api/v1/admin")

# Health check route
@admin_bp.route("/healthz")
def admin_healthz():
    return jsonify(ok=True, time=time.strftime("%Y-%m-%d %H:%M:%S"))

# Telemetry dump route
@admin_bp.route("/telemetry", methods=["GET"])
def telemetry():
    try:
        with open("/run/transferdepot/bwatch.json") as f:
            data = json.load(f)

        # Optional: ?fields=foo,bar
        fields = request.args.get("fields")
        if fields:
            keys = fields.split(",")
            data = {k: v for k, v in data.items() if k in keys}

        return jsonify(ok=True, **data)
    except Exception as e:
        return jsonify(ok=False, error=str(e),
                       time=time.strftime("%Y-%m-%d %H:%M:%S")), 500

# Summaries (not hooked to route yet)
def get_group_summaries(upload_path):
    summaries = []
    try:
        for group in os.listdir(upload_path):
            group_path = os.path.join(upload_path, group)
            if os.path.isdir(group_path):
                files = [f for f in os.listdir(group_path)
                         if os.path.isfile(os.path.join(group_path, f))]

                latest_time = None
                for f in files:
                    full = os.path.join(group_path, f)
                    mtime = os.path.getmtime(full)
                    if latest_time is None or mtime > latest_time:
                        latest_time = mtime

                summaries.append({
                    "group": group,
                    "files": len(files),
                    "latest_file": max(files) if files else None,
                    "last_updated": time.strftime("%Y-%m-%d %H:%M:%S",
                                                  time.localtime(latest_time)) if latest_time else "-"
                })
    except Exception as e:
        print(f"Error reading group summaries: {e}")
    return summaries
