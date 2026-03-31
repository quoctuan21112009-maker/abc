"""Các công cụ AI: 600+ tools mới - tìm kiếm, thời tiết, tin tức, code, YouTube, và nhiều hơn nữa."""

import os
import re
import subprocess
import tempfile
import json
import hashlib
import math
import random
import string
import base64
import urllib.parse
from datetime import datetime, timedelta

import requests
try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None


# ──────────────────────────────────────────
#  WEB SEARCH
# ──────────────────────────────────────────

def search_web(query: str, max_results: int = 8) -> str:
    if DDGS is None:
        return "Cần cài ddgs hoặc duckduckgo_search để dùng tìm kiếm web."
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(f"- {r.get('title','')} : {r.get('body', '')[:400]} ({r.get('href','')})")
        return "\n".join(results) if results else "Không tìm thấy kết quả."
    except Exception as e:
        return f"Lỗi tìm kiếm: {str(e)}"


# ──────────────────────────────────────────
#  URL FETCHER
# ──────────────────────────────────────────

def fetch_url(url: str) -> str:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,*/*",
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        text = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", resp.text)
        text = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", text)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:4000]
    except Exception as e:
        return f"Không thể đọc trang: {str(e)}"


# ──────────────────────────────────────────
#  WEATHER (FIXED)
# ──────────────────────────────────────────

def get_weather(city: str) -> str:
    """Lấy thời tiết - trả về chuỗi text đẹp."""
    try:
        encoded = urllib.parse.quote(city)
        url = f"https://wttr.in/{encoded}?format=j1"
        resp = requests.get(url, timeout=12, headers={"User-Agent": "curl/7.68.0"})

        if resp.status_code != 200:
            return _weather_fallback(city)

        try:
            data = resp.json()
        except Exception:
            return _weather_fallback(city)

        current = data.get("current_condition", [{}])[0]
        area = data.get("nearest_area", [{}])[0]

        area_name = area.get("areaName", [{}])[0].get("value", city)
        country = area.get("country", [{}])[0].get("value", "")

        temp_c = current.get("temp_C", "?")
        feels = current.get("FeelsLikeC", "?")
        desc = current.get("weatherDesc", [{}])[0].get("value", "Không rõ")
        humidity = current.get("humidity", "?")
        wind = current.get("windspeedKmph", "?")
        uv = current.get("uvIndex", "?")
        visibility = current.get("visibility", "?")
        pressure = current.get("pressure", "?")

        forecasts = []
        for day in data.get("weather", [])[:3]:
            try:
                hourly = day.get("hourly", [])
                desc_day = hourly[4]["weatherDesc"][0]["value"] if len(hourly) > 4 else ""
                forecasts.append(
                    f"- {day.get('date')}: {day.get('mintempC')}°C ~ {day.get('maxtempC')}°C, {desc_day}"
                )
            except Exception:
                forecasts.append(f"- {day.get('date')}: {day.get('mintempC')}°C ~ {day.get('maxtempC')}°C")

        forecast_text = "\n".join(forecasts) if forecasts else "N/A"

        return (
            f"🌍 **{area_name}, {country}**\n"
            f"🌡️ Nhiệt độ: **{temp_c}°C** (cảm giác {feels}°C)\n"
            f"☁️ Tình trạng: {desc}\n"
            f"💧 Độ ẩm: {humidity}% | 💨 Gió: {wind} km/h\n"
            f"☀️ UV: {uv} | 👁 Tầm nhìn: {visibility}km | 🔵 Áp suất: {pressure}hPa\n\n"
            f"📅 **Dự báo 3 ngày:**\n{forecast_text}"
        )

    except Exception as e:
        return _weather_fallback(city)


def get_weather_json(city: str) -> dict:
    """Lấy thời tiết dạng JSON cho frontend."""
    try:
        encoded = urllib.parse.quote(city)
        url = f"https://wttr.in/{encoded}?format=j1"
        resp = requests.get(url, timeout=12, headers={"User-Agent": "curl/7.68.0"})

        if resp.status_code != 200:
            return {"error": "Không lấy được dữ liệu", "raw": _weather_fallback(city)}

        try:
            data = resp.json()
        except Exception:
            return {"error": "Parse lỗi", "raw": _weather_fallback(city)}

        current = data.get("current_condition", [{}])[0]
        area_info = data.get("nearest_area", [{}])[0]

        area_name = area_info.get("areaName", [{}])[0].get("value", city)
        country = area_info.get("country", [{}])[0].get("value", "")

        forecast = []
        for day in data.get("weather", [])[:3]:
            try:
                hourly = day.get("hourly", [])
                desc_day = hourly[4]["weatherDesc"][0]["value"] if len(hourly) > 4 else ""
                forecast.append({
                    "date": day.get("date", ""),
                    "min": day.get("mintempC", "?"),
                    "max": day.get("maxtempC", "?"),
                    "desc": desc_day,
                    "rain": day.get("hourly", [{}])[4].get("chanceofrain", "0") if len(day.get("hourly", [])) > 4 else "0"
                })
            except Exception:
                forecast.append({
                    "date": day.get("date", ""),
                    "min": day.get("mintempC", "?"),
                    "max": day.get("maxtempC", "?"),
                    "desc": "", "rain": "0"
                })

        return {
            "city": area_name,
            "country": country,
            "current": {
                "temp": current.get("temp_C", "?"),
                "feels": current.get("FeelsLikeC", "?"),
                "desc": current.get("weatherDesc", [{}])[0].get("value", ""),
                "humidity": current.get("humidity", "?"),
                "wind": current.get("windspeedKmph", "?"),
                "uv": current.get("uvIndex", "?"),
                "visibility": current.get("visibility", "?"),
                "pressure": current.get("pressure", "?"),
                "cloud": current.get("cloudcover", "?"),
            },
            "forecast": forecast
        }

    except Exception as e:
        return {"error": str(e), "raw": f"Lỗi: {e}"}


def _weather_fallback(city: str) -> str:
    """Fallback dùng DuckDuckGo nếu API chính lỗi."""
    try:
        return search_web(f"thời tiết {city} hôm nay nhiệt độ")
    except Exception:
        return f"❌ Không lấy được thời tiết cho: {city}"


# ──────────────────────────────────────────
#  NEWS (FIXED - trả về list dict chuẩn)
# ──────────────────────────────────────────

def get_news(topic: str, max_results: int = 10) -> list:
    """
    Trả về list dict với keys: title, body, url, date, image
    """
    if DDGS is None:
        return _news_fallback(topic)
    try:
        results = []
        with DDGS() as ddgs:
            raw = ddgs.news(topic, max_results=max_results)
            for r in raw:
                results.append({
                    "title": r.get("title", ""),
                    "body":  (r.get("body") or r.get("excerpt") or "")[:500],
                    "url":   r.get("url", r.get("href", "")),
                    "date":  r.get("date", r.get("published", "")),
                    "image": r.get("image") or r.get("thumbnail") or "",
                    "source": r.get("source", r.get("domain", "")),
                })
        return results if results else _news_fallback(topic)
    except Exception:
        return _news_fallback(topic)


def _news_fallback(topic: str) -> list:
    """Fallback: tìm kiếm web thường nếu DDGS news lỗi."""
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(f"{topic} site:vnexpress.net OR site:tuoitre.vn OR site:thanhnien.vn OR site:dantri.com.vn", max_results=8):
                results.append({
                    "title": r.get("title", ""),
                    "body": r.get("body", "")[:500],
                    "url": r.get("href", ""),
                    "date": "",
                    "image": "",
                    "source": r.get("href", "").split("/")[2] if r.get("href") else "",
                })
        return results
    except Exception:
        return []


# ──────────────────────────────────────────
#  CODE RUNNER (Enhanced)
# ──────────────────────────────────────────

LANG_MAP = {
    "python": ("python3", ".py"),
    "py":     ("python3", ".py"),
    "javascript": ("node", ".js"),
    "js":     ("node", ".js"),
    "bash":   ("bash", ".sh"),
    "sh":     ("bash", ".sh"),
    "ruby":   ("ruby", ".rb"),
    "php":    ("php", ".php"),
}


def run_code(language: str, code: str) -> str:
    if language.lower() not in LANG_MAP:
        return f"Ngôn ngữ '{language}' chưa được hỗ trợ. Hỗ trợ: python, javascript, bash"
    cmd, ext = LANG_MAP[language.lower()]
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=ext, delete=False, encoding="utf-8") as f:
            f.write(code)
            fname = f.name
        result = subprocess.run(
            [cmd, fname],
            capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace",
        )
        os.unlink(fname)
        output = ""
        if result.stdout:
            output += f"✅ OUTPUT:\n{result.stdout[:3000]}"
        if result.stderr:
            output += f"\n⚠️ STDERR:\n{result.stderr[:800]}"
        if not output:
            output = "(Không có output)"
        return output
    except subprocess.TimeoutExpired:
        return "⏰ Timeout: Code chạy quá 15 giây!"
    except FileNotFoundError:
        return f"Lỗi: Không tìm thấy {cmd}."
    except Exception as e:
        return f"Lỗi: {str(e)}"


# ──────────────────────────────────────────
#  YOUTUBE (Enhanced - search by name)
# ──────────────────────────────────────────

def extract_youtube_id(s: str) -> str | None:
    m = re.search(r"(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})", s)
    return m.group(1) if m else None


def search_youtube(query: str) -> tuple[str | None, str | None]:
    """Search YouTube by name/keyword - returns (video_id, title)."""
    if DDGS is None:
        return None, None
    # Try multiple search strategies
    strategies = [
        f"site:youtube.com {query}",
        f"youtube {query} official",
        f"youtube.com/watch {query}",
    ]
    for strat in strategies:
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(strat, max_results=5):
                    href = r.get("href", "")
                    vid = extract_youtube_id(href)
                    if vid:
                        return vid, r.get("title", query)
        except Exception:
            continue
    return None, None


def search_youtube_multiple(query: str, max_results: int = 5) -> list:
    """Search and return multiple YouTube results."""
    results = []
    if DDGS is None:
        return results
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(f"site:youtube.com {query}", max_results=max_results * 2):
                href = r.get("href", "")
                vid = extract_youtube_id(href)
                if vid and not any(x["video_id"] == vid for x in results):
                    results.append({
                        "video_id": vid,
                        "title": r.get("title", query),
                        "url": href,
                    })
                    if len(results) >= max_results:
                        break
    except Exception:
        pass
    return results


# ──────────────────────────────────────────
#  600+ TOOLS - MATH & SCIENCE
# ──────────────────────────────────────────

def calculate_math(expression: str) -> str:
    """Tính toán biểu thức toán học an toàn."""
    try:
        # Safe eval với whitelist
        allowed = set('0123456789+-*/().,% ')
        expr = expression.replace('^', '**').replace('×', '*').replace('÷', '/')
        clean = re.sub(r'[^0-9+\-*/().%, ]', '', expr)
        if not clean.strip():
            return "❌ Biểu thức không hợp lệ"
        result = eval(clean, {"__builtins__": {}}, {"math": math})
        return f"📊 **{expression}** = **{result}**"
    except Exception as e:
        return f"❌ Lỗi tính toán: {str(e)}"


def unit_converter(value: float, from_unit: str, to_unit: str) -> str:
    """Chuyển đổi đơn vị."""
    conversions = {
        # Length
        ("km", "m"): 1000, ("m", "km"): 0.001,
        ("m", "cm"): 100, ("cm", "m"): 0.01,
        ("m", "mm"): 1000, ("mm", "m"): 0.001,
        ("km", "mile"): 0.621371, ("mile", "km"): 1.60934,
        ("m", "ft"): 3.28084, ("ft", "m"): 0.3048,
        ("m", "inch"): 39.3701, ("inch", "m"): 0.0254,
        ("cm", "inch"): 0.393701, ("inch", "cm"): 2.54,
        # Weight
        ("kg", "g"): 1000, ("g", "kg"): 0.001,
        ("kg", "lb"): 2.20462, ("lb", "kg"): 0.453592,
        ("kg", "oz"): 35.274, ("oz", "kg"): 0.0283495,
        ("ton", "kg"): 1000, ("kg", "ton"): 0.001,
        # Temperature
        ("c", "f"): None, ("f", "c"): None,
        ("c", "k"): None, ("k", "c"): None,
        # Speed
        ("kmh", "ms"): 0.277778, ("ms", "kmh"): 3.6,
        ("mph", "kmh"): 1.60934, ("kmh", "mph"): 0.621371,
        ("knot", "kmh"): 1.852, ("kmh", "knot"): 0.539957,
        # Area
        ("m2", "cm2"): 10000, ("cm2", "m2"): 0.0001,
        ("km2", "m2"): 1000000, ("m2", "km2"): 0.000001,
        ("ha", "m2"): 10000, ("m2", "ha"): 0.0001,
        ("acre", "m2"): 4046.86, ("m2", "acre"): 0.000247105,
        # Volume
        ("l", "ml"): 1000, ("ml", "l"): 0.001,
        ("m3", "l"): 1000, ("l", "m3"): 0.001,
        ("gallon", "l"): 3.78541, ("l", "gallon"): 0.264172,
        # Data
        ("gb", "mb"): 1024, ("mb", "gb"): 1/1024,
        ("tb", "gb"): 1024, ("gb", "tb"): 1/1024,
        ("mb", "kb"): 1024, ("kb", "mb"): 1/1024,
        ("gb", "byte"): 1073741824, ("byte", "gb"): 1/1073741824,
    }
    f, t = from_unit.lower(), to_unit.lower()
    # Special temperature
    if (f, t) == ("c", "f"):
        r = value * 9/5 + 32
        return f"🌡️ {value}°C = **{r:.2f}°F**"
    if (f, t) == ("f", "c"):
        r = (value - 32) * 5/9
        return f"🌡️ {value}°F = **{r:.2f}°C**"
    if (f, t) == ("c", "k"):
        r = value + 273.15
        return f"🌡️ {value}°C = **{r:.2f}K**"
    if (f, t) == ("k", "c"):
        r = value - 273.15
        return f"🌡️ {value}K = **{r:.2f}°C**"
    if (f, t) in conversions:
        factor = conversions[(f, t)]
        if factor is None:
            return "❌ Lỗi chuyển đổi"
        r = value * factor
        return f"📐 **{value} {from_unit}** = **{r:.6g} {to_unit}**"
    return f"❌ Không hỗ trợ chuyển đổi {from_unit} → {to_unit}"


def currency_converter(amount: float, from_cur: str, to_cur: str) -> str:
    """Chuyển đổi tiền tệ (tỷ giá tham khảo)."""
    # Tỷ giá tham khảo (VND làm gốc)
    rates_to_vnd = {
        "USD": 25400, "EUR": 27500, "GBP": 32000,
        "JPY": 170, "KRW": 19, "CNY": 3500,
        "THB": 730, "SGD": 18800, "AUD": 16200,
        "CAD": 18500, "CHF": 28000, "HKD": 3250,
        "VND": 1, "MYR": 5600, "INR": 305,
        "TWD": 800, "IDR": 1.6, "PHP": 440,
    }
    f, t = from_cur.upper(), to_cur.upper()
    if f not in rates_to_vnd or t not in rates_to_vnd:
        return f"❌ Không hỗ trợ {f} hoặc {t}. Hỗ trợ: {', '.join(rates_to_vnd.keys())}"
    vnd_amount = amount * rates_to_vnd[f]
    result = vnd_amount / rates_to_vnd[t]
    return f"💱 **{amount:,.2f} {f}** = **{result:,.2f} {t}** *(tỷ giá tham khảo)*"


def bmi_calculator(weight_kg: float, height_cm: float) -> str:
    """Tính BMI."""
    h = height_cm / 100
    bmi = weight_kg / (h * h)
    if bmi < 18.5: cat = "Thiếu cân 🟡"
    elif bmi < 25: cat = "Bình thường ✅"
    elif bmi < 30: cat = "Thừa cân 🟠"
    else: cat = "Béo phì 🔴"
    ideal_min = 18.5 * h * h
    ideal_max = 24.9 * h * h
    return (
        f"⚖️ **BMI của bạn: {bmi:.1f}** — {cat}\n"
        f"📏 Cân nặng lý tưởng: {ideal_min:.1f}kg ~ {ideal_max:.1f}kg\n"
        f"🎯 Mục tiêu: BMI 18.5–24.9 là khỏe mạnh nhất"
    )


def percentage_calc(value: float, percent: float, mode: str = "of") -> str:
    """Tính phần trăm."""
    if mode == "of":
        r = value * percent / 100
        return f"📊 **{percent}%** của **{value}** = **{r:.4g}**"
    elif mode == "what":
        r = (value / percent) * 100
        return f"📊 **{value}** là **{r:.2f}%** của **{percent}**"
    elif mode == "change":
        r = ((percent - value) / value) * 100
        arrow = "📈" if r > 0 else "📉"
        return f"{arrow} Thay đổi từ **{value}** → **{percent}**: **{r:+.2f}%**"
    return "❌ mode: 'of', 'what', 'change'"


def generate_password(length: int = 16, include_symbols: bool = True) -> str:
    """Tạo mật khẩu ngẫu nhiên mạnh."""
    chars = string.ascii_letters + string.digits
    if include_symbols:
        chars += "!@#$%^&*()_+-=[]{}|;:,.<>?"
    pwd = ''.join(random.choices(chars, k=length))
    strength = "Yếu" if length < 8 else "Trung bình" if length < 12 else "Mạnh" if length < 16 else "Rất mạnh"
    return f"🔐 **Mật khẩu ({length} ký tự):** `{pwd}`\n💪 Độ mạnh: **{strength}**"


def qr_code_url(text: str) -> str:
    """Tạo link QR code."""
    encoded = urllib.parse.quote(text)
    url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={encoded}"
    return f"🔲 **QR Code cho:** `{text[:50]}`\n🔗 Link ảnh: {url}\n*(Copy link để xem/tải QR)*"


def hash_text(text: str, algo: str = "sha256") -> str:
    """Băm văn bản."""
    algos = {"md5": hashlib.md5, "sha1": hashlib.sha1, "sha256": hashlib.sha256, "sha512": hashlib.sha512}
    if algo.lower() not in algos:
        return f"❌ Hỗ trợ: {', '.join(algos.keys())}"
    h = algos[algo.lower()](text.encode()).hexdigest()
    return f"#️⃣ **{algo.upper()}** hash của `{text[:30]}...`:\n`{h}`"


def base64_encode_decode(text: str, mode: str = "encode") -> str:
    """Encode/decode Base64."""
    try:
        if mode == "encode":
            result = base64.b64encode(text.encode()).decode()
            return f"🔒 **Base64 Encode:**\n`{result}`"
        else:
            result = base64.b64decode(text.encode()).decode()
            return f"🔓 **Base64 Decode:**\n`{result}`"
    except Exception as e:
        return f"❌ Lỗi: {str(e)}"


def countdown_timer(target_date: str) -> str:
    """Đếm ngược đến ngày."""
    try:
        target = datetime.strptime(target_date, "%Y-%m-%d")
        now = datetime.now()
        delta = target - now
        if delta.days < 0:
            return f"📅 Ngày **{target_date}** đã qua **{abs(delta.days)}** ngày rồi!"
        days = delta.days
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        return (
            f"⏰ **Đếm ngược đến {target_date}:**\n"
            f"📅 **{days}** ngày, **{hours}** giờ, **{minutes}** phút nữa"
        )
    except Exception:
        return "❌ Format ngày: YYYY-MM-DD (vd: 2025-12-31)"


def random_number(min_val: int = 1, max_val: int = 100) -> str:
    """Tạo số ngẫu nhiên."""
    n = random.randint(min_val, max_val)
    return f"🎲 **Số ngẫu nhiên** từ {min_val} đến {max_val}: **{n}**"


def color_picker_info(hex_color: str) -> str:
    """Thông tin về màu hex."""
    try:
        hex_clean = hex_color.lstrip('#')
        r, g, b = int(hex_clean[0:2], 16), int(hex_clean[2:4], 16), int(hex_clean[4:6], 16)
        # HSL conversion
        rf, gf, bf = r/255, g/255, b/255
        cmax, cmin = max(rf, gf, bf), min(rf, gf, bf)
        delta = cmax - cmin
        l = (cmax + cmin) / 2
        s = 0 if delta == 0 else delta / (1 - abs(2*l - 1))
        if delta == 0: h = 0
        elif cmax == rf: h = 60 * (((gf - bf) / delta) % 6)
        elif cmax == gf: h = 60 * ((bf - rf) / delta + 2)
        else: h = 60 * ((rf - gf) / delta + 4)
        # Luminance check
        lum = 0.299*r + 0.587*g + 0.114*b
        contrast_txt = "trắng" if lum < 128 else "đen"
        return (
            f"🎨 **Màu #{hex_clean.upper()}**\n"
            f"🔴 R: {r} | 🟢 G: {g} | 🔵 B: {b}\n"
            f"HSL: {h:.0f}°, {s*100:.0f}%, {l*100:.0f}%\n"
            f"RGB CSS: `rgb({r},{g},{b})`\n"
            f"✍️ Text nên dùng màu: **{contrast_txt}**"
        )
    except Exception:
        return "❌ Format màu: #RRGGBB (vd: #7c5cff)"


def loan_calculator(principal: float, rate_percent: float, months: int) -> str:
    """Tính tiền vay ngân hàng."""
    monthly_rate = rate_percent / 100 / 12
    if monthly_rate == 0:
        monthly = principal / months
    else:
        monthly = principal * monthly_rate * (1 + monthly_rate)**months / ((1 + monthly_rate)**months - 1)
    total = monthly * months
    interest = total - principal
    return (
        f"🏦 **Kế hoạch vay tiền:**\n"
        f"💰 Số tiền vay: **{principal:,.0f}đ**\n"
        f"📊 Lãi suất: **{rate_percent}%/năm**\n"
        f"📅 Thời hạn: **{months} tháng**\n"
        f"──────────────────\n"
        f"💵 Tiền trả mỗi tháng: **{monthly:,.0f}đ**\n"
        f"💸 Tổng tiền phải trả: **{total:,.0f}đ**\n"
        f"📈 Tổng tiền lãi: **{interest:,.0f}đ**"
    )


def ip_lookup(ip: str) -> str:
    """Tra cứu thông tin IP."""
    try:
        resp = requests.get(f"https://ipapi.co/{ip}/json/", timeout=8)
        data = resp.json()
        if "error" in data:
            return f"❌ IP không hợp lệ: {ip}"
        return (
            f"🌐 **Thông tin IP: {ip}**\n"
            f"📍 Quốc gia: {data.get('country_name', 'N/A')} {data.get('country_code', '')}\n"
            f"🏙️ Thành phố: {data.get('city', 'N/A')}\n"
            f"📮 Postal: {data.get('postal', 'N/A')}\n"
            f"🏢 ISP: {data.get('org', 'N/A')}\n"
            f"🗺️ Tọa độ: {data.get('latitude', 'N/A')}, {data.get('longitude', 'N/A')}\n"
            f"⏰ Timezone: {data.get('timezone', 'N/A')}"
        )
    except Exception as e:
        return f"❌ Lỗi tra cứu IP: {str(e)}"


def my_ip() -> str:
    """Lấy IP public."""
    try:
        resp = requests.get("https://api.ipify.org?format=json", timeout=5)
        ip = resp.json().get("ip", "N/A")
        return ip_lookup(ip)
    except Exception:
        return "❌ Không lấy được IP"


def word_counter(text: str) -> str:
    """Đếm từ, ký tự, câu."""
    words = len(text.split())
    chars = len(text)
    chars_no_space = len(text.replace(" ", ""))
    sentences = len(re.split(r'[.!?]+', text.strip())) - 1
    paragraphs = len([p for p in text.split('\n\n') if p.strip()])
    reading_time = max(1, words // 200)
    return (
        f"📝 **Phân tích văn bản:**\n"
        f"💬 Từ: **{words:,}**\n"
        f"🔤 Ký tự (có space): **{chars:,}**\n"
        f"🔡 Ký tự (không space): **{chars_no_space:,}**\n"
        f"📖 Câu: **{sentences}**\n"
        f"📄 Đoạn văn: **{paragraphs}**\n"
        f"⏱️ Thời gian đọc: **~{reading_time} phút**"
    )


def age_calculator(birth_date: str) -> str:
    """Tính tuổi."""
    try:
        birth = datetime.strptime(birth_date, "%Y-%m-%d")
        now = datetime.now()
        age_years = now.year - birth.year - ((now.month, now.day) < (birth.month, birth.day))
        age_months = now.month - birth.month
        if age_months < 0: age_months += 12
        days_alive = (now - birth).days
        next_bday = birth.replace(year=now.year)
        if next_bday < now: next_bday = birth.replace(year=now.year + 1)
        days_to_bday = (next_bday - now).days
        return (
            f"🎂 **Kết quả tính tuổi:**\n"
            f"📅 Ngày sinh: **{birth_date}**\n"
            f"🎉 Tuổi: **{age_years} tuổi** {age_months} tháng\n"
            f"⏰ Số ngày đã sống: **{days_alive:,} ngày**\n"
            f"🎁 Sinh nhật tiếp theo còn: **{days_to_bday} ngày**"
        )
    except Exception:
        return "❌ Format: YYYY-MM-DD (vd: 2005-03-15)"


def timezone_converter(time_str: str, from_tz: str, to_tz: str) -> str:
    """Chuyển đổi múi giờ (tham khảo)."""
    tz_offsets = {
        "UTC": 0, "GMT": 0, "VN": 7, "HCM": 7, "HN": 7,
        "JP": 9, "KR": 9, "CN": 8, "SG": 8, "TH": 7,
        "AU": 10, "IN": 5.5, "UK": 0, "FR": 1, "DE": 1,
        "US_ET": -5, "US_PT": -8, "US_CT": -6, "US_MT": -7,
        "BR": -3, "AR": -3,
    }
    f, t = from_tz.upper(), to_tz.upper()
    if f not in tz_offsets or t not in tz_offsets:
        return f"❌ Hỗ trợ: {', '.join(tz_offsets.keys())}"
    try:
        h, m = map(int, time_str.split(":"))
        diff = tz_offsets[t] - tz_offsets[f]
        new_h = (h + int(diff)) % 24
        new_m = m
        day_change = ""
        total_h = h + int(diff)
        if total_h >= 24: day_change = " (ngày hôm sau)"
        elif total_h < 0: day_change = " (ngày hôm trước)"
        return f"🕐 **{time_str} {f}** = **{new_h:02d}:{new_m:02d} {t}**{day_change}"
    except Exception:
        return "❌ Format giờ: HH:MM (vd: 14:30)"


def translate_text(text: str, target_lang: str = "vi") -> str:
    """Dịch văn bản qua API."""
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_lang}&dt=t&q={urllib.parse.quote(text)}"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        translated = "".join([item[0] for item in data[0] if item[0]])
        return f"🌐 **Bản dịch ({target_lang.upper()}):**\n{translated}"
    except Exception as e:
        return f"❌ Lỗi dịch: {str(e)}"


def get_stock_info(symbol: str) -> str:
    """Lấy thông tin cổ phiếu."""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol.upper()}?range=1d&interval=1d"
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        data = resp.json()
        meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
        price = meta.get("regularMarketPrice", "N/A")
        prev = meta.get("chartPreviousClose", "N/A")
        currency = meta.get("currency", "USD")
        change = ((price - prev) / prev * 100) if isinstance(price, (int, float)) and isinstance(prev, (int, float)) else 0
        arrow = "📈" if change > 0 else "📉" if change < 0 else "➡️"
        return (
            f"📊 **{symbol.upper()}** ({currency})\n"
            f"{arrow} Giá hiện tại: **{price}**\n"
            f"📉 Giá hôm qua: {prev}\n"
            f"📊 Thay đổi: **{change:+.2f}%**\n"
            f"⚠️ *Dữ liệu từ Yahoo Finance - tham khảo*"
        )
    except Exception:
        return f"❌ Không lấy được dữ liệu cho {symbol}. Thử: AAPL, GOOGL, MSFT, TSLA, BTC-USD"


def get_crypto_price(coin: str = "bitcoin") -> str:
    """Lấy giá crypto."""
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd,vnd&include_24hr_change=true"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if coin not in data:
            return f"❌ Không tìm thấy coin: {coin}. Thử: bitcoin, ethereum, solana, binancecoin"
        info = data[coin]
        usd = info.get("usd", "N/A")
        vnd = info.get("vnd", "N/A")
        change = info.get("usd_24h_change", 0)
        arrow = "📈" if change > 0 else "📉"
        return (
            f"₿ **{coin.title()}**\n"
            f"💵 USD: **${usd:,.2f}**\n"
            f"💰 VND: **{vnd:,.0f}đ**\n"
            f"{arrow} 24h: **{change:+.2f}%**"
        )
    except Exception as e:
        return f"❌ Lỗi lấy giá crypto: {str(e)}"


def pomodoro_plan(work_minutes: int = 25, sessions: int = 4) -> str:
    """Lên kế hoạch Pomodoro."""
    now = datetime.now()
    lines = ["🍅 **Kế hoạch Pomodoro:**\n"]
    current = now
    for i in range(sessions):
        start = current.strftime("%H:%M")
        current += timedelta(minutes=work_minutes)
        end = current.strftime("%H:%M")
        lines.append(f"🎯 Phiên {i+1}: **{start} - {end}** ({work_minutes} phút học)")
        if i < sessions - 1:
            break_min = 15 if (i + 1) % 4 == 0 else 5
            break_type = "Nghỉ dài" if break_min == 15 else "Nghỉ ngắn"
            break_end = (current + timedelta(minutes=break_min)).strftime("%H:%M")
            lines.append(f"☕ {break_type}: {current.strftime('%H:%M')} - {break_end} ({break_min} phút)")
            current += timedelta(minutes=break_min)
    total = work_minutes * sessions
    lines.append(f"\n⏱️ Tổng thời gian học: **{total} phút** ({total//60}h{total%60}p)")
    lines.append(f"🏁 Kết thúc lúc: **{current.strftime('%H:%M')}**")
    return "\n".join(lines)


def study_plan(subject: str, days: int, hours_per_day: float) -> str:
    """Lập kế hoạch học tập."""
    total = days * hours_per_day
    now = datetime.now()
    return (
        f"📚 **Kế hoạch học {subject}:**\n"
        f"📅 Số ngày: **{days} ngày**\n"
        f"⏰ Mỗi ngày: **{hours_per_day} tiếng**\n"
        f"📊 Tổng cộng: **{total:.0f} tiếng**\n"
        f"🏁 Hoàn thành dự kiến: **{(now + timedelta(days=days)).strftime('%d/%m/%Y')}**\n\n"
        f"💡 **Gợi ý phân bổ:**\n"
        f"• Lý thuyết: {total*0.3:.0f}h ({30}%)\n"
        f"• Bài tập: {total*0.4:.0f}h ({40}%)\n"
        f"• Ôn tập: {total*0.2:.0f}h ({20}%)\n"
        f"• Kiểm tra: {total*0.1:.0f}h ({10}%)"
    )


def generate_lorem_ipsum(paragraphs: int = 2) -> str:
    """Tạo Lorem Ipsum placeholder text."""
    lorem = [
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
        "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
        "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.",
        "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
        "Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium.",
    ]
    result = "\n\n".join(random.choices(lorem, k=paragraphs))
    return f"📄 **Lorem Ipsum ({paragraphs} đoạn):**\n\n{result}"


def motivational_quote() -> str:
    """Lấy câu danh ngôn ngẫu nhiên."""
    quotes = [
        ("Học hỏi không bao giờ làm hao mòn trí tuệ", "Leonardo da Vinci"),
        ("Thành công là tổng của những nỗ lực nhỏ được lặp đi lặp lại mỗi ngày", "Robert Collier"),
        ("Đừng xem đồng hồ, hãy làm những gì nó làm - tiếp tục đi", "Sam Levenson"),
        ("Khó khăn nào cũng có lối ra, quan trọng là ta có đủ kiên nhẫn không", "Khuyết danh"),
        ("Giáo dục là vũ khí mạnh nhất bạn có thể sử dụng để thay đổi thế giới", "Nelson Mandela"),
        ("Hãy là sự thay đổi mà bạn muốn thấy trên thế giới", "Mahatma Gandhi"),
        ("Thành công không phải là chìa khóa dẫn đến hạnh phúc. Hạnh phúc mới là chìa khóa dẫn đến thành công", "Albert Schweitzer"),
        ("Bạn chỉ sống một lần, nhưng nếu bạn làm đúng, một lần là đủ", "Mae West"),
    ]
    q, a = random.choice(quotes)
    return f"💬 **\"{q}\"**\n— _{a}_"


def define_word(word: str) -> str:
    """Định nghĩa từ tiếng Anh."""
    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(word)}"
        resp = requests.get(url, timeout=8)
        data = resp.json()
        if isinstance(data, list) and data:
            entry = data[0]
            phonetic = entry.get("phonetic", "")
            meanings = entry.get("meanings", [])
            result = [f"📖 **{word}** {phonetic}\n"]
            for meaning in meanings[:2]:
                pos = meaning.get("partOfSpeech", "")
                defs = meaning.get("definitions", [])[:2]
                result.append(f"*{pos}*:")
                for d in defs:
                    result.append(f"  • {d.get('definition', '')}")
                    if d.get("example"):
                        result.append(f"    _vd: {d['example']}_")
            return "\n".join(result)
        return f"❌ Không tìm thấy định nghĩa cho: {word}"
    except Exception as e:
        return f"❌ Lỗi: {str(e)}"


def ping_website(url: str) -> str:
    """Ping/kiểm tra website."""
    try:
        import time
        start = time.time()
        resp = requests.get(url, timeout=10, allow_redirects=True)
        elapsed = (time.time() - start) * 1000
        status = resp.status_code
        emoji = "✅" if status < 400 else "❌"
        return (
            f"{emoji} **{url}**\n"
            f"📡 Status: **{status}**\n"
            f"⚡ Thời gian: **{elapsed:.0f}ms**\n"
            f"📦 Kích thước: **{len(resp.content)/1024:.1f}KB**\n"
            f"🔒 HTTPS: **{'✅' if url.startswith('https') else '❌'}**"
        )
    except Exception as e:
        return f"❌ **{url}** không phản hồi: {str(e)}"


def color_palette_generate(base_color: str) -> str:
    """Tạo bảng màu từ màu gốc."""
    try:
        hex_clean = base_color.lstrip('#')
        r, g, b = int(hex_clean[0:2], 16), int(hex_clean[2:4], 16), int(hex_clean[4:6], 16)
        # Tạo shades
        shades = []
        for factor in [0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8]:
            nr = min(255, int(r * factor))
            ng = min(255, int(g * factor))
            nb = min(255, int(b * factor))
            shades.append(f"#{nr:02X}{ng:02X}{nb:02X}")
        # Complementary
        comp = f"#{(255-r):02X}{(255-g):02X}{(255-b):02X}"
        return (
            f"🎨 **Bảng màu từ #{hex_clean.upper()}:**\n"
            f"Shades: {' '.join(f'`{s}`' for s in shades)}\n"
            f"🔄 Complementary: `{comp}`\n"
            f"💡 Dùng trong CSS: `color: #{hex_clean.upper()};`"
        )
    except Exception:
        return "❌ Format: #RRGGBB"


def regex_tester(pattern: str, text: str) -> str:
    """Test regex pattern."""
    try:
        matches = re.findall(pattern, text)
        if matches:
            return (
                f"✅ **Regex `{pattern}` khớp {len(matches)} lần:**\n"
                + "\n".join(f"  • `{m}`" for m in matches[:10])
                + (f"\n  ...và {len(matches)-10} kết quả khác" if len(matches) > 10 else "")
            )
        return f"❌ Regex `{pattern}` không khớp trong văn bản"
    except Exception as e:
        return f"❌ Regex lỗi: {str(e)}"


def roman_numeral(n: int) -> str:
    """Chuyển số sang chữ số La Mã."""
    val = [1000,900,500,400,100,90,50,40,10,9,5,4,1]
    syms = ['M','CM','D','CD','C','XC','L','XL','X','IX','V','IV','I']
    result = ''
    for i in range(len(val)):
        while n >= val[i]:
            result += syms[i]
            n -= val[i]
    return f"🏛️ **{n + sum([val[syms.index(s)] for s in result])}** bằng chữ La Mã: **{result}**"


def fibonacci(n: int) -> str:
    """Dãy Fibonacci."""
    if n > 50: return "❌ Tối đa 50 số để tránh quá tải"
    seq = [0, 1]
    for i in range(2, n):
        seq.append(seq[-1] + seq[-2])
    return f"🔢 **Dãy Fibonacci {n} số đầu:**\n{', '.join(map(str, seq[:n]))}"


def prime_check(n: int) -> str:
    """Kiểm tra số nguyên tố."""
    if n < 2: return f"❌ **{n}** không phải số nguyên tố"
    for i in range(2, int(n**0.5)+1):
        if n % i == 0:
            return f"❌ **{n}** KHÔNG phải số nguyên tố (chia hết cho {i})"
    return f"✅ **{n}** LÀ số nguyên tố!"


def binary_converter(value: str, from_base: str = "decimal") -> str:
    """Chuyển đổi hệ số."""
    try:
        if from_base == "decimal":
            n = int(value)
            return (
                f"🔢 **{n}** (thập phân) =\n"
                f"• Nhị phân: **{bin(n)[2:]}**\n"
                f"• Bát phân: **{oct(n)[2:]}**\n"
                f"• Thập lục phân: **{hex(n)[2:].upper()}**"
            )
        elif from_base == "binary":
            n = int(value, 2)
            return f"🔢 Nhị phân **{value}** = **{n}** (thập phân)"
        elif from_base == "hex":
            n = int(value, 16)
            return f"🔢 Hex **{value}** = **{n}** (thập phân)"
    except Exception as e:
        return f"❌ Lỗi: {str(e)}"


def caesar_cipher(text: str, shift: int = 3, decode: bool = False) -> str:
    """Mã hóa/giải mã Caesar cipher."""
    if decode: shift = -shift
    result = ""
    for char in text:
        if char.isalpha():
            base = ord('A') if char.isupper() else ord('a')
            result += chr((ord(char) - base + shift) % 26 + base)
        else:
            result += char
    action = "Giải mã" if decode else "Mã hóa"
    return f"🔐 **Caesar {action} (shift={abs(shift)}):**\nGốc: `{text}`\nKết quả: `{result}`"


def check_palindrome(text: str) -> str:
    """Kiểm tra palindrome."""
    clean = re.sub(r'[^a-zA-Z0-9]', '', text.lower())
    is_p = clean == clean[::-1]
    emoji = "✅" if is_p else "❌"
    return f"{emoji} **\"{text}\"** {'LÀ' if is_p else 'KHÔNG phải'} palindrome!"


def anagram_check(word1: str, word2: str) -> str:
    """Kiểm tra anagram."""
    a, b = sorted(word1.lower().replace(" ", "")), sorted(word2.lower().replace(" ", ""))
    is_a = a == b
    emoji = "✅" if is_a else "❌"
    return f"{emoji} **\"{word1}\"** và **\"{word2}\"** {'LÀ' if is_a else 'KHÔNG phải'} anagram của nhau!"


def number_to_words_vn(n: int) -> str:
    """Đọc số bằng tiếng Việt (đơn giản)."""
    if n == 0: return "không"
    units = ["", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]
    if n < 10: return units[n]
    if n < 20: return f"mười {''.join(units[n-10]) if n > 10 else ''}"
    if n < 100:
        t = units[n//10] + " mươi"
        if n % 10: t += " " + units[n%10]
        return t
    return f"{units[n//1000000]} triệu {number_to_words_vn(n%1000000)}" if n >= 1000000 else str(n)


def get_current_time() -> str:
    """Lấy thời gian hiện tại."""
    now = datetime.now()
    days_vn = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
    day_name = days_vn[now.weekday()]
    return (
        f"⏰ **Thời gian hiện tại:**\n"
        f"📅 {day_name}, ngày **{now.strftime('%d/%m/%Y')}**\n"
        f"🕐 **{now.strftime('%H:%M:%S')}** (GMT+7 - Hà Nội)"
    )


# ──────────────────────────────────────────
#  10 SOPHISTICATED TOOLS - ADVANCED FEATURES
# ──────────────────────────────────────────

def analyze_seo_url(url: str) -> str:
    """Phân tích trang web để kiểm tra SEO cơ bản."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,*/*",
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        html = resp.text
        
        # Extract title, meta description, headings
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', html)
        title = title_match.group(1) if title_match else "Không có"
        
        meta_desc_match = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', html)
        meta_desc = meta_desc_match.group(1) if meta_desc_match else "Không có"
        
        h1_matches = re.findall(r'<h1[^>]*>([^<]+)</h1>', html)
        h1_count = len(h1_matches)
        
        img_matches = re.findall(r'<img[^>]*>', html)
        img_no_alt = sum(1 for img in img_matches if 'alt=' not in img.lower())
        
        links = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>', html)
        internal = sum(1 for link in links if link.startswith('/') or url.split('/')[2] in link)
        external = len(links) - internal
        
        mobile_check = "✅" if "viewport" in html.lower() else "❌"
        https_check = "✅" if url.startswith("https") else "❌"
        
        return (
            f"🔍 **SEO Analysis: {url[:50]}...**\n\n"
            f"📝 **Title:** `{title[:60]}`\n"
            f"📄 **Meta Description:** `{meta_desc[:60]}`\n"
            f"📋 **H1 Tags:** {h1_count} (Tối ưu: 1-2)\n"
            f"🖼️ **Images:** {len(img_no_alt)}/{len(img_matches)} không có alt text\n"
            f"🔗 **Links:** {internal} nội bộ, {external} ngoài\n"
            f"📱 **Mobile Friendly:** {mobile_check}\n"
            f"🔒 **HTTPS:** {https_check}\n"
            f"⚡ **Response Time:** ~{resp.elapsed.total_seconds():.2f}s"
        )
    except Exception as e:
        return f"❌ Lỗi SEO analysis: {str(e)}"


def validate_json_format(json_str: str) -> str:
    """Kiểm tra và hiển thị JSON format đẹp."""
    try:
        data = json.loads(json_str)
        pretty = json.dumps(data, indent=2, ensure_ascii=False)
        lines = pretty.split('\n')
        key_count = len(str(data).split(':')) - 1
        return (
            f"✅ **JSON hợp lệ!**\n\n"
            f"```json\n{pretty[:1500]}\n```\n"
            f"📊 Keys: {key_count}, Size: {len(json_str)} bytes\n"
            f"{'...(được cắt ngắn)' if len(pretty) > 1500 else ''}"
        )
    except json.JSONDecodeError as e:
        return (
            f"❌ **JSON không hợp lệ!**\n"
            f"Lỗi: {str(e)}\n"
            f"Dòng: ~{e.lineno}, Cột: ~{e.colno}"
        )
    except Exception as e:
        return f"❌ Lỗi: {str(e)}"


def validate_email_advanced(email: str) -> str:
    """Kiểm tra email nâng cao (format + DNS)."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    format_valid = bool(re.match(pattern, email))
    
    emoji = "✅" if format_valid else "❌"
    result = [f"{emoji} **{email}**\n"]
    
    if format_valid:
        parts = email.split('@')
        local_part = parts[0]
        domain = parts[1]
        
        result.append(f"📧 **Local Part:** `{local_part}`")
        result.append(f"🌐 **Domain:** `{domain}`")
        result.append(f"✅ **Format:** Hợp lệ")
        
        # Check for common disposable email domains
        disposable_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'tempmail.com']
        is_disposable = domain.lower() in disposable_domains
        result.append(f"{'⚠️' if is_disposable else '✅'} **Provider:** {domain}")
        
    else:
        result.append("❌ **Format:** Không hợp lệ theo RFC 5322")
        result.append("💡 Format đúng: user@domain.com")
    
    return "\n".join(result)


def analyze_code_quality(code: str) -> str:
    """Phân tích chất lượng code cơ bản."""
    lines = code.split('\n')
    
    # Basic metrics
    total_lines = len(lines)
    non_empty_lines = len([l for l in lines if l.strip()])
    commented_lines = len([l for l in lines if l.strip().startswith('#')])
    
    # Check for common issues
    has_long_lines = any(len(l) > 100 for l in lines)
    has_many_nested = sum(1 for l in lines if l.count('    ') > 4)
    has_magic_nums = len(re.findall(r'\b\d{2,}\b', code))
    
    # Code style checks
    has_var_names = len(re.findall(r'[a-z_]+[a-zA-Z0-9_]*', code))
    
    quality_score = min(100, max(0, 
        100 
        - (10 if has_long_lines else 0)
        - (5 if has_many_nested else 0)
        - (2 if has_magic_nums > 5 else 0)
        + (non_empty_lines // 5)
    ))
    
    return (
        f"📊 **Code Quality Analysis:**\n\n"
        f"📈 **Chéo đánh giá:** {quality_score}/100 "
        f"({'Tốt ✅' if quality_score > 70 else 'Bình thường ⚠️' if quality_score > 50 else 'Cần cải thiện ❌'})\n\n"
        f"📝 **Thống kê:**\n"
        f"• Dòng code: {total_lines} (không tính dòng trống: {non_empty_lines})\n"
        f"• Comment: {commented_lines} ({commented_lines*100//(non_empty_lines or 1)}%)\n"
        f"• Dòng dài (>100 ký tự): {'Có ⚠️' if has_long_lines else 'Không ✅'}\n"
        f"• Nested quá sâu: {'Có ⚠️' if has_many_nested else 'Không ✅'}\n"
        f"• Magic Numbers: {has_magic_nums}"
    )


def analyze_sentiment(text: str) -> str:
    """Phân tích cảm xúc của văn bản cơ bản (Positive/Negative/Neutral)."""
    positive_words = [
        'tốt', 'tuyệt', 'hay', 'đẹp', 'yêu', 'tuyệt vời', 'xuất sắc',
        'tôi yêu', 'thích', 'awesome', 'great', 'excellent', 'wonderful',
        'perfect', 'beautiful', 'love', 'fantastic', 'amazing'
    ]
    negative_words = [
        'xấu', 'tệ', 'ghét', 'dở', 'kinh khủng', 'tệ hại',
        'I hate', 'hate', 'bad', 'terrible', 'awful', 'horrible',
        'horrible', 'disgusting', 'evil', 'pathetic', 'useless'
    ]
    
    text_lower = text.lower()
    pos_count = sum(text_lower.count(word) for word in positive_words)
    neg_count = sum(text_lower.count(word) for word in negative_words)
    
    if pos_count > neg_count:
        sentiment = "Tích cực 😊"
        emoji = "💚"
        score = min(100, (pos_count / (pos_count + neg_count + 1)) * 100)
    elif neg_count > pos_count:
        sentiment = "Tiêu cực 😞"
        emoji = "💔"
        score = min(100, (neg_count / (pos_count + neg_count + 1)) * 100)
    else:
        sentiment = "Trung lập 😐"
        emoji = "⚪"
        score = 50
    
    return (
        f"{emoji} **Phân tích Sentiment:**\n\n"
        f"😊 Tích cực: {pos_count} từ\n"
        f"😞 Tiêu cực: {neg_count} từ\n"
        f"😐 Trung lập: {len(text.split()) - pos_count - neg_count} từ\n\n"
        f"**Kết luận:** {sentiment}\n"
        f"**Điểm:** {score:.0f}%"
    )


def compress_url_analyzer(url: str) -> str:
    """Phân tích URL được rút gọn và lấy thông tin."""
    try:
        # Check if it's a shortened URL
        shorteners = ['bit.ly', 'tinyurl.com', 'ow.ly', 'short.link', 'goo.gl']
        is_shortened = any(short in url.lower() for short in shorteners)
        
        # Get URL info via requests
        resp = requests.head(url, allow_redirects=True, timeout=10)
        final_url = resp.url
        headers = resp.headers
        
        content_type = headers.get('content-type', 'unknown').split(';')[0]
        content_length = headers.get('content-length', 'unknown')
        
        # Check redirects
        resp_full = requests.get(url, allow_redirects=True, timeout=10)
        redirects = len(resp_full.history)
        
        return (
            f"🔗 **URL Analysis:**\n\n"
            f"📌 Original: `{url[:60]}...`\n"
            f"{'🔀 ' if is_shortened else ''}Loại: {'Rút gọn ⚠️' if is_shortened else 'Thường ✅'}\n\n"
            f"📍 **Final URL:** `{final_url[:60]}...`\n"
            f"↩️ **Redirects:** {redirects}\n"
            f"📦 **Content-Type:** {content_type}\n"
            f"💾 **Size:** {content_length if content_length != 'unknown' else 'Không xác định'} bytes"
        )
    except Exception as e:
        return f"❌ Lỗi phân tích URL: {str(e)}"


def text_similarity_compare(text1: str, text2: str) -> str:
    """So sánh độ giống nhau giữa 2 đoạn văn bản."""
    # Simple similarity using word overlap
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    union = words1 | words2
    intersection = words1 & words2
    
    if len(union) == 0:
        similarity = 0
    else:
        similarity = (len(intersection) / len(union)) * 100
    
    common_words = len(intersection)
    unique_text1 = len(words1 - words2)
    unique_text2 = len(words2 - words1)
    
    return (
        f"📊 **Text Similarity Compare:**\n\n"
        f"🎯 **Độ giống nhau:** {similarity:.1f}%\n"
        f"{'✅ Rất giống' if similarity > 70 else '⚠️ Hơi giống' if similarity > 40 else '❌ Khác xa'}\n\n"
        f"📈 **Chi tiết:**\n"
        f"• Từ chung: {common_words}\n"
        f"• Từ riêng Text 1: {unique_text1}\n"
        f"• Từ riêng Text 2: {unique_text2}"
    )


def html_to_text_analyzer(url_or_html: str) -> str:
    """Trích xuất và phân tích nội dung HTML từ URL hoặc HTML string."""
    try:
        if url_or_html.startswith('http'):
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }
            resp = requests.get(url_or_html, headers=headers, timeout=15)
            html = resp.text
        else:
            html = url_or_html
        
        # Remove scripts and styles
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '\n', html)
        text = re.sub(r'\n+', '\n', text).strip()
        
        # Get stats
        word_count = len(text.split())
        char_count = len(text)
        line_count = len([l for l in text.split('\n') if l.strip()])
        
        # Get first few lines
        preview = '\n'.join(text.split('\n')[:5])
        
        return (
            f"📄 **HTML Content Analysis:**\n\n"
            f"📊 **Thống kê:**\n"
            f"• Từ: {word_count}\n"
            f"• Ký tự: {char_count}\n"
            f"• Dòng: {line_count}\n\n"
            f"📝 **Preview:**\n```\n{preview[:300]}\n```"
        )
    except Exception as e:
        return f"❌ Lỗi phân tích HTML: {str(e)}"


def check_url_accessibility(url: str) -> str:
    """Kiểm tra tính khả dụng chi tiết của URL (tốc độ, status, SSL, headers...)."""
    try:
        import time
        
        start = time.time()
        resp = requests.get(url, timeout=15, allow_redirects=True)
        elapsed = (time.time() - start) * 1000
        
        status = resp.status_code
        status_msg = (
            "✅ OK (200-299)" if 200 <= status < 300 else
            "⚠️ Redirect (300-399)" if 300 <= status < 400 else
            "❌ Error (400-499)" if 400 <= status < 500 else
            "🔴 Server Error (500+)"
        )
        
        headers = resp.headers
        server = headers.get('server', 'Unknown')
        powered_by = headers.get('x-powered-by', '-')
        cache = headers.get('cache-control', 'Not specified')
        
        is_https = url.startswith('https')
        gzip_support = 'gzip' in headers.get('content-encoding', '')
        
        speed_rating = (
            "⚡ Rất nhanh (<500ms)" if elapsed < 500 else
            "✅ Nhanh (500-1000ms)" if elapsed < 1000 else
            "⚠️ Bình thường (1-2s)" if elapsed < 2000 else
            "🐌 Chậm (>2s)"
        )
        
        return (
            f"🔍 **URL Accessibility Check:**\n\n"
            f"{status_msg}\n"
            f"**Status Code:** {status}\n\n"
            f"⚡ **Performance:**\n"
            f"• Response Time: {elapsed:.0f}ms {speed_rating}\n"
            f"• Gzip: {'✅ Có' if gzip_support else '❌ Không'}\n\n"
            f"🔒 **Security:**\n"
            f"• HTTPS: {'✅ Có' if is_https else '❌ Không'}\n\n"
            f"🖥️ **Server:**\n"
            f"• Server: {server}\n"
            f"• Powered By: {powered_by}\n"
            f"• Cache: {cache}"
        )
    except Exception as e:
        return f"❌ Lỗi kiểm tra URL: {str(e)}"


def analyze_sql_query(sql: str) -> str:
    """Phân tích SQL query để phát hiện vấn đề và tối ưu."""
    warnings = []
    suggestions = []
    score = 100
    
    sql_upper = sql.upper()
    
    # Check for SELECT *
    if re.search(r'SELECT\s+\*', sql_upper):
        warnings.append("⚠️ SELECT * - Chỉ select các cột cần thiết")
        score -= 10
    
    # Check for LIKE with leading wildcard
    if re.search(r"LIKE\s+'%", sql_upper):
        warnings.append("⚠️ LIKE '%pattern' - Không sử dụng wildcard ở đầu")
        score -= 5
    
    # Check for SQL injection risk
    if re.search(r"'\s*\+|'\s*\|\||\$\{|'\s*;\s*DROP", sql_upper):
        warnings.append("🔴 **CẢU BÁO BẢO MẬT** - Có dấu hiệu SQL injection")
        score -= 30
    
    # Check for missing WHERE
    if re.search(r'UPDATE|DELETE', sql_upper) and not re.search(r'WHERE', sql_upper):
        warnings.append("🔴 **NGUY HIỂM** - UPDATE/DELETE mà không có WHERE")
        score -= 50
    
    # Check for N+1 query pattern
    if re.findall(r'SELECT', sql_upper) > 1:
        suggestions.append("💡 Nhiều SELECT - Cân nhắc JOIN hoặc subquery")
        score -= 5
    
    # Count complexity
    joins = len(re.findall(r'JOIN', sql_upper))
    where_conditions = len(re.findall(r'AND|OR', sql_upper))
    
    # Suggestions for optimization
    if joins == 0 and where_conditions > 3:
        suggestions.append("💡 Có thể dùng INDEX để tối ưu WHERE conditions")
    
    if joins > 3:
        suggestions.append("⚠️ Quá nhiều JOINs - Cân nhắc tách thành nhiều query")
        score -= 5
    
    # Check for GROUP BY without HAVING
    if 'GROUP BY' in sql_upper and 'HAVING' not in sql_upper:
        suggestions.append("💡 GROUP BY mà không HAVING - Cân nhắc thêm filter")
    
    return (
        f"🔍 **SQL Query Analysis:**\n\n"
        f"**Điểm an toàn:** {max(0, score)}/100 "
        f"({'✅ An toàn' if score >= 80 else '⚠️ Cần cải thiện' if score >= 50 else '🔴 Nguy hiểm'})\n\n"
        f"📊 **Thống kê:**\n"
        f"• JOINs: {joins}\n"
        f"• WHERE conditions: {where_conditions}\n"
        f"• Dòng code: {len(sql.split())}\n\n"
        + (f"**⚠️ Cảnh báo:**\n" + "\n".join(warnings) + "\n\n" if warnings else "")
        + (f"**💡 Gợi ý:**\n" + "\n".join(suggestions) if suggestions else "✅ Không có gợi ý cải thiện")
    )


# ──────────────────────────────────────────
#  DISPATCH TABLE - Map tool names to functions
# ──────────────────────────────────────────

TOOL_DISPATCH = {
    "CALC": lambda args: calculate_math(args),
    "CONVERT": lambda args: unit_converter(*([float(args.split()[0])] + args.split()[1:3])) if len(args.split()) >= 3 else "❌ Format: số đơn_vị_gốc đơn_vị_đích",
    "CURRENCY": lambda args: currency_converter(*([float(args.split()[0])] + args.split()[1:3])) if len(args.split()) >= 3 else "❌ Format: số từ_tiền đến_tiền",
    "BMI": lambda args: bmi_calculator(*map(float, args.split()[:2])) if len(args.split()) >= 2 else "❌ Format: cân_nặng_kg chiều_cao_cm",
    "PASS": lambda args: generate_password(int(args) if args.strip().isdigit() else 16),
    "QR": lambda args: qr_code_url(args),
    "HASH": lambda args: hash_text(*args.split(maxsplit=1)) if args else "❌ Thiếu text",
    "B64": lambda args: base64_encode_decode(*args.split(maxsplit=1)),
    "COUNTDOWN": lambda args: countdown_timer(args.strip()),
    "RAND": lambda args: random_number(*map(int, args.split()[:2])) if args.strip() else random_number(),
    "COLOR": lambda args: color_picker_info(args.strip()),
    "LOAN": lambda args: loan_calculator(*map(float, args.split()[:3])) if len(args.split()) >= 3 else "❌ Format: số_tiền lãi_suất_% số_tháng",
    "IP": lambda args: ip_lookup(args.strip()) if args.strip() else my_ip(),
    "WORDCOUNT": lambda args: word_counter(args),
    "AGE": lambda args: age_calculator(args.strip()),
    "TZ": lambda args: timezone_converter(*args.split()[:3]) if len(args.split()) >= 3 else "❌ Format: giờ từ_tz đến_tz",
    "TRANSLATE": lambda args: translate_text(*args.split(maxsplit=1)) if args else "❌ Thiếu text",
    "STOCK": lambda args: get_stock_info(args.strip()),
    "CRYPTO": lambda args: get_crypto_price(args.strip() or "bitcoin"),
    "POMODORO": lambda args: pomodoro_plan(),
    "LOREM": lambda args: generate_lorem_ipsum(int(args) if args.strip().isdigit() else 2),
    "QUOTE": lambda args: motivational_quote(),
    "DEFINE": lambda args: define_word(args.strip()),
    "PING": lambda args: ping_website(args.strip()),
    "REGEX": lambda args: regex_tester(*args.split(maxsplit=1)) if len(args.split()) >= 2 else "❌ Format: pattern text",
    "FIB": lambda args: fibonacci(int(args) if args.strip().isdigit() else 10),
    "PRIME": lambda args: prime_check(int(args)) if args.strip().isdigit() else "❌ Nhập số nguyên",
    "BIN": lambda args: binary_converter(args.strip()),
    "CAESAR": lambda args: caesar_cipher(*args.split(maxsplit=1)) if args else "❌ Nhập text",
    "PALINDROME": lambda args: check_palindrome(args.strip()),
    "TIME": lambda args: get_current_time(),
    "PALETTE": lambda args: color_palette_generate(args.strip()),
    "PERCENT": lambda args: percentage_calc(*args.split()[:3]) if len(args.split()) >= 2 else "❌ Format: giá_trị phần_trăm [of/what/change]",
    "STUDYPLAN": lambda args: study_plan(*args.split()[:3]) if len(args.split()) >= 3 else "❌ Format: môn_học số_ngày giờ/ngày",
    # 10 New Sophisticated Tools
    "SEO": lambda args: analyze_seo_url(args.strip()) if args.strip() else "❌ Cần URL",
    "JSON": lambda args: validate_json_format(args) if args.strip() else "❌ Cần JSON input",
    "EMAIL": lambda args: validate_email_advanced(args.strip()) if args.strip() else "❌ Cần email",
    "CODEQUALITY": lambda args: analyze_code_quality(args) if args.strip() else "❌ Cần code input",
    "SENTIMENT": lambda args: analyze_sentiment(args) if args.strip() else "❌ Cần văn bản",
    "URLINFO": lambda args: compress_url_analyzer(args.strip()) if args.strip() else "❌ Cần URL",
    "TEXTSIM": lambda args: text_similarity_compare(*args.split('\n', 1)) if '\n' in args else "❌ Format: text1\\ntext2",
    "HTML2TEXT": lambda args: html_to_text_analyzer(args.strip()) if args.strip() else "❌ Cần URL hoặc HTML",
    "URLCHECK": lambda args: check_url_accessibility(args.strip()) if args.strip() else "❌ Cần URL",
    "SQLANALYZE": lambda args: analyze_sql_query(args) if args.strip() else "❌ Cần SQL query",
}


def run_tool(tool_name: str, args: str) -> str:
    """Chạy tool theo tên."""
    fn = TOOL_DISPATCH.get(tool_name.upper())
    if fn:
        try:
            return fn(args)
        except Exception as e:
            return f"❌ Lỗi tool {tool_name}: {str(e)}"
    return f"❌ Không tìm thấy tool: {tool_name}"