"""Khởi tạo OpenAI-compatible client cho các AI provider."""

from openai import OpenAI
from routes.config import DEFAULT_GROQ_API_KEY, DEFAULT_PROVIDER, PROVIDER_URLS


def get_ai_client(api_key: str | None = None, provider: str | None = None) -> OpenAI:
    """Tạo OpenAI client cho provider được chỉ định."""
    prov = (provider or DEFAULT_PROVIDER).lower()
    key = api_key if api_key else DEFAULT_GROQ_API_KEY
    base_url = PROVIDER_URLS.get(prov, PROVIDER_URLS["groq"])
    headers: dict = {}
    if prov == "openrouter":
        headers = {"HTTP-Referer": "https://dnsbot.app", "X-Title": "DNS Bot 11A1"}
    return OpenAI(api_key=key, base_url=base_url, default_headers=headers)
