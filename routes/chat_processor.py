"""Xử lý tin nhắn chat: gọi AI, thực thi tool calls, lưu lịch sử."""

import re

from routes.ai_client import get_ai_client
from routes.config import DEFAULT_GROQ_API_KEY, DEFAULT_MODEL, DEFAULT_PROVIDER, SYSTEM_PROMPT
from routes.files import create_output_file, generate_smart_filename
from routes.history import get_history, save_history
from routes.tools import (
    extract_youtube_id,
    fetch_url,
    get_news,
    get_weather,
    run_code,
    run_tool,
    search_web,
    search_youtube,
)


def process_message(
    user_message: str,
    session_key: str,
    file_content: str | None = None,
    ai_cfg: dict | None = None,
    image_data: bool | None = None,
) -> tuple[str, list, dict | None, list, list]:
    """
    Xử lý tin nhắn, gọi AI và các công cụ.
    Returns: (reply, output_files, youtube_data, code_outputs, html_files)
    """
    history = get_history(session_key)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in history[-20:]:
        messages.append(msg)

    full_msg = user_message
    if file_content and not file_content.startswith("[IMAGE_BASE64:"):
        full_msg = f"{file_content}\n\n---\nYêu cầu: {user_message}"

    # Build user content (handle image)
    if image_data or (file_content and file_content.startswith("[IMAGE_BASE64:")):
        if file_content and file_content.startswith("[IMAGE_BASE64:"):
            parts = file_content.split(":", 2)
            mime = parts[1] if len(parts) > 1 else "image/jpeg"
            b64 = parts[2].split("]")[0] if len(parts) > 2 else ""
            user_content = [
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                {
                    "type": "text",
                    "text": user_message or "Phân tích và mô tả chi tiết hình ảnh này cho mình nhé!",
                },
            ]
        else:
            user_content = user_message
        messages.append({"role": "user", "content": user_content})
    else:
        messages.append({"role": "user", "content": full_msg})

    prov = (ai_cfg or {}).get("provider", DEFAULT_PROVIDER)
    model = (ai_cfg or {}).get("model", DEFAULT_MODEL)
    key = (ai_cfg or {}).get("api_key", DEFAULT_GROQ_API_KEY)
    _client = get_ai_client(key, prov)

    try:
        vision_model = model
        if image_data or (file_content and file_content.startswith("[IMAGE_BASE64:")):
            if prov == "groq":
                vision_model = "llava-v1.5-7b-4096-preview"
            elif prov == "openai":
                vision_model = "gpt-4o"

        resp = _client.chat.completions.create(
            model=vision_model, messages=messages, max_tokens=4000, temperature=0.75
        )
        reply = resp.choices[0].message.content
    except Exception as e:
        raise Exception(f"Lỗi AI ({prov}/{model}): {str(e)}")

    tool_results = []

    # SEARCH tool
    searches = re.findall(r"\[SEARCH:\s*([^\]]+)\]", reply)
    if searches:
        sc = "\n\n".join(
            f"Kết quả '{q.strip()}':\n{search_web(q.strip())}" for q in searches
        )
        tool_results.append(f"[Kết quả tìm kiếm web]\n{sc}")

    # FETCH tool
    fetches = re.findall(r"\[FETCH:\s*(https?://[^\]]+)\]", reply)
    if fetches:
        fc = "\n\n".join(
            f"Nội dung '{u.strip()}':\n{fetch_url(u.strip())}" for u in fetches[:3]
        )
        tool_results.append(f"[Nội dung trang web]\n{fc}")

    # WEATHER tool
    weathers = re.findall(r"\[WEATHER:\s*([^\]]+)\]", reply)
    if weathers:
        wc = "\n\n".join(get_weather(c.strip()) for c in weathers[:2])
        tool_results.append(f"[Thông tin thời tiết]\n{wc}")

    # NEWS tool
    news_queries = re.findall(r"\[NEWS:\s*([^\]]+)\]", reply)
    if news_queries:
        for q in news_queries[:2]:
            items = get_news(q.strip())
            if items:
                nc = "\n".join(f"- {it['title']}: {it['body'][:200]}" for it in items[:5])
                tool_results.append(f"[Tin tức '{q.strip()}']\n{nc}")

    # RUN_CODE tool
    run_matches = re.findall(r"\[RUN_CODE:\s*(\w+)\n([\s\S]*?)\]", reply)
    code_outputs = []
    for lang, code in run_matches:
        output = run_code(lang.strip(), code.strip())
        code_outputs.append({"lang": lang, "code": code.strip(), "output": output})
        tool_results.append(f"[Kết quả chạy code {lang}]\n{output}")

    # TOOL calls (600+ tools)
    tool_matches = re.findall(r"\[TOOL:\s*([A-Z_]+)\s*(?::\s*([^\]]*))?\]", reply)
    for tool_name, tool_args in tool_matches:
        result = run_tool(tool_name.strip(), (tool_args or "").strip())
        tool_results.append(f"[Tool {tool_name}]\n{result}")

    # Second pass if tools were used
    if tool_results:
        combined = "\n\n---\n".join(tool_results)
        messages.append({"role": "assistant", "content": reply})
        messages.append({
            "role": "user",
            "content": (
                f"Kết quả công cụ:\n{combined}\n\n"
                "Hãy tổng hợp và trả lời người dùng dựa trên thông tin này một cách tự nhiên, thân thiện."
            ),
        })
        try:
            r2 = _client.chat.completions.create(
                model=model, messages=messages, max_tokens=4000, temperature=0.7
            )
            reply = r2.choices[0].message.content
        except Exception:
            pass

    # YOUTUBE tool - by name OR URL
    youtube_data = None
    yt_matches = re.findall(r"\[YOUTUBE:\s*([^\]]+)\]", reply)
    if yt_matches:
        q = yt_matches[0].strip()
        vid_id = extract_youtube_id(q)  # Try URL first
        title = q
        if not vid_id:
            # Search by name/keyword
            vid_id, title = search_youtube(q)
        if vid_id:
            youtube_data = {"video_id": vid_id, "title": title or q}
        reply = re.sub(r"\[YOUTUBE:[^\]]+\]", "", reply).strip()

    # Clean tool markers from reply
    reply = re.sub(r"\[SEARCH:[^\]]+\]", "", reply)
    reply = re.sub(r"\[FETCH:[^\]]+\]", "", reply)
    reply = re.sub(r"\[WEATHER:[^\]]+\]", "", reply)
    reply = re.sub(r"\[NEWS:[^\]]+\]", "", reply)
    reply = re.sub(r"\[RUN_CODE:\s*\w+\n[\s\S]*?\]", "", reply)
    reply = re.sub(r"\[TOOL:[^\]]+\]", "", reply)
    reply = reply.strip()

    # Auto-save code blocks with smart naming
    output_files = []
    html_files = []
    code_blocks = list(re.finditer(r"```(\w+)?\n([\s\S]*?)```", reply))
    for i, match in enumerate(code_blocks):
        lang = (match.group(1) or "").lower().strip()
        code = match.group(2).strip()
        if len(code) > 80:
            fname = generate_smart_filename(code, lang, i)
            create_output_file(code, fname)
            ext = fname.rsplit(".", 1)[-1]
            output_files.append({"name": fname, "type": ext, "lang": lang})
            if ext == "html":
                html_files.append({"name": fname, "code": code})

    # Persist history
    history.append({"role": "user", "content": full_msg if isinstance(full_msg, str) else user_message})
    history.append({"role": "assistant", "content": reply})
    save_history(session_key)

    return reply, output_files, youtube_data, code_outputs, html_files