import os
import logging
from flask import Flask
from services import api_bp, admin_bp, ui_bp


DEFAULT_GROUPS_FILE = "/home/tux/sh1re/transferdepot-001/groups.json"
DEFAULT_UPLOAD_FOLDER = "/home/tux/sh1re/transferdepot-001/files"
DEFAULT_CHUNK_SIZE = 8 * 1024 * 1024

app = Flask(__name__)

app.config.from_mapping(
    GROUPS_FILE=os.getenv("TD_GROUPS_FILE", DEFAULT_GROUPS_FILE),
    UPLOAD_FOLDER=os.getenv("TD_UPLOAD_FOLDER", DEFAULT_UPLOAD_FOLDER),
    UPLOAD_CHUNK_SIZE=int(os.getenv("TD_CHUNK_SIZE", DEFAULT_CHUNK_SIZE)),
)

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

logging.basicConfig(level=logging.DEBUG)
app.logger.debug(
    "Config loaded", extra={
        "upload_folder": app.config["UPLOAD_FOLDER"],
        "groups_file": app.config["GROUPS_FILE"],
        "chunk_size": app.config["UPLOAD_CHUNK_SIZE"],
    }
)

app.register_blueprint(admin_bp)
app.register_blueprint(ui_bp)
app.register_blueprint(api_bp, url_prefix="/api/v1")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
