"""Routes chat AI và quản lý session."""

import json

from flask import Blueprint, jsonify, request, send_file, send_from_directory, session
from werkzeug.utils import secure_filename

from routes.chat_processor import process_message
from routes.config import DEFAULT_GROQ_API_KEY, DEFAULT_MODEL, DEFAULT_PROVIDER
from routes.database import get_db
from routes.files import get_file_category, read_file_content
from routes.history import _histories, clear_history

import os

chat_bp = Blueprint("chat", __name__)

UPLOAD_FOLDER = "uploads"


@chat_bp.route("/")
def index():
    return send_from_directory("static", "index.html")


@chat_bp.route("/chat", methods=["POST"])
def chat():
    if "user_id" not in session:
        return jsonify({"error": "Chưa đăng nhập"}), 401
    session_key = f"user_{session['user_id']}_chat"
    file_content = None
    image_data = None

    if request.content_type and "application/json" in request.content_type:
        data = request.get_json()
        message = data.get("message", "").strip()
    else:
        message = request.form.get("message", "").strip()
        if "file" in request.files:
            file = request.files["file"]
            if file and file.filename:
                filename = secure_filename(file.filename)
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                file_content = read_file_content(filepath, filename)
                if file_content and not isinstance(file_content, str):
                    file_content = str(file_content)
                cat, ext = get_file_category(filename)
                size = os.path.getsize(filepath)
                with get_db() as conn:
                    conn.execute(
                        "INSERT INTO uploads (user_id,filename,orig_name,file_type,file_size) VALUES (?,?,?,?,?)",
                        (session["user_id"], filename, file.filename, cat, size),
                    )
                if cat == "image":
                    image_data = True

    if not message and not file_content:
        return jsonify({"error": "Empty message"}), 400
    if not message:
        message = "Hãy phân tích và mô tả chi tiết nội dung file/ảnh này cho mình"

    api_key = session.get("ai_api_key")
    if not api_key:
        return jsonify({"error": "Vui lòng nhập API key trong cấu hình AI"}), 400

    ai_cfg = {
        "provider": session.get("ai_provider", DEFAULT_PROVIDER),
        "model": session.get("ai_model", DEFAULT_MODEL),
        "api_key": api_key,
    }
    try:
        reply, files, youtube_data, code_outputs, html_files = process_message(
            message, session_key, file_content, ai_cfg, image_data
        )
        return jsonify({
            "reply": reply,
            "files": files,
            "youtube": youtube_data,
            "code_outputs": code_outputs,
            "html_files": html_files,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/clear", methods=["POST"])
def clear():
    if "user_id" not in session:
        return jsonify({"error": "Chưa đăng nhập"}), 401
    clear_history(f"user_{session['user_id']}_chat")
    return jsonify({"status": "ok"})


@chat_bp.route("/download/<filename>")
def download(filename):
    path = os.path.join("outputs", filename)
    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    return jsonify({"error": "File not found"}), 404


@chat_bp.route("/view/<filename>")
def view_file(filename):
    path = os.path.join("outputs", filename)
    if os.path.exists(path):
        return send_file(path)
    return jsonify({"error": "File not found"}), 404


@chat_bp.route("/uploads/<filename>")
def serve_upload(filename):
    return send_from_directory("uploads", filename)


# ── Chat session management ──────────────────────────

@chat_bp.route("/api/chat-sessions", methods=["GET"])
def get_chat_sessions():
    if "user_id" not in session:
        return jsonify({"error": "Chưa đăng nhập"}), 401
    with get_db() as conn:
        sessions = conn.execute(
            "SELECT id, title, created_at, updated_at FROM ai_sessions WHERE user_id=? ORDER BY updated_at DESC LIMIT 20",
            (session["user_id"],),
        ).fetchall()
    return jsonify([dict(s) for s in sessions])


@chat_bp.route("/api/chat-sessions/<int:sess_id>", methods=["GET"])
def get_chat_session(sess_id):
    if "user_id" not in session:
        return jsonify({"error": "Chưa đăng nhập"}), 401
    with get_db() as conn:
        s = conn.execute(
            "SELECT * FROM ai_sessions WHERE id=? AND user_id=?",
            (sess_id, session["user_id"]),
        ).fetchone()
    if not s:
        return jsonify({"error": "Không tìm thấy"}), 404
    return jsonify({"id": s["id"], "title": s["title"], "messages": json.loads(s["messages"] or "[]")})


@chat_bp.route("/api/chat-sessions/new", methods=["POST"])
def new_chat_session():
    if "user_id" not in session:
        return jsonify({"error": "Chưa đăng nhập"}), 401
    sk = f"user_{session['user_id']}_chat"
    clear_history(sk)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO ai_sessions (user_id, messages) VALUES (?, ?)",
            (session["user_id"], "[]"),
        )
        new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    _histories[f"{sk}_session_id"] = new_id
    return jsonify({"success": True, "session_id": new_id})
