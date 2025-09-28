import os
import logging
from flask import Flask
from services import api_bp, admin_bp, ui_bp   # assuming you also have ui_bp

app = Flask(__name__)

# Point to the correct upload folder (default: ./files)
app.config["UPLOAD_FOLDER"] = os.getenv(
    "TD_UPLOAD_FOLDER",
    os.path.join(os.path.dirname(__file__), "files")
)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Optional: enable debug-level logging
logging.basicConfig(level=logging.DEBUG)

# Register the blueprints -- clarity over cleverness
app.register_blueprint(admin_bp)
app.register_blueprint(ui_bp)
app.register_blueprint(api_bp, url_prefix="/api/v1")  # Note the prefix here

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
