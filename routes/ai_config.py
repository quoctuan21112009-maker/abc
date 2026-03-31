"""Routes cấu hình AI provider và model."""

from flask import Blueprint, jsonify, request, session

from routes.config import AVAILABLE_MODELS, DEFAULT_GROQ_API_KEY, DEFAULT_MODEL, DEFAULT_PROVIDER

ai_config_bp = Blueprint("ai_config", __name__)


@ai_config_bp.route("/api/models", methods=["GET"])
def get_models():
    return jsonify(AVAILABLE_MODELS)


@ai_config_bp.route("/api/config", methods=["GET", "POST"])
def ai_config_route():
    if "user_id" not in session:
        return jsonify({"error": "Chưa đăng nhập"}), 401
    if request.method == "POST":
        data = request.get_json()
        prov = data.get("provider", DEFAULT_PROVIDER)
        model = data.get("model", DEFAULT_MODEL)
        key = data.get("api_key", "")
        session["ai_provider"] = prov
        session["ai_model"] = model
        session["ai_api_key"] = key
        session.modified = True
        return jsonify({"success": True, "provider": prov, "model": model})
    return jsonify({
        "provider": session.get("ai_provider") or DEFAULT_PROVIDER,
        "model": session.get("ai_model") or DEFAULT_MODEL,
        "has_key": bool(session.get("ai_api_key")),
        "key_set": bool(session.get("ai_api_key")),
    })
