from flask import Flask
from services.api_v1 import api_bp

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "files"
# Allow uploads up to 1 GB (adjust as needed)
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024


app.register_blueprint(api_bp, url_prefix="/api/v1")
app.register_blueprint(ui_bp)



if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080)
