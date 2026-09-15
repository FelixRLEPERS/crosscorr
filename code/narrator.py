"""
narrator.py
Голосовой наставник для игры «Охота на призрака».
Озвучка через edge-tts (Microsoft Neural Voices). Бесплатно, без API-ключей.
"""

import asyncio
import concurrent.futures
import io
import threading

import streamlit as st

try:
    import edge_tts
    EDGE_TTS_OK = True
except ImportError:
    EDGE_TTS_OK = False


# ============================================================
# НАСТРОЙКИ ГОЛОСА
# ============================================================

VOICE  = "ru-RU-DmitryNeural"   # мужской, глубокий
RATE   = "+30%"                  # быстрее обычного
PITCH  = "-4Hz"                  # чуть ниже
VOLUME = "+0%"


# ============================================================
# КЭШ АУДИО
# ============================================================

_AUDIO_CACHE = {}
_CACHE_LOCK = threading.Lock()


def _cache_get(text):
    with _CACHE_LOCK:
        return _AUDIO_CACHE.get(text)


def _cache_set(text, audio):
    with _CACHE_LOCK:
        _AUDIO_CACHE[text] = audio


# ============================================================
# ГЕНЕРАЦИЯ АУДИО
# ============================================================

async def _synthesize_async(text):
    communicate = edge_tts.Communicate(
        text=text,
        voice=VOICE,
        rate=RATE,
        pitch=PITCH,
        volume=VOLUME,
    )
    audio_bytes = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_bytes += chunk["data"]
    return audio_bytes


def _synthesize(text):
    def run():
        return asyncio.run(_synthesize_async(text))
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(run).result()


# ============================================================
# ПРЕДГЕНЕРАЦИЯ (в фоне)
# ============================================================

def pregenerate_async(texts):
    def worker():
        for text in texts:
            if _cache_get(text):
                continue
            try:
                audio = _synthesize(text)
                if audio:
                    _cache_set(text, audio)
            except Exception:
                pass
    threading.Thread(target=worker, daemon=True).start()


# ============================================================
# ОЗВУЧКА
# ============================================================

def speak(text, autoplay=True):
    if not EDGE_TTS_OK:
        return False
    if not text or not text.strip():
        return False

    text = text[:4500]

    audio_bytes = _cache_get(text)
    if not audio_bytes:
        try:
            audio_bytes = _synthesize(text)
            if audio_bytes:
                _cache_set(text, audio_bytes)
        except Exception as e:
            st.caption(f"🔇 Озвучка: {e}")
            return False

    if not audio_bytes:
        return False

    try:
        st.audio(io.BytesIO(audio_bytes), format="audio/mp3", autoplay=autoplay)
        return True
    except Exception as e:
        st.caption(f"🔇 Озвучка: {e}")
        return False


# ============================================================
# ХЕЛПЕРЫ
# ============================================================

def build_level_text(level, title, story, task=""):
    if task:
        return (
            f"Уровень {level}. {title}. "
            f"История. {story} "
            f"Задание. {task}"
        )
    return f"Уровень {level}. {title}. История. {story}"


def build_intro_text(name):
    return (
        f"Привет, {name}. Я — твой наставник. "
        f"Мы вместе будем искать призрака. "
        f"Если что-то непонятно — спрашивай, я рядом. "
        f"Поехали."
    )


# ============================================================
# ГОТОВЫЕ ФРАЗЫ
# ============================================================

def narrator_intro(name):
    text = build_intro_text(name)
    speak(text)
    return text


def narrator_level_start(*args, **kwargs):
    level = args[0] if len(args) > 0 else kwargs.get("level", 1)
    title = args[1] if len(args) > 1 else kwargs.get("title", "")
    story = args[2] if len(args) > 2 else kwargs.get("story", "")
    task  = args[3] if len(args) > 3 else kwargs.get("task", "")
    text = build_level_text(level, title, story, task)
    speak(text)
    return text


def narrator_praise():
    text = "Отлично. Ты справился. Так держать, исследователь."
    speak(text)
    return text


def narrator_error():
    text = (
        "Не переживай, это нормально. "
        "Нажми кнопку «Подсказка», и я покажу решение. "
        "Ошибки — это путь к победе."
    )
    speak(text)
    return text


def narrator_skip():
    text = "Ничего страшного. Иногда нужно пропустить, чтобы идти дальше. Ты молодец."
    speak(text)
    return text


def narrator_victory(name):
    text = (
        f"Поздравляю, {name}. Ты прошёл базовый курс. "
        f"Ты научился писать код, работать с данными и искать призрака. "
        f"Теперь выбери свою специализацию. Восемь дверей открыто перед тобой."
    )
    speak(text)
    return text


def narrator_branch_intro(branch_name):
    text = f"Добро пожаловать в ветку {branch_name}. Здесь тебя ждут новые тайны."
    speak(text)
    return text


def narrator_branch_success():
    text = "Отлично. Ты справился с заданием ветки. Продолжай."
    speak(text)
    return text
