import os
import logging
from flask import Flask
from services import api_bp, admin_bp, ui_bp

app = Flask(__name__)

# Groups file (leave this as-is, tested)
app.config["GROUPS_FILE"] = "/tux/home/transferdepot-001/config/groups.json"

# Upload folder (only one definition)
td_upload_folder = os.getenv("TD_UPLOAD_FOLDER", "/home/tux/transferdepot-001/files")
app.config["UPLOAD_FOLDER"] = td_upload_folder
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Debug log
logging.basicConfig(level=logging.DEBUG)
app.logger.debug(f"UPLOAD_FOLDER set to: {app.config['UPLOAD_FOLDER']}")

# Register the blueprints
app.register_blueprint(admin_bp)
app.register_blueprint(ui_bp)
app.register_blueprint(api_bp, url_prefix="/api/v1")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
