"""Routes xác thực: đăng ký, đăng nhập, đăng xuất, thông tin user."""

import sqlite3

from flask import Blueprint, jsonify, request, session

from routes.database import get_db, hash_password

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    email = (data.get("email") or "").strip() or None
    fullname = (data.get("fullname") or "").strip() or None
    if not username or not password:
        return jsonify({"error": "Vui lòng nhập tên đăng nhập và mật khẩu"}), 400
    if len(username) < 3:
        return jsonify({"error": "Tên đăng nhập phải ít nhất 3 ký tự"}), 400
    if len(password) < 6:
        return jsonify({"error": "Mật khẩu phải ít nhất 6 ký tự"}), 400
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO users (username,password,email,fullname) VALUES (?,?,?,?)",
                (username, hash_password(password), email, fullname),
            )
        return jsonify({"success": True, "message": "Đăng ký thành công!"})
    except sqlite3.IntegrityError:
        return jsonify({"error": "Tên đăng nhập hoặc email đã tồn tại"}), 409


@auth_bp.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    with get_db() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, hash_password(password)),
        ).fetchone()
    if not user:
        return jsonify({"error": "Sai tên đăng nhập hoặc mật khẩu"}), 401
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["fullname"] = user["fullname"] or user["username"]
    # Mỗi lần đăng nhập mới bắt buộc thiết lập lại API key AI
    session.pop("ai_api_key", None)
    session["ai_provider"] = None
    session["ai_model"] = None
    sk = f"user_{user['id']}_chat"
    with get_db() as conn:
        if not conn.execute(
            "SELECT id FROM chat_sessions WHERE user_id=? AND session_key=?",
            (user["id"], sk),
        ).fetchone():
            conn.execute(
                "INSERT INTO chat_sessions (user_id,session_key) VALUES (?,?)", (user["id"], sk)
            )
    return jsonify({
        "success": True,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "fullname": user["fullname"] or user["username"],
            "role": user["role"],
        },
    })


@auth_bp.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})


@auth_bp.route("/api/me")
def me():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    return jsonify({
        "id": session["user_id"],
        "username": session["username"],
        "fullname": session["fullname"],
        "bio": user["bio"] if user else "",
        "role": user["role"] if user else "student",
    })


@auth_bp.route("/api/users", methods=["GET"])
def get_users():
    if "user_id" not in session:
        return jsonify({"error": "Chưa đăng nhập"}), 401
    with get_db() as conn:
        users = conn.execute(
            "SELECT id, username, fullname, role, created_at FROM users ORDER BY created_at DESC"
        ).fetchall()
    return jsonify([dict(u) for u in users])
