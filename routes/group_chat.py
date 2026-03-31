"""Routes chat nhóm (group messages)."""

from flask import Blueprint, jsonify, request, session

from routes.database import get_db

group_chat_bp = Blueprint("group_chat", __name__)


@group_chat_bp.route("/api/group-messages", methods=["GET"])
def get_group_messages():
    if "user_id" not in session:
        return jsonify({"error": "Chưa đăng nhập"}), 401
    since = request.args.get("since", 0)
    with get_db() as conn:
        msgs = conn.execute(
            "SELECT * FROM group_messages WHERE id > ? ORDER BY created_at ASC LIMIT 100",
            (since,),
        ).fetchall()
    return jsonify([dict(m) for m in msgs])


@group_chat_bp.route("/api/group-messages", methods=["POST"])
def send_group_message():
    if "user_id" not in session:
        return jsonify({"error": "Chưa đăng nhập"}), 401
    data = request.get_json()
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"error": "Nội dung trống"}), 400
    with get_db() as conn:
        conn.execute(
            "INSERT INTO group_messages (user_id, username, fullname, content) VALUES (?,?,?,?)",
            (session["user_id"], session["username"], session["fullname"], content),
        )
        msg_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        msg = conn.execute("SELECT * FROM group_messages WHERE id=?", (msg_id,)).fetchone()
    return jsonify(dict(msg))
