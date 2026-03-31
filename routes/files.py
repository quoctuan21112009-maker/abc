"""Xử lý file: đọc nội dung, đặt tên thông minh, lưu output."""

import base64
import os
import re

from routes.config import ALLOWED_EXTENSIONS


def get_file_category(filename: str) -> tuple[str, str]:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    for cat, exts in ALLOWED_EXTENSIONS.items():
        if ext in exts:
            return cat, ext
    return "other", ext


def read_file_content(filepath: str, filename: str) -> str:
    cat, ext = get_file_category(filename)
    try:
        if cat == "text":
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            return f"📄 Nội dung file **{filename}**:\n```{ext}\n{content[:6000]}\n```"

        elif cat == "image":
            size = os.path.getsize(filepath)
            with open(filepath, "rb") as f:
                img_data = base64.b64encode(f.read()).decode("utf-8")
            mime = {
                "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "gif": "image/gif", "webp": "image/webp", "bmp": "image/bmp",
            }.get(ext, "image/jpeg")
            return f"[IMAGE_BASE64:{mime}:{img_data[:50000]}] File: {filename}, size: {size // 1024}KB"

        elif cat == "video":
            return f"🎬 Video **{filename}** ({os.path.getsize(filepath) // 1024 // 1024}MB) đã tải lên."

        elif ext == "pdf":
            try:
                import PyPDF2
                with open(filepath, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    text = "\n".join(p.extract_text() or "" for p in reader.pages[:20])
                return f"📑 PDF **{filename}**:\n{text[:5000]}"
            except Exception:
                return f"📑 PDF **{filename}** đã upload."

        else:
            return f"📎 File **{filename}** (.{ext}) đã tải lên."

    except Exception as e:
        return f"Lỗi đọc file: {str(e)}"


def generate_smart_filename(code: str, lang: str, index: int) -> str:
    """Tạo tên file có nghĩa dựa trên nội dung code."""
    patterns = {
        "html": [
            r"<title>([^<]{3,40})</title>",
            r"<!--\s*([A-Za-z][A-Za-z0-9 _-]{2,30})\s*-->",
            r"<h1[^>]*>([^<]{3,30})</h1>",
        ],
        "py": [
            r"#\s*([A-Za-z][A-Za-z0-9 _-]{2,30})",
            r"class ([A-Za-z][A-Za-z0-9_]{2,20})",
            r"def ([A-Za-z][A-Za-z0-9_]{2,20})",
        ],
        "js": [
            r"//\s*([A-Za-z][A-Za-z0-9 _-]{2,30})",
            r"function ([A-Za-z][A-Za-z0-9_]{2,20})",
            r"const ([A-Za-z][A-Za-z0-9_]{2,20})",
        ],
        "css": [
            r"/\*\s*([A-Za-z][A-Za-z0-9 _-]{2,30})\s*\*/",
            r"\/\*\s*@title\s+([^\n]{3,30})",
        ],
    }
    ext_map = {
        "python": "py", "py": "py", "html": "html", "css": "css",
        "javascript": "js", "js": "js", "java": "java", "cpp": "cpp",
        "c": "c", "typescript": "ts", "ts": "ts",
    }
    ext = ext_map.get(lang.lower(), lang.lower() or "txt")

    for pattern in patterns.get(ext, []):
        m = re.search(pattern, code[:2000], re.IGNORECASE)
        if m:
            name = m.group(1).strip().lower()
            name = re.sub(r"[^a-z0-9_]", "_", name)
            name = re.sub(r"_+", "_", name).strip("_")
            if 3 <= len(name) <= 30:
                return f"{name}.{ext}"

    defaults = {
        "html": ["webpage", "index", "app", "page", "site"],
        "py":   ["script", "app", "program", "main", "code"],
        "js":   ["script", "app", "main", "module", "code"],
        "css":  ["styles", "theme", "layout", "design"],
    }
    fallback_list = defaults.get(ext, ["code", "file", "output", "result", "snippet"])
    name = fallback_list[index % len(fallback_list)]
    return f"{name}_{index + 1}.{ext}"


def create_output_file(content: str, filename: str, output_dir: str = "outputs") -> str:
    path = os.path.join(output_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path
