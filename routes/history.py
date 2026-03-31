"""Quản lý lịch sử chat: in-memory cache + lưu trữ DB."""

import json

from routes.database import get_db

_histories: dict = {}


def get_history(sk: str) -> list:
    if sk not in _histories:
        uid = sk.replace("user_", "").replace("_chat", "")
        try:
            uid_int = int(uid)
            with get_db() as conn:
                sess = conn.execute(
                    "SELECT id, messages FROM ai_sessions WHERE user_id=? ORDER BY updated_at DESC LIMIT 1",
                    (uid_int,),
                ).fetchone()
                if sess:
                    _histories[sk] = json.loads(sess["messages"] or "[]")
                    _histories[f"{sk}_session_id"] = sess["id"]
                else:
                    _histories[sk] = []
        except Exception:
            _histories[sk] = []
    return _histories.setdefault(sk, [])


def save_history(sk: str) -> None:
    uid = sk.replace("user_", "").replace("_chat", "")
    try:
        uid_int = int(uid)
        sess_id = _histories.get(f"{sk}_session_id")
        msgs_json = json.dumps(_histories.get(sk, []), ensure_ascii=False)
        with get_db() as conn:
            if sess_id:
                conn.execute(
                    "UPDATE ai_sessions SET messages=?, updated_at=datetime('now','localtime') WHERE id=?",
                    (msgs_json, sess_id),
                )
            else:
                conn.execute(
                    "INSERT INTO ai_sessions (user_id, messages) VALUES (?,?)",
                    (uid_int, msgs_json),
                )
                new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                _histories[f"{sk}_session_id"] = new_id
    except Exception as e:
        print(f"Save history error: {e}")


def clear_history(sk: str) -> None:
    _histories[sk] = []
    save_history(sk)
