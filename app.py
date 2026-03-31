
"""
DNS Bot - Main entry (fixed for Render deployment)
"""

import os
import sys
from flask import Flask, jsonify, session

# ─────────────────────────────────────────
# FIX IMPORT PATH (QUAN TRỌNG)
# ─────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

# ─────────────────────────────────────────
# IMPORT MODULES
# ─────────────────────────────────────────
from routes.database import init_db

# Blueprints
from routes.ai_config import ai_config_bp
from routes.auth import auth_bp
from routes.chat import chat_bp
from routes.group_chat import group_chat_bp
from routes.notes import notes_bp
from routes.snippets import snippets_bp
from routes.tasks import tasks_bp
from routes.utilities import utilities_bp

# ─────────────────────────────────────────
# FLASK APP
# ─────────────────────────────────────────
app = Flask(__name__)

# SECRET KEY (dùng ENV cho production)
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key_123")

# CONFIG
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["OUTPUT_FOLDER"] = "outputs"
app.config["MAX_CONTENT_LENGTH"] = 128 * 1024 * 1024

# ─────────────────────────────────────────
# CREATE FOLDERS
# ─────────────────────────────────────────
for d in ["uploads", "outputs", "static", "user_chats"]:
    os.makedirs(os.path.join(BASE_DIR, d), exist_ok=True)

# ─────────────────────────────────────────
# INIT DATABASE (SAFE)
# ─────────────────────────────────────────
@app.before_request
def ensure_db_initialized():
    if not hasattr(app, "_db_initialized"):
        try:
            init_db()
            app._db_initialized = True
            print("✅ Database initialized (lazy)")
        except Exception as e:
            print("❌ DB INIT ERROR:", e)

# ─────────────────────────────────────────
# REGISTER BLUEPRINTS
# ─────────────────────────────────────────

app.register_blueprint(auth_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(ai_config_bp)
app.register_blueprint(notes_bp)
app.register_blueprint(tasks_bp)
app.register_blueprint(snippets_bp)
app.register_blueprint(group_chat_bp)
app.register_blueprint(utilities_bp)
# ─────────────────────────────────────────
# FIX /api/me (KHÔNG CRASH)
# ─────────────────────────────────────────
@app.route("/api/me")
def api_me():
    try:
        user_id = session.get("user_id")

        if not user_id:
            return jsonify({"user": None}), 200

        return jsonify({
            "user": {
                "id": user_id
            }
        }), 200

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

# ─────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────
@app.route("/")
def home():
    return jsonify({
        "status": "ok",
        "message": "DNS Bot running"
    })

# ─────────────────────────────────────────
# RUN (LOCAL) / GUNICORN (PROD)
# ─────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

