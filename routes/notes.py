"""Routes quản lý ghi chú (notes)."""

from flask import Blueprint, jsonify, request, session

from routes.database import get_db

notes_bp = Blueprint("notes", __name__)


@notes_bp.route("/api/notes", methods=["GET"])
def get_notes():
    if "user_id" not in session:
        return jsonify({"error": "Chưa đăng nhập"}), 401
    with get_db() as conn:
        notes = conn.execute(
            "SELECT * FROM notes WHERE user_id=? ORDER BY pinned DESC, updated_at DESC",
            (session["user_id"],),
        ).fetchall()
    return jsonify([dict(n) for n in notes])


@notes_bp.route("/api/notes", methods=["POST"])
def create_note():
    if "user_id" not in session:
        return jsonify({"error": "Chưa đăng nhập"}), 401
    data = request.get_json()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO notes (user_id, title, content, color) VALUES (?,?,?,?)",
            (
                session["user_id"],
                data.get("title", "Ghi chú mới"),
                data.get("content", ""),
                data.get("color", "#7c3aed"),
            ),
        )
        note_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        note = conn.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
    return jsonify(dict(note))


@notes_bp.route("/api/notes/<int:note_id>", methods=["PUT"])
def update_note(note_id):
    if "user_id" not in session:
        return jsonify({"error": "Chưa đăng nhập"}), 401
    data = request.get_json()
    with get_db() as conn:
        conn.execute(
            "UPDATE notes SET title=?, content=?, color=?, pinned=?, updated_at=datetime('now','localtime') WHERE id=? AND user_id=?",
            (
                data.get("title"),
                data.get("content"),
                data.get("color"),
                data.get("pinned", 0),
                note_id,
                session["user_id"],
            ),
        )
    return jsonify({"success": True})


@notes_bp.route("/api/notes/<int:note_id>", methods=["DELETE"])
def delete_note(note_id):
    if "user_id" not in session:
        return jsonify({"error": "Chưa đăng nhập"}), 401
    with get_db() as conn:
        conn.execute("DELETE FROM notes WHERE id=? AND user_id=?", (note_id, session["user_id"]))
    return jsonify({"success": True})
