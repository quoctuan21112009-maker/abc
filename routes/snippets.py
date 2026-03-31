"""Routes quản lý code snippets."""

from flask import Blueprint, jsonify, request, session

from routes.database import get_db

snippets_bp = Blueprint("snippets", __name__)


@snippets_bp.route("/api/snippets", methods=["GET"])
def get_snippets():
    if "user_id" not in session:
        return jsonify({"error": "Chưa đăng nhập"}), 401
    with get_db() as conn:
        snips = conn.execute(
            "SELECT * FROM code_snippets WHERE user_id=? ORDER BY created_at DESC",
            (session["user_id"],),
        ).fetchall()
    return jsonify([dict(s) for s in snips])


@snippets_bp.route("/api/snippets", methods=["POST"])
def create_snippet():
    if "user_id" not in session:
        return jsonify({"error": "Chưa đăng nhập"}), 401
    data = request.get_json()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO code_snippets (user_id, title, code, language) VALUES (?,?,?,?)",
            (
                session["user_id"],
                data.get("title", "Code mới"),
                data.get("code", ""),
                data.get("language", "python"),
            ),
        )
        sid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        snip = conn.execute("SELECT * FROM code_snippets WHERE id=?", (sid,)).fetchone()
    return jsonify(dict(snip))


@snippets_bp.route("/api/snippets/<int:snip_id>", methods=["DELETE"])
def delete_snippet(snip_id):
    if "user_id" not in session:
        return jsonify({"error": "Chưa đăng nhập"}), 401
    with get_db() as conn:
        conn.execute(
            "DELETE FROM code_snippets WHERE id=? AND user_id=?", (snip_id, session["user_id"])
        )
    return jsonify({"success": True})
