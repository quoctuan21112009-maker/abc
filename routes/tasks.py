"""Routes quản lý công việc (tasks)."""

from flask import Blueprint, jsonify, request, session

from routes.database import get_db

tasks_bp = Blueprint("tasks", __name__)


@tasks_bp.route("/api/tasks", methods=["GET"])
def get_tasks():
    if "user_id" not in session:
        return jsonify({"error": "Chưa đăng nhập"}), 401
    with get_db() as conn:
        tasks = conn.execute(
            "SELECT * FROM tasks WHERE user_id=? ORDER BY created_at DESC",
            (session["user_id"],),
        ).fetchall()
    return jsonify([dict(t) for t in tasks])


@tasks_bp.route("/api/tasks", methods=["POST"])
def create_task():
    if "user_id" not in session:
        return jsonify({"error": "Chưa đăng nhập"}), 401
    data = request.get_json()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO tasks (user_id, title, description, priority, due_date) VALUES (?,?,?,?,?)",
            (
                session["user_id"],
                data.get("title", "Task mới"),
                data.get("description", ""),
                data.get("priority", "medium"),
                data.get("due_date"),
            ),
        )
        task_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        task = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    return jsonify(dict(task))


@tasks_bp.route("/api/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    if "user_id" not in session:
        return jsonify({"error": "Chưa đăng nhập"}), 401
    data = request.get_json()
    with get_db() as conn:
        conn.execute(
            "UPDATE tasks SET title=?, description=?, status=?, priority=?, due_date=? WHERE id=? AND user_id=?",
            (
                data.get("title"),
                data.get("description"),
                data.get("status"),
                data.get("priority"),
                data.get("due_date"),
                task_id,
                session["user_id"],
            ),
        )
    return jsonify({"success": True})


@tasks_bp.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    if "user_id" not in session:
        return jsonify({"error": "Chưa đăng nhập"}), 401
    with get_db() as conn:
        conn.execute("DELETE FROM tasks WHERE id=? AND user_id=?", (task_id, session["user_id"]))
    return jsonify({"success": True})
