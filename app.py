import os
import logging
from flask import Flask
from services import api_bp, admin_api_bp, admin_ui_bp, ui_bp


DEFAULT_GROUPS_FILE = "/home/tux/sh1re/transferdepot-001/groups.json"
DEFAULT_UPLOAD_FOLDER = "/home/tux/sh1re/transferdepot-001/files"
DEFAULT_CHUNK_SIZE = 8 * 1024 * 1024
DEFAULT_STATUS_FOLDER = os.path.join(os.path.dirname(__file__), "run", "status")
DEFAULT_HEARTBEAT_INTERVAL = 30  # seconds
DEFAULT_HEARTBEAT_RETENTION = 180  # seconds
DEFAULT_RETENTION_DEFAULT_DAYS = 28
DEFAULT_ONCALL_DIR = os.path.join(
    os.path.dirname(DEFAULT_UPLOAD_FOLDER), "artifacts", "ONCALL"
)
DEFAULT_ONCALL_FILE = "oncall_board.pdf"


def _parse_retention_overrides(raw: str):
    overrides = {}
    if not raw:
        return overrides
    for part in raw.split(","):
        piece = part.strip()
        if not piece:
            continue
        if ":" not in piece:
            continue
        key, value = piece.split(":", 1)
        key = key.strip()
        try:
            overrides[key] = int(value.strip())
        except ValueError:
            continue
    return overrides

app = Flask(__name__)

app.config.from_mapping(
    GROUPS_FILE=os.getenv("TD_GROUPS_FILE", DEFAULT_GROUPS_FILE),
    UPLOAD_FOLDER=os.getenv("TD_UPLOAD_FOLDER", DEFAULT_UPLOAD_FOLDER),
    UPLOAD_CHUNK_SIZE=int(os.getenv("TD_CHUNK_SIZE", DEFAULT_CHUNK_SIZE)),
    STATUS_FOLDER=os.getenv("TD_STATUS_FOLDER", DEFAULT_STATUS_FOLDER),
    HEARTBEAT_INTERVAL=int(os.getenv("TD_HEARTBEAT_INTERVAL", DEFAULT_HEARTBEAT_INTERVAL)),
    HEARTBEAT_RETENTION=int(os.getenv("TD_HEARTBEAT_RETENTION", DEFAULT_HEARTBEAT_RETENTION)),
    RETENTION_DEFAULT_DAYS=int(os.getenv("TD_RETENTION_DEFAULT_DAYS", DEFAULT_RETENTION_DEFAULT_DAYS)),
    ONCALL_DIR=os.getenv("TD_ONCALL_DIR", DEFAULT_ONCALL_DIR),
    ONCALL_FILE=os.getenv("TD_ONCALL_FILE", DEFAULT_ONCALL_FILE),
)

app.config["RETENTION_OVERRIDES"] = _parse_retention_overrides(
    os.getenv("TD_RETENTION_OVERRIDES", "")
)

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["STATUS_FOLDER"], exist_ok=True)

logging.basicConfig(level=logging.DEBUG)
app.logger.debug(
    "Config loaded", extra={
        "upload_folder": app.config["UPLOAD_FOLDER"],
        "groups_file": app.config["GROUPS_FILE"],
        "chunk_size": app.config["UPLOAD_CHUNK_SIZE"],
        "status_folder": app.config["STATUS_FOLDER"],
        "heartbeat_interval": app.config["HEARTBEAT_INTERVAL"],
        "retention_default_days": app.config["RETENTION_DEFAULT_DAYS"],
        "retention_overrides": app.config["RETENTION_OVERRIDES"],
        "oncall_dir": app.config["ONCALL_DIR"],
        "oncall_file": app.config["ONCALL_FILE"],
    }
)

app.register_blueprint(admin_ui_bp)
app.register_blueprint(admin_api_bp)
app.register_blueprint(ui_bp)
app.register_blueprint(api_bp, url_prefix="/api/v1")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
