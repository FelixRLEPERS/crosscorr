"""
🎮 CrossCorr — «ОХОТА НА ПРИЗРАКА»
Фон — MP4. Музыка — MP3 + кастомный слайдер громкости в правом нижнем углу.
Запуск: python -m streamlit run quest.py
"""

import os
import glob
import base64
import streamlit as st
import streamlit.components.v1 as components

# ============================================================
# ПОИСК МЕДИА-ФАЙЛОВ
# ============================================================

def _find_first(ext):
    files = sorted(glob.glob(f"*.{ext}"))
    return files[0] if files else None

BG_VIDEO_FILE = _find_first("mp4")
MUSIC_FILE    = _find_first("mp3")


@st.cache_data(show_spinner=False)
def _file_to_b64(path):
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None


BG_VIDEO_B64 = _file_to_b64(BG_VIDEO_FILE)
MUSIC_B64    = _file_to_b64(MUSIC_FILE)


# ============================================================
# НАРРАТОР
# ============================================================

try:
    from narrator import (
        speak,
        narrator_intro, narrator_level_start,
        narrator_praise, narrator_error, narrator_skip,
        narrator_victory, narrator_branch_intro, narrator_branch_success
    )
except Exception:
    def speak(*a, **k): pass
    def narrator_intro(*a, **k): pass
    def narrator_level_start(*a, **k): pass
    def narrator_praise(*a, **k): pass
    def narrator_error(*a, **k): pass
    def narrator_skip(*a, **k): pass
    def narrator_victory(*a, **k): pass
    def narrator_branch_intro(*a, **k): pass
    def narrator_branch_success(*a, **k): pass


# ============================================================
# СТРАНИЦА
# ============================================================

st.set_page_config(
    page_title="CrossCorr — Охота на призрака",
    page_icon="👻",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ============================================================
# СОСТОЯНИЕ
# ============================================================

_defaults = {
    "level": 1, "name": "", "fragments": 0, "attempts": 0,
    "show_hint": False, "game_started": False,
    "branch": None, "branch_level": 1, "branches_done": [],
    "show_branches": False,
    "music_vol": 12,
    "music_muted": False,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ============================================================
# ФОН — ВИДЕО + СЛАЙДЕР ГРОМКОСТИ
# ============================================================

def inject_media():
    """Вставляет видео-фон и кастомный слайдер громкости в правом нижнем углу."""

    st.markdown("""
    <style>
    /* ===== КОРНЕВОЙ ФОН-ВИДЕО ===== */
    #crosscorr-bg-video {
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
        object-fit: cover !important;
        z-index: 0 !important;
        pointer-events: none !important;
        opacity: 1.0 !important;
    }
    #crosscorr-bg-overlay {
        position: fixed !important;
        inset: 0 !important;
        background: radial-gradient(
            ellipse at center,
            rgba(0,0,0,0.25) 0%,
            rgba(0,0,0,0.50) 55%,
            rgba(0,0,0,0.70) 100%
        ) !important;
        z-index: 1 !important;
        pointer-events: none !important;
    }
    [data-testid="stAppViewContainer"] > section,
    .main, .block-container {
        position: relative !important;
        z-index: 10 !important;
    }
    .stApp {
        background: #0d0d0d !important;
    }

    /* ===== ИСПРАВЛЕНИЕ КЛИКОВ ПО КНОПКАМ ===== */
    .stButton > button,
    div.stButton > button {
        position: relative !important;
        z-index: 2147483645 !important;
        pointer-events: auto !important;
    }
    .stButton {
        position: relative !important;
        z-index: 2147483645 !important;
    }

    /* ===== IFRAME СО СЛАЙДЕРОМ — ФИКСИРУЕМ В ПРАВОМ НИЖНЕМ УГЛУ ===== */
    iframe[title="streamlit_component"] {
        position: fixed !important;
        bottom: 22px !important;
        right: 22px !important;
        top: auto !important;
        left: auto !important;
        width: 320px !important;
        height: 80px !important;
        min-width: 320px !important;
        max-width: 320px !important;
        min-height: 80px !important;
        max-height: 80px !important;
        z-index: 2147483646 !important;
        border: none !important;
        background: transparent !important;
        pointer-events: auto !important;
        overflow: hidden !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    /* ===== СКРЫТИЕ НАТИВНЫХ АУДИО-ПЛЕЕРОВ ===== */
    audio,
    .stAudio,
    [data-testid="stAudio"],
    [data-testid*="Audio"],
    [data-testid*="audio"],
    .element-container audio {
        position: fixed !important;
        top: -99999px !important;
        left: -99999px !important;
        width: 1px !important;
        height: 1px !important;
        opacity: 0 !important;
        visibility: hidden !important;
        pointer-events: none !important;
        z-index: -99999 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # --- ВИДЕО-ФОН ---
    if BG_VIDEO_B64:
        st.markdown(f"""
        <video id="crosscorr-bg-video" autoplay loop muted playsinline>
            <source src="data:video/mp4;base64,{BG_VIDEO_B64}" type="video/mp4">
        </video>
        <div id="crosscorr-bg-overlay"></div>
        """, unsafe_allow_html=True)

    # --- МУЗЫКА + КАСТОМНЫЙ СЛАЙДЕР ---
    if MUSIC_B64:
        default_vol = int(st.session_state.music_vol)
        muted_class = "muted" if st.session_state.music_muted else ""

        # Скрытое аудио в главном документе Streamlit
        st.markdown(f"""
        <audio id="crosscorr-bgm" loop preload="auto"
               style="position:fixed;top:-99999px;left:-99999px;width:1px;height:1px;opacity:0;pointer-events:none;">
            <source src="data:audio/mpeg;base64,{MUSIC_B64}" type="audio/mpeg">
        </audio>
        """, unsafe_allow_html=True)

        # --- САМ СЛАЙДЕР ВНУТРИ IFRAME ---
        components.html(f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="utf-8">
        <style>
            html, body {{
                margin: 0;
                padding: 0;
                width: 100%;
                height: 100%;
                background: transparent;
                overflow: hidden;
                font-family: 'Manrope', 'Inter', system-ui, sans-serif;
            }}
            #panel {{
                box-sizing: border-box;
                width: 100%;
                height: 100%;
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 12px 18px;
                background: rgba(10,10,10,0.85);
                border: 1px solid rgba(255,255,255,0.16);
                border-radius: 18px;
                backdrop-filter: blur(20px) saturate(140%);
                -webkit-backdrop-filter: blur(20px) saturate(140%);
                box-shadow: 0 14px 40px rgba(0,0,0,0.6);
                user-select: none;
            }}
            #icon {{
                font-size: 20px;
                color: #ffffff;
                cursor: pointer;
                line-height: 1;
                filter: drop-shadow(0 0 6px rgba(255,255,255,0.35));
            }}
            #icon.muted {{
                color: #555;
                filter: none;
            }}
            #track {{
                position: relative;
                flex: 1;
                height: 22px;
                cursor: pointer;
                display: flex;
                align-items: center;
                touch-action: none;
            }}
            #rail {{
                position: absolute;
                left: 0;
                right: 0;
                top: 50%;
                height: 6px;
                transform: translateY(-50%);
                background: rgba(255,255,255,0.14);
                border-radius: 3px;
                pointer-events: none;
            }}
            #fill {{
                position: absolute;
                left: 0;
                top: 50%;
                height: 6px;
                transform: translateY(-50%);
                background: #ffffff;
                border-radius: 3px;
                pointer-events: none;
                width: 12%;
            }}
            #knob {{
                position: absolute;
                top: 50%;
                left: 12%;
                width: 16px;
                height: 16px;
                margin-left: -8px;
                margin-top: -8px;
                border-radius: 50%;
                background: #ffffff;
                box-shadow: 0 0 10px rgba(255,255,255,0.75),
                            0 0 22px rgba(255,255,255,0.4);
                pointer-events: none;
            }}
        </style>
        </head>
        <body>
            <div id="panel">
                <span id="icon" class="{muted_class}">♪</span>
                <div id="track">
                    <div id="rail"></div>
                    <div id="fill"></div>
                    <div id="knob"></div>
                </div>
            </div>

            <script>
            (function() {{
                var parentDoc = window.parent.document;

                var icon  = document.getElementById('icon');
                var track = document.getElementById('track');
                var fill  = document.getElementById('fill');
                var knob  = document.getElementById('knob');

                function getAudio() {{
                    return parentDoc.getElementById('crosscorr-bgm');
                }}

                var vol = parseInt(localStorage.getItem('crosscorr_vol') || '{default_vol}');
                var muted = localStorage.getItem('crosscorr_muted') === 'true';
                if (isNaN(vol)) vol = {default_vol};
                vol = Math.max(0, Math.min(100, vol));

                function render() {{
                    fill.style.width = vol + '%';
                    knob.style.left  = vol + '%';
                    icon.classList.toggle('muted', muted);
                }}

                function apply() {{
                    var a = getAudio();
                    if (a) a.volume = muted ? 0 : vol / 100;
                }}

                function tryPlay() {{
                    var a = getAudio();
                    if (!a) return;
                    if (muted) return;
                    var p = a.play();
                    if (p && p.catch) p.catch(function(){{}});
                }}

                var dragging = false;

                function posToVol(clientX) {{
                    var rect = track.getBoundingClientRect();
                    var x = clientX - rect.left;
                    if (x < 0) x = 0;
                    if (x > rect.width) x = rect.width;
                    return Math.round((x / rect.width) * 100);
                }}

                track.addEventListener('pointerdown', function(e) {{
                    dragging = true;
                    try {{ track.setPointerCapture(e.pointerId); }} catch(err) {{}}
                    vol = posToVol(e.clientX);
                    render();
                    apply();
                    localStorage.setItem('crosscorr_vol', vol);
                    if (vol > 0 && muted) {{
                        muted = false;
                        localStorage.setItem('crosscorr_muted', 'false');
                        render();
                        tryPlay();
                    }}
                    e.preventDefault();
                }});

                track.addEventListener('pointermove', function(e) {{
                    if (!dragging) return;
                    vol = posToVol(e.clientX);
                    render();
                    apply();
                    localStorage.setItem('crosscorr_vol', vol);
                }});

                track.addEventListener('pointerup', function(e) {{
                    if (!dragging) return;
                    dragging = false;
                    try {{ track.releasePointerCapture(e.pointerId); }} catch(err) {{}}
                    localStorage.setItem('crosscorr_vol', vol);
                }});

                track.addEventListener('pointercancel', function() {{
                    dragging = false;
                    localStorage.setItem('crosscorr_vol', vol);
                }});

                icon.addEventListener('click', function() {{
                    muted = !muted;
                    localStorage.setItem('crosscorr_muted', muted ? 'true' : 'false');
                    render();
                    apply();
                    if (!muted) tryPlay();
                }});

                render();
                apply();

                parentDoc.addEventListener('click', tryPlay, {{ once: true }});
                parentDoc.addEventListener('keydown', tryPlay, {{ once: true }});
                tryPlay();

                setInterval(function() {{
                    var a = getAudio();
                    if (a) {{
                        var target = muted ? 0 : vol / 100;
                        if (Math.abs(a.volume - target) > 0.001) {{
                            a.volume = target;
                        }}
                    }}
                }}, 500);
            }})();
            </script>
        </body>
        </html>
        """, height=80)


inject_media()


# ============================================================
# ГЛАВНЫЕ СТИЛИ
# ============================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Manrope', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    color: #ffffff;
    -webkit-font-smoothing: antialiased;
}

#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }
[data-testid="stToolbar"], [data-testid="stDecoration"] { display: none; }

.block-container {
    padding-top: 3rem !important;
    padding-bottom: 6rem !important;
    max-width: 1080px !important;
}

/* ---------- ТИПОГРАФИКА ---------- */
h1, h2, h3, h4 {
    font-family: 'Manrope', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: -0.025em !important;
    color: #ffffff !important;
    line-height: 1.15 !important;
}
p, li, span, div, label { color: #c8c8c8 !important; line-height: 1.7; }
code, pre { font-family: 'JetBrains Mono', monospace !important; }
code {
    background: rgba(255,255,255,0.08) !important;
    color: #ffffff !important;
    padding: 2px 8px !important;
    border-radius: 6px !important;
    font-size: 0.9em !important;
    border: 1px solid rgba(255,255,255,0.08);
}

/* ---------- ЛОГОТИП ---------- */
.crosscorr-logo {
    font-family: 'Manrope', sans-serif;
    font-weight: 800;
    font-size: 4.2em;
    letter-spacing: -0.045em;
    text-align: center;
    margin: 0;
    line-height: 1;
    background: linear-gradient(180deg, #ffffff 0%, #ffffff 45%, #6a6a6a 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: fadeUp 0.9s ease-out both;
}
.crosscorr-tagline {
    text-align: center;
    font-family: 'Manrope', sans-serif;
    font-weight: 400;
    color: #909090 !important;
    font-size: 0.85em;
    letter-spacing: 0.35em;
    text-transform: uppercase;
    margin-top: 14px;
    margin-bottom: 55px;
    animation: fadeUp 0.9s 0.15s ease-out both;
}
.level-title {
    font-family: 'Manrope', sans-serif;
    font-size: 2.5em;
    font-weight: 800;
    letter-spacing: -0.03em;
    text-align: center;
    margin: 0 0 40px 0;
    color: #ffffff;
    line-height: 1.1;
    text-shadow: 0 2px 20px rgba(0,0,0,0.8);
    animation: fadeUp 0.6s ease-out both;
}
@keyframes fadeUp {
    from { opacity: 0; transform: translateY(14px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* ---------- КАРТОЧКИ ---------- */
.card {
    background: rgba(0,0,0,0.6);
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 20px;
    padding: 26px 30px;
    margin: 16px 0;
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    transition: border-color 0.35s ease, box-shadow 0.35s ease, transform 0.35s ease;
    animation: fadeUp 0.6s ease-out both;
}
.card:hover {
    border-color: rgba(255,255,255,0.28);
    box-shadow: 0 20px 60px rgba(0,0,0,0.55), 0 0 40px rgba(255,255,255,0.05);
    transform: translateY(-2px);
}
.card-label {
    font-family: 'Manrope', sans-serif;
    font-weight: 600;
    font-size: 0.8em;
    color: #a8a8a8 !important;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-bottom: 14px;
}
.card p { color: #e5e5e5 !important; font-size: 1.05em; line-height: 1.75; margin: 0; }
.card b, .card strong { color: #ffffff !important; font-weight: 700; }

/* ---------- СТАТИСТИКА ---------- */
.stat-box {
    background: rgba(0,0,0,0.6);
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 18px;
    padding: 20px 22px;
    text-align: center;
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    transition: all 0.35s ease;
    animation: fadeUp 0.5s ease-out both;
}
.stat-box:hover {
    border-color: rgba(255,255,255,0.3);
    background: rgba(0,0,0,0.75);
    transform: translateY(-2px);
}
.stat-label {
    font-family: 'Manrope', sans-serif;
    font-weight: 500;
    font-size: 0.78em;
    color: #a8a8a8 !important;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}
.stat-value {
    font-family: 'Manrope', sans-serif;
    font-size: 2em;
    font-weight: 700;
    color: #ffffff !important;
    line-height: 1.1;
    margin-top: 8px;
    letter-spacing: -0.02em;
}

/* ---------- ВЕТКИ ---------- */
.branch-card {
    background: rgba(0,0,0,0.6);
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 20px;
    padding: 26px 28px;
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    animation: fadeUp 0.6s ease-out both;
}
.branch-card:hover {
    border-color: rgba(255,255,255,0.32);
    background: rgba(0,0,0,0.78);
    transform: translateY(-4px);
    box-shadow: 0 24px 70px rgba(0,0,0,0.65), 0 0 60px rgba(255,255,255,0.08);
}
.branch-name {
    font-family: 'Manrope', sans-serif;
    font-size: 1.35em;
    font-weight: 700;
    color: #ffffff !important;
    letter-spacing: -0.015em;
    margin: 0 0 10px 0;
}
.branch-desc {
    color: #b0b0b0 !important;
    font-size: 0.95em;
    line-height: 1.6;
    margin-bottom: 16px;
}
.branch-status {
    font-family: 'Manrope', sans-serif;
    font-weight: 600;
    font-size: 0.78em;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #888 !important;
}
.branch-status.done { color: #ffffff !important; }

/* ---------- КНОПКИ ---------- */
div.stButton > button {
    position: relative !important;
    z-index: 2147483645 !important;
    pointer-events: auto !important;
    width: 100% !important;
    background: rgba(0,0,0,0.55) !important;
    color: #ffffff !important;
    font-family: 'Manrope', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.98em !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    border-radius: 14px !important;
    padding: 13px 22px !important;
    transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1) !important;
    cursor: pointer !important;
    overflow: hidden;
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
}
div.stButton > button:hover {
    background: rgba(255,255,255,0.96) !important;
    color: #000000 !important;
    border-color: #ffffff !important;
    transform: translateY(-2px);
    box-shadow:
        0 0 26px rgba(255,255,255,0.55),
        0 0 52px rgba(255,255,255,0.28) !important;
}
div.stButton > button:active { transform: translateY(0); }
div.stButton > button:focus {
    outline: none !important;
    border-color: rgba(255,255,255,0.55) !important;
    box-shadow: 0 0 0 3px rgba(255,255,255,0.12) !important;
}
div.stButton > button::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.85), transparent);
    transition: left 0.7s ease;
}
div.stButton > button:hover::before { left: 100%; }

/* ---------- ПОЛЯ ---------- */
.stTextArea textarea {
    background: rgba(0,0,0,0.75) !important;
    color: #f0f0f0 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.95em !important;
    line-height: 1.7 !important;
    border: 1px solid rgba(255,255,255,0.16) !important;
    border-radius: 16px !important;
    padding: 18px 22px !important;
    caret-color: #ffffff;
}
.stTextArea textarea:focus {
    border-color: rgba(255,255,255,0.45) !important;
    box-shadow: 0 0 0 3px rgba(255,255,255,0.08) !important;
}
.stTextInput input {
    background: rgba(0,0,0,0.75) !important;
    color: #ffffff !important;
    border: 1px solid rgba(255,255,255,0.16) !important;
    border-radius: 14px !important;
    padding: 14px 18px !important;
    font-family: 'Manrope', sans-serif !important;
    font-size: 1em !important;
}
.stTextInput input::placeholder { color: #6a6a6a !important; }
.stTextInput input:focus {
    border-color: rgba(255,255,255,0.45) !important;
    box-shadow: 0 0 0 3px rgba(255,255,255,0.08) !important;
}
.stTextInput label {
    font-family: 'Manrope', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.8em !important;
    color: #a8a8a8 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
}

.stAlert {
    background: rgba(0,0,0,0.65) !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
    border-radius: 14px !important;
    color: #ffffff !important;
    backdrop-filter: blur(14px);
}
[data-testid="stAlertContainer"] { background: transparent !important; }

.stCode, pre {
    background: rgba(0,0,0,0.75) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 12px !important;
    color: #ffffff !important;
}

hr {
    border: none !important;
    border-top: 1px solid rgba(255,255,255,0.1) !important;
    margin: 32px 0 !important;
}

/* ---------- ФИНАЛ ---------- */
.victory-big {
    font-family: 'Manrope', sans-serif;
    font-size: 4.5em;
    font-weight: 800;
    text-align: center;
    letter-spacing: -0.045em;
    line-height: 1;
    margin: 20px 0;
    background: linear-gradient(180deg, #ffffff 0%, #ffffff 40%, #5a5a5a 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: fadeUp 0.8s ease-out both;
}
.victory-sub {
    text-align: center;
    font-family: 'Manrope', sans-serif;
    font-weight: 400;
    color: #b0b0b0 !important;
    letter-spacing: 0.3em;
    text-transform: uppercase;
    font-size: 0.85em;
    margin-bottom: 45px;
    animation: fadeUp 0.8s 0.1s ease-out both;
}
.win-card {
    background: rgba(0,0,0,0.65);
    border: 1px solid rgba(255,255,255,0.32);
    border-radius: 20px;
    padding: 32px;
    text-align: center;
    margin: 20px 0;
    backdrop-filter: blur(16px);
    animation: fadeUp 0.6s ease-out both, glowPulse 3.5s ease-in-out infinite;
}
@keyframes glowPulse {
    0%, 100% { box-shadow: 0 0 60px rgba(255,255,255,0.08); }
    50%      { box-shadow: 0 0 100px rgba(255,255,255,0.2); }
}
.win-card h2 {
    color: #ffffff !important;
    font-size: 1.65em;
    margin: 0;
    font-weight: 700;
}

::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: #000; }
::-webkit-scrollbar-thumb {
    background: rgba(255,255,255,0.22);
    border-radius: 5px;
    border: 2px solid #000;
}
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.38); }

[data-testid="stMetric"] { display: none; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# 8 БАЗОВЫХ УРОВНЕЙ
# ============================================================

LEVELS = {
    1: {"title": "Уровень 1 — Радиостанция",
        "story": "Ты — оператор обсерватории CrossCorr. Все станции замолчали. Нужно включить радиостанцию и отправить позывной.",
        "task": "1. Создай переменную operator с твоим именем.\n2. Создай frequency = 14.074.\n3. Напечатай: \"Оператор: <имя> на частоте <частота>\"",
        "hint": "operator = \"Твоё_Имя\"\nfrequency = 14.074\nprint(\"Оператор:\", operator, \"на частоте\", frequency)",
        "check": lambda code, out: "operator" in code and "frequency" in code and "print" in code,
        "success": "Радиостанция ожила!"},
    2: {"title": "Уровень 2 — Магнитометр",
        "story": "Магнитометр показывает странные значения. Что это — буря, помехи или сигнал призрака?",
        "task": "Напиши код с if / elif / else:\n- Если field > 100 — печатай \"Магнитная буря!\"\n- Если 50 <= field <= 100 — печатай \"Норма\"\n- Если field < 50 — печатай \"Помехи\"\n\nfield = 87",
        "hint": "field = 87\nif field > 100:\n    print(\"Магнитная буря!\")\nelif field >= 50:\n    print(\"Норма\")\nelse:\n    print(\"Помехи\")",
        "check": lambda code, out: "if" in code and "elif" in code and "else" in code,
        "success": "Магнитометр откалиброван!"},
    3: {"title": "Уровень 3 — Нейтронный монитор",
        "story": "Монитор записал 10 событий. Нужно посчитать частицы.",
        "task": "Дан список:\nevents = [12, 15, 9, 22, 18, 30, 14, 11, 25, 19]\n\n1. Считай сумму через цикл for.\n2. Печатай: \"Всего частиц: <сумма>\"\n3. Печатай: \"Максимум: <max>\"",
        "hint": "events = [12, 15, 9, 22, 18, 30, 14, 11, 25, 19]\ntotal = 0\nfor e in events:\n    total = total + e\nprint(\"Всего частиц:\", total)\nprint(\"Максимум:\", max(events))",
        "check": lambda code, out: "for" in code and "total" in code,
        "success": "Частицы посчитаны!"},
    4: {"title": "Уровень 4 — Геодезия",
        "story": "Станция GPS потеряла координаты. Нужно написать функцию расстояния.",
        "task": "1. Создай словарь stations:\n- \"P1\": (55.0, 37.0)\n- \"P2\": (32.0, -110.0)\n- \"P3\": (35.0, 139.0)\n\n2. Напиши функцию distance(lat1, lon1, lat2, lon2), возвращающую ((lat1-lat2)**2 + (lon1-lon2)**2) ** 0.5\n\n3. Напечатай расстояние между P1 и P2.",
        "hint": "stations = {\"P1\": (55.0, 37.0), \"P2\": (32.0, -110.0), \"P3\": (35.0, 139.0)}\ndef distance(lat1, lon1, lat2, lon2):\n    return ((lat1-lat2)**2 + (lon1-lon2)**2) ** 0.5\nd = distance(*stations[\"P1\"], *stations[\"P2\"])\nprint(\"Расстояние P1-P2:\", round(d, 2))",
        "check": lambda code, out: "def" in code and "stations" in code,
        "success": "Станция починена!"},
    5: {"title": "Уровень 5 — Атомные часы",
        "story": "Часы рассинхронизированы. Нужно найти максимальное расхождение.",
        "task": "1. Создай список log = [3.2, 5.1, 1.8, 9.4, 2.7, 8.9, 4.3]\n2. Найди максимум через цикл for (без max).\n3. Печатай: \"Максимальное расхождение: <max> нс\"",
        "hint": "log = [3.2, 5.1, 1.8, 9.4, 2.7, 8.9, 4.3]\nmax_diff = 0\nfor x in log:\n    if x > max_diff:\n        max_diff = x\nprint(\"Максимальное расхождение:\", max_diff, \"нс\")",
        "check": lambda code, out: "for" in code and "max_diff" in code,
        "success": "Часы синхронизированы!"},
    6: {"title": "Уровень 6 — Баллистика",
        "story": "Полигон прислал данные выстрелов. Нужно найти зависимость скорости от температуры.",
        "task": "1. Создай два списка:\n- temp = [-10, 0, 10, 20, 30, 40]\n- speed = [820, 835, 850, 865, 880, 895]\n\n2. Печатай каждую пару:\n\"Температура: <t>°C → Скорость: <s> м/с\"",
        "hint": "temp = [-10, 0, 10, 20, 30, 40]\nspeed = [820, 835, 850, 865, 880, 895]\nfor i in range(len(temp)):\n    print(\"Температура:\", temp[i], \"°C → Скорость:\", speed[i], \"м/с\")",
        "check": lambda code, out: "for" in code and "temp" in code and "speed" in code,
        "success": "Баллистика обработана!"},
    7: {"title": "Уровень 7 — Кросс-корреляция",
        "story": "Все 7 фрагментов собраны! Пора запустить финальный анализ: есть ли призрак?",
        "task": "1. Создай список signals = [0.12, -0.05, 0.08, 0.15, -0.02, 0.10]\n2. Посчитай среднее: sum(signals) / len(signals)\n3. Если avg > 0.05 — печатай \"ПРИЗРАК НАЙДЕН!\"\n4. Иначе — печатай \"Сигнала нет. Но мы проверили!\"",
        "hint": "signals = [0.12, -0.05, 0.08, 0.15, -0.02, 0.10]\navg = sum(signals) / len(signals)\nprint(\"Средний сигнал:\", round(avg, 4))\nif avg > 0.05:\n    print(\"ПРИЗРАК НАЙДЕН!\")\nelse:\n    print(\"Сигнала нет. Но мы проверили!\")",
        "check": lambda code, out: "signals" in code and "if" in code,
        "success": "АНАЛИЗ ЗАВЕРШЁН!"},
    8: {"title": "Уровень 8 — ДНК",
        "story": "ДНК — это инструкция для тела. Если в ней опечатка — это мутация.",
        "task": "1. Создай список mutations = [5, 7, 3, 8, 6, 9, 4, 7, 5, 8]\n2. Посчитай среднее: avg = sum(mutations) / len(mutations)\n3. Печатай: \"Средняя частота мутаций: <avg>\"\n4. Если avg > 6 — печатай \"Мутации активны!\"\n5. Иначе — \"Мутации спокойны\"",
        "hint": "mutations = [5, 7, 3, 8, 6, 9, 4, 7, 5, 8]\navg = sum(mutations) / len(mutations)\nprint(\"Средняя частота мутаций:\", avg)\nif avg > 6:\n    print(\"Мутации активны!\")\nelse:\n    print(\"Мутации спокойны\")",
        "check": lambda code, out: "mutations" in code and "avg" in code,
        "success": "Ты открыл тайну ДНК!"},
}

# ============================================================
# ВЕТКИ
# ============================================================

BRANCHES = {
    "bio":      {"name": "Био-детектив",       "description": "ДНК, мутации, микробиом. Ищем призрака в живом."},
    "planet":   {"name": "Планета-детектив",   "description": "Сейсмика, геодезия, магнетизм. Ищем призрака в Земле."},
    "quantum":  {"name": "Квантовый детектив", "description": "Атомные часы, гравиволны, нейтрино."},
    "time":     {"name": "Хранитель времени",  "description": "Кольца деревьев, лёд, осадки."},
    "neuro":    {"name": "Нейро-детектив",     "description": "ЭЭГ, ЭКГ, сон."},
    "finance":  {"name": "Финансовый детектив","description": "Рынки, трафик, соцсети."},
    "engineer": {"name": "Инженер-детектив",   "description": "Сборка своих датчиков."},
    "creator":  {"name": "Создай свою игру",   "description": "Ты — автор. Создай свой уровень."},
}

BRANCH_LEVELS = {
    "bio": {
        1: {"title": "Био-1 — ДНК: инструкция жизни",
            "story": "Ты в лаборатории. ДНК — это инструкция для тела.",
            "task": "1. Создай gene = \"ATGCGTACG\".\n2. Найди длину через len(gene).\n3. Печатай: \"Ген: <gene>, длина: <length>\"",
            "hint": "gene = \"ATGCGTACG\"\nlength = len(gene)\nprint(\"Ген:\", gene, \"длина:\", length)",
            "check": lambda code, out: "gene" in code and "len" in code,
            "success": "Первая инструкция прочитана!"},
        2: {"title": "Био-2 — Ищем мутацию",
            "story": "Сравниваешь две ДНК: здоровую и мутировавшую.",
            "task": "1. Создай healthy = \"ATGCGTACG\" и mutated = \"ATGCGTTCG\".\n2. Пройди циклом for по индексам.\n3. Если буквы разные — печатай: \"Мутация на позиции <i>: <h> -> <m>\"",
            "hint": "healthy = \"ATGCGTACG\"\nmutated = \"ATGCGTTCG\"\nfor i in range(len(healthy)):\n    if healthy[i] != mutated[i]:\n        print(\"Мутация на позиции\", i, \":\", healthy[i], \"->\", mutated[i])",
            "check": lambda code, out: "for" in code and "if" in code and "healthy" in code,
            "success": "Мутация найдена!"},
        3: {"title": "Био-3 — Считаем мутации",
            "story": "У тебя 5 образцов ДНК. Посчитай статистику.",
            "task": "1. Создай samples = [3, 7, 2, 9, 5].\n2. Найди max(), min(), sum().\n3. Печатай: \"Максимум: <max>, Минимум: <min>, Всего: <sum>\"",
            "hint": "samples = [3, 7, 2, 9, 5]\nprint(\"Максимум:\", max(samples), \"Минимум:\", min(samples), \"Всего:\", sum(samples))",
            "check": lambda code, out: "samples" in code and "max" in code and "min" in code,
            "success": "Мутации посчитаны!"},
        4: {"title": "Био-4 — ДНК и Луна",
            "story": "Гипотеза: может ли Луна влиять на мутации?",
            "task": "1. mutations = [5, 7, 3, 8, 6]\n2. moon = [384400, 384500, 384300, 384600, 384200]\n3. Посчитай средние.\n4. Печатай оба средних.",
            "hint": "mutations = [5, 7, 3, 8, 6]\nmoon = [384400, 384500, 384300, 384600, 384200]\navg = sum(mutations) / len(mutations)\navg_moon = sum(moon) / len(moon)\nprint(\"Средняя частота мутаций:\", avg, \"среднее расстояние:\", avg_moon)",
            "check": lambda code, out: "mutations" in code and "moon" in code and "avg" in code,
            "success": "Данные готовы!"},
        5: {"title": "Био-5 — Ложная мутация",
            "story": "Финальный уровень. Это призрак или случайность?",
            "task": "1. data = [5, 7, 3, 8, 6, 4, 9, 2, 7, 5]\n2. Посчитай среднее.\n3. Если avg > 6 — печатай \"ПРИЗРАК НАЙДЕН В ДНК!\"\n4. Иначе — \"Ложная мутация\"",
            "hint": "data = [5, 7, 3, 8, 6, 4, 9, 2, 7, 5]\navg = sum(data) / len(data)\nprint(\"Среднее:\", avg)\nif avg > 6:\n    print(\"ПРИЗРАК НАЙДЕН В ДНК!\")\nelse:\n    print(\"Ложная мутация\")",
            "check": lambda code, out: "data" in code and "avg" in code and "if" in code,
            "success": "БОСС ПОБЕЖДЁН!"},
    },
    "planet": {
        1: {"title": "Планета-1 — Сеть сейсмостанций",
            "story": "Ты — геофизик. Сеть станций замолчала.",
            "task": "1. Создай stations = [\"ST1\", \"ST2\", \"ST3\", \"ST4\", \"ST5\"].\n2. Найди длину через len().\n3. Печатай: \"Станций в сети: <count>\"",
            "hint": "stations = [\"ST1\", \"ST2\", \"ST3\", \"ST4\", \"ST5\"]\nprint(\"Станций в сети:\", len(stations))",
            "check": lambda code, out: "stations" in code and "len" in code,
            "success": "Сеть станций проверена!"},
        2: {"title": "Планета-2 — Оценка магнитуды",
            "story": "Пришёл сигнал землетрясения. Оцени его силу.",
            "task": "magnitude = 5.8\n\n- Если > 7 — печатай \"Сильное\"\n- Если >= 5 — печатай \"Среднее\"\n- Иначе — \"Слабое\"",
            "hint": "magnitude = 5.8\nif magnitude > 7:\n    print(\"Сильное\")\nelif magnitude >= 5:\n    print(\"Среднее\")\nelse:\n    print(\"Слабое\")",
            "check": lambda code, out: "magnitude" in code and "if" in code and "elif" in code,
            "success": "Магнитуда оценена!"},
        3: {"title": "Планета-3 — Серия толчков",
            "story": "Станция записала серию толчков.",
            "task": "tremors = [2.1, 3.5, 1.8, 4.2, 2.9, 3.1]\n\n1. Считай сумму через for.\n2. Посчитай среднее.\n3. Печатай: \"Средняя магнитуда: <avg>\"",
            "hint": "tremors = [2.1, 3.5, 1.8, 4.2, 2.9, 3.1]\ntotal = 0\nfor t in tremors:\n    total = total + t\navg = total / len(tremors)\nprint(\"Средняя магнитуда:\", round(avg, 2))",
            "check": lambda code, out: "for" in code and "tremors" in code and "avg" in code,
            "success": "Серия обработана!"},
        4: {"title": "Планета-4 — Поиск эпицентра",
            "story": "Финальный уровень. Найди эпицентр по данным станций!",
            "task": "data = [2.0, 3.0, 5.0, 8.0, 4.0, 6.0, 3.0, 7.0]\n\n1. Посчитай среднее и максимум.\n2. Если максимум > 7 — печатай \"ЭПИЦЕНТР НАЙДЕН!\"\n3. Иначе — \"Фоновый шум\"",
            "hint": "data = [2.0, 3.0, 5.0, 8.0, 4.0, 6.0, 3.0, 7.0]\navg = sum(data) / len(data)\nprint(\"Среднее:\", avg)\nmx = max(data)\nprint(\"Максимум:\", mx)\nif mx > 7:\n    print(\"ЭПИЦЕНТР НАЙДЕН!\")\nelse:\n    print(\"Фоновый шум\")",
            "check": lambda code, out: "data" in code and "max" in code and "if" in code,
            "success": "БОСС ПОБЕЖДЁН!"},
    },
    "quantum": {
        1: {"title": "Квант-1 — Атомные часы",
            "story": "Две атомные часы показывают разное время.",
            "task": "1. clock1 = 1234567890\n2. clock2 = 1234567893\n3. Печатай разницу: \"Расхождение: <diff> нс\"",
            "hint": "clock1 = 1234567890\nclock2 = 1234567893\ndiff = abs(clock1 - clock2)\nprint(\"Расхождение:\", diff, \"нс\")",
            "check": lambda code, out: "clock1" in code and "clock2" in code and "diff" in code,
            "success": "Часы сверены!"},
        2: {"title": "Квант-2 — Тревога",
            "story": "Если расхождение больше 5 нс — это сигнал призрака.",
            "task": "diff = 7\n\n- Если diff > 5 — печатай \"ВНИМАНИЕ!\"\n- Иначе — \"Всё спокойно\"",
            "hint": "diff = 7\nif diff > 5:\n    print(\"ВНИМАНИЕ!\")\nelse:\n    print(\"Всё спокойно\")",
            "check": lambda code, out: "diff" in code and "if" in code,
            "success": "Тревога обработана!"},
        3: {"title": "Квант-3 — Гравитационные волны",
            "story": "Детектор поймал слабые колебания.",
            "task": "waves = [0.001, 0.003, 0.002, 0.005, 0.001]\n\n1. Найди максимум и минимум.\n2. Печатай: \"Максимум: <mx>, Минимум: <mn>\"",
            "hint": "waves = [0.001, 0.003, 0.002, 0.005, 0.001]\nprint(\"Максимум:\", max(waves), \"Минимум:\", min(waves))",
            "check": lambda code, out: "waves" in code and "max" in code and "min" in code,
            "success": "Волны обработаны!"},
        4: {"title": "Квант-4 — Нейтрино",
            "story": "Детектор нейтрино записал 7 событий.",
            "task": "events = [1, 0, 0, 1, 1, 0, 1]\n\n1. Посчитай сумму через for.\n2. Если сумма >= 4 — печатай \"ПРИЗРАК АКТИВЕН!\"\n3. Иначе — \"Фон\"",
            "hint": "events = [1, 0, 0, 1, 1, 0, 1]\ntotal = 0\nfor e in events:\n    total = total + e\nprint(\"Событий:\", total)\nif total >= 4:\n    print(\"ПРИЗРАК АКТИВЕН!\")\nelse:\n    print(\"Фон\")",
            "check": lambda code, out: "events" in code and "for" in code and "if" in code,
            "success": "БОСС ПОБЕЖДЁН!"},
    },
    "time": {
        1: {"title": "Время-1 — Кольца дерева",
            "story": "Спил дерева хранит историю климата.",
            "task": "1. rings = [2.5, 3.1, 4.2, 3.8, 2.9]\n2. Посчитай sum() и len().\n3. Печатай: \"Сумма: <s>, Длина: <l>\"",
            "hint": "rings = [2.5, 3.1, 4.2, 3.8, 2.9]\nprint(\"Сумма:\", sum(rings), \"Длина:\", len(rings))",
            "check": lambda code, out: "rings" in code and "sum" in code and "len" in code,
            "success": "Кольца изучены!"},
        2: {"title": "Время-2 — Ледяной керн",
            "story": "Лёд Антарктиды хранит уровни CO2.",
            "task": "co2 = [280, 290, 310, 350, 400]\n\nПройди циклом for и печатай:\n\"Уровень: <x> ppm\"",
            "hint": "co2 = [280, 290, 310, 350, 400]\nfor x in co2:\n    print(\"Уровень:\", x, \"ppm\")",
            "check": lambda code, out: "co2" in code and "for" in code,
            "success": "Керн прочитан!"},
        3: {"title": "Время-3 — Осадки за годы",
            "story": "Метеостанция собрала данные об осадках.",
            "task": "rain = [450, 520, 480, 610, 390]\n\n1. Посчитай среднее.\n2. Печатай: \"Среднее: <avg>\"",
            "hint": "rain = [450, 520, 480, 610, 390]\navg = sum(rain) / len(rain)\nprint(\"Среднее:\", avg)",
            "check": lambda code, out: "rain" in code and "avg" in code,
            "success": "Осадки посчитаны!"},
        4: {"title": "Время-4 — Тренд климата",
            "story": "Становится теплее или холоднее?",
            "task": "years = [1.0, 1.5, 2.0, 2.8, 3.5]\n\n1. Посчитай среднее.\n2. Если avg > 2 — печатай \"Потепление!\"\n3. Иначе — \"Стабильно\"",
            "hint": "years = [1.0, 1.5, 2.0, 2.8, 3.5]\navg = sum(years) / len(years)\nprint(\"Среднее:\", avg)\nif avg > 2:\n    print(\"Потепление!\")\nelse:\n    print(\"Стабильно\")",
            "check": lambda code, out: "years" in code and "avg" in code and "if" in code,
            "success": "БОСС ПОБЕЖДЁН!"},
    },
    "neuro": {
        1: {"title": "Нейро-1 — ЭЭГ-сигнал",
            "story": "ЭЭГ показывает ритмы мозга.",
            "task": "eeg = [12, 15, 11, 18, 14, 13]\n\n1. Посчитай сумму и длину.\n2. Печатай: \"Сумма: <s>, Точек: <l>\"",
            "hint": "eeg = [12, 15, 11, 18, 14, 13]\nprint(\"Сумма:\", sum(eeg), \"Точек:\", len(eeg))",
            "check": lambda code, out: "eeg" in code and "sum" in code and "len" in code,
            "success": "Сигнал получен!"},
        2: {"title": "Нейро-2 — Внимание",
            "story": "Если сигнал выше 15 — мозг в фокусе.",
            "task": "focus = 17\n\n- Если focus > 15 — печатай \"В фокусе!\"\n- Иначе — \"Отдых\"",
            "hint": "focus = 17\nif focus > 15:\n    print(\"В фокусе!\")\nelse:\n    print(\"Отдых\")",
            "check": lambda code, out: "focus" in code and "if" in code,
            "success": "Внимание проверено!"},
        3: {"title": "Нейро-3 — Спектр",
            "story": "Печатай каждый ритм из записи.",
            "task": "waves = [8, 12, 15, 10, 14]\n\nПройди циклом и печатай:\n\"Ритм: <x> Гц\"",
            "hint": "waves = [8, 12, 15, 10, 14]\nfor x in waves:\n    print(\"Ритм:\", x, \"Гц\")",
            "check": lambda code, out: "waves" in code and "for" in code,
            "success": "Спектр готов!"},
        4: {"title": "Нейро-4 — Сон или бодрствование",
            "story": "Найди максимум и оцени состояние.",
            "task": "data = [10, 14, 9, 12, 8, 11]\n\n1. Найди максимум.\n2. Если > 15 — печатай \"БОДРСТВОВАНИЕ\"\n3. Иначе — \"СОН\"",
            "hint": "data = [10, 14, 9, 12, 8, 11]\nmx = max(data)\nprint(\"Максимум:\", mx)\nif mx > 15:\n    print(\"БОДРСТВОВАНИЕ\")\nelse:\n    print(\"СОН\")",
            "check": lambda code, out: "data" in code and "max" in code and "if" in code,
            "success": "БОСС ПОБЕЖДЁН!"},
    },
    "finance": {
        1: {"title": "Финанс-1 — Курс акции",
            "story": "Ты следишь за курсом акции стартапа.",
            "task": "prices = [100, 102, 98, 105, 103]\n\n1. Посчитай sum() и len().\n2. Печатай: \"Сумма: <s>, Дней: <l>\"",
            "hint": "prices = [100, 102, 98, 105, 103]\nprint(\"Сумма:\", sum(prices), \"Дней:\", len(prices))",
            "check": lambda code, out: "prices" in code and "sum" in code and "len" in code,
            "success": "Данные загружены!"},
        2: {"title": "Финанс-2 — Скачок цены",
            "story": "Проверь, был ли большой скачок.",
            "task": "change = 7\n\n- Если change > 5 — печатай \"Рост!\"\n- Иначе — \"Спокойно\"",
            "hint": "change = 7\nif change > 5:\n    print(\"Рост!\")\nelse:\n    print(\"Спокойно\")",
            "check": lambda code, out: "change" in code and "if" in code,
            "success": "Скачок проверен!"},
        3: {"title": "Финанс-3 — Волатильность",
            "story": "Разница между макс и мин — показатель риска.",
            "task": "prices = [100, 105, 98, 110, 102]\n\nНайди максимум, минимум и их разницу.",
            "hint": "prices = [100, 105, 98, 110, 102]\nmx = max(prices)\nmn = min(prices)\nprint(\"Максимум:\", mx, \"Минимум:\", mn, \"Разница:\", mx - mn)",
            "check": lambda code, out: "prices" in code and "max" in code and "min" in code,
            "success": "Волатильность оценена!"},
        4: {"title": "Финанс-4 — Аномалия",
            "story": "Найди аномалию на рынке!",
            "task": "prices = [100, 102, 101, 150, 103, 104]\n\n1. Среднее.\n2. Максимум.\n3. Если максимум > avg * 1.3 — печатай \"АНОМАЛИЯ!\"\n4. Иначе — \"Спокойно\"",
            "hint": "prices = [100, 102, 101, 150, 103, 104]\navg = sum(prices) / len(prices)\nmx = max(prices)\nprint(\"Среднее:\", avg, \"Максимум:\", mx)\nif mx > avg * 1.3:\n    print(\"АНОМАЛИЯ!\")\nelse:\n    print(\"Спокойно\")",
            "check": lambda code, out: "prices" in code and "avg" in code and "if" in code,
            "success": "БОСС ПОБЕЖДЁН!"},
    },
    "engineer": {
        1: {"title": "Инженер-1 — Первый датчик",
            "story": "Ты собираешь свой датчик.",
            "task": "1. sensor_name = \"D-01\"\n2. sensitivity = 0.85\n3. Печатай: \"Датчик <name>, чувствительность <s>\"",
            "hint": "sensor_name = \"D-01\"\nsensitivity = 0.85\nprint(\"Датчик\", sensor_name, \"чувствительность\", sensitivity)",
            "check": lambda code, out: "sensor_name" in code and "sensitivity" in code,
            "success": "Датчик настроен!"},
        2: {"title": "Инженер-2 — Калибровка",
            "story": "Если сигнал ниже 0.5 — нужна калибровка.",
            "task": "signal = 0.42\n\n- Если signal < 0.5 — печатай \"Калибровка нужна\"\n- Иначе — \"Датчик в норме\"",
            "hint": "signal = 0.42\nif signal < 0.5:\n    print(\"Калибровка нужна\")\nelse:\n    print(\"Датчик в норме\")",
            "check": lambda code, out: "signal" in code and "if" in code,
            "success": "Калибровка проведена!"},
        3: {"title": "Инженер-3 — Массив датчиков",
            "story": "У тебя 5 датчиков.",
            "task": "readings = [0.85, 0.92, 0.78, 0.95, 0.88]\n\nНайди среднее через цикл for.",
            "hint": "readings = [0.85, 0.92, 0.78, 0.95, 0.88]\ntotal = 0\nfor r in readings:\n    total = total + r\navg = total / len(readings)\nprint(\"Средняя чувствительность:\", round(avg, 3))",
            "check": lambda code, out: "readings" in code and "for" in code and "avg" in code,
            "success": "Массив обработан!"},
        4: {"title": "Инженер-4 — Собери свой датчик",
            "story": "Создай функцию пересчёта сигнала!",
            "task": "1. Напиши функцию convert(x), возвращающую x * 100.\n2. raw = [0.1, 0.3, 0.7]\n3. Пройди циклом и печатай: \"<x> -> <convert(x)>\"",
            "hint": "def convert(x):\n    return x * 100\nraw = [0.1, 0.3, 0.7]\nfor x in raw:\n    print(x, \"->\", convert(x))",
            "check": lambda code, out: "def" in code and "convert" in code and "for" in code,
            "success": "БОСС ПОБЕЖДЁН!"},
    },
    "creator": {
        1: {"title": "Творец-1 — Создай персонажа",
            "story": "Ты — автор. Придумай героя своей игры.",
            "task": "1. hero = \"Твоё_Имя\"\n2. hp = 100\n3. Печатай: \"Герой <hero>, HP: <hp>\"",
            "hint": "hero = \"Алиса\"\nhp = 100\nprint(\"Герой\", hero, \"HP:\", hp)",
            "check": lambda code, out: "hero" in code and "hp" in code,
            "success": "Герой создан!"},
        2: {"title": "Творец-2 — Диалог",
            "story": "Герой встречает врага.",
            "task": "hp = 30\n\n- Если hp < 50 — печатай \"Герой убегает\"\n- Иначе — \"Герой сражается\"",
            "hint": "hp = 30\nif hp < 50:\n    print(\"Герой убегает\")\nelse:\n    print(\"Герой сражается\")",
            "check": lambda code, out: "hp" in code and "if" in code,
            "success": "Развилка пройдена!"},
        3: {"title": "Творец-3 — Инвентарь",
            "story": "Герой собрал предметы.",
            "task": "inventory = [\"меч\", \"щит\", \"зелье\"]\n\nПройди циклом и печатай:\n\"У героя: <item>\"",
            "hint": "inventory = [\"меч\", \"щит\", \"зелье\"]\nfor item in inventory:\n    print(\"У героя:\", item)",
            "check": lambda code, out: "inventory" in code and "for" in code,
            "success": "Инвентарь открыт!"},
        4: {"title": "Творец-4 — Свой уровень",
            "story": "Собери свою мини-игру!",
            "task": "1. room = {\"name\": \"Пещера\", \"danger\": 7}\n2. Печатай название.\n3. Если danger > 5 — \"Опасно!\", иначе \"Спокойно\"",
            "hint": "room = {\"name\": \"Пещера\", \"danger\": 7}\nprint(\"Комната:\", room[\"name\"])\nif room[\"danger\"] > 5:\n    print(\"Опасно!\")\nelse:\n    print(\"Спокойно\")",
            "check": lambda code, out: "room" in code and "if" in code,
            "success": "ТЫ — АВТОР!"},
    },
}

# ============================================================
# УТИЛИТЫ
# ============================================================

def run_code_safe(code):
    import io, contextlib
    try:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exec(code, {"__builtins__": __builtins__}, {})
        return output.getvalue(), None
    except Exception as e:
        return "", str(e)


def stat_box(label, value):
    return f'<div class="stat-box"><div class="stat-label">{label}</div><div class="stat-value">{value}</div></div>'


def card(label, body):
    body_html = body.replace("\n", "<br>")
    return f'<div class="card"><div class="card-label">{label}</div><p>{body_html}</p></div>'


# ============================================================
# ЭКРАНЫ
# ============================================================

def show_start_screen():
    st.markdown('<div class="crosscorr-logo">CROSSCORR</div>', unsafe_allow_html=True)
    st.markdown('<div class="crosscorr-tagline">signal detection systems</div>', unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align:center; margin-bottom: 50px; animation: fadeUp 0.9s 0.25s ease-out both;">
        <div style="font-size: 1.9em; font-weight: 700; color: #fff; letter-spacing: -0.025em; line-height: 1.15;">
            Охота на призрака
        </div>
        <div style="color: #a0a0a0; font-size: 0.95em; margin-top: 14px; font-weight: 400;">
            Обучающая игра по Python · 11–13 лет
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="card" style="animation-delay: 0.35s;">
        <div class="card-label">Брифинг</div>
        <p>В 2047 году учёные обнаружили <b>сенсорные узлы</b> — станции, которые ловят сигналы «частиц-призраков».</p>
        <p>Ты — <b>юный оператор CrossCorr</b>. Восстанови сеть, собери <b>8 фрагментов</b> и проведи анализ.</p>
        <p style="color:#a0a0a0 !important; font-style: italic; margin-top: 16px;">Найдёшь ли ты призрака — или докажешь, что его нет?</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        name = st.text_input(
            "Имя оператора",
            value="",
            placeholder="Введи своё имя...",
            label_visibility="visible"
        )
        if st.button("🚀   Начать охоту", use_container_width=True):
            if name.strip():
                st.session_state.name = name.strip()
                st.session_state.game_started = True
                narrator_intro(name.strip())
                st.rerun()
            else:
                st.warning("⚠️ Введи имя оператора")


def show_level():
    level = st.session_state.level
    if level > 8:
        show_victory()
        return
    data = LEVELS[level]

    st.markdown(f'<div class="level-title">{data["title"]}</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(stat_box("Уровень", f"{level} / 8"), unsafe_allow_html=True)
    with c2:
        st.markdown(stat_box("Фрагменты", f"{st.session_state.fragments} / 8"), unsafe_allow_html=True)
    with c3:
        st.markdown(stat_box("Попытки", st.session_state.attempts), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if st.session_state.get(f"spoken_{level}") != True:
        narrator_level_start(level, data["title"], data["story"][:200])
        st.session_state[f"spoken_{level}"] = True

    st.markdown(card("История", data["story"]), unsafe_allow_html=True)
    st.markdown(card("Задание", data["task"]), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**Введи код:**")
    code = st.text_area(
        "Код:",
        value=f"# Уровень {level}\n\n",
        height=220,
        key=f"code_{level}",
        label_visibility="collapsed"
    )

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        run_btn = st.button("▶️   Запустить код", use_container_width=True, key=f"run_{level}")
    with col2:
        hint_btn = st.button("💡   Подсказка", use_container_width=True, key=f"hint_{level}")
    with col3:
        skip_btn = st.button("⏭️   Пропустить", use_container_width=True, key=f"skip_{level}")

    if hint_btn:
        st.session_state.show_hint = True
    if st.session_state.show_hint:
        st.info(f"💡 **Подсказка:**\n\n```python\n{data['hint']}\n```")

    if run_btn:
        st.session_state.attempts += 1
        output, error = run_code_safe(code)
        if error:
            st.error(f"❌ **Ошибка:**\n\n`{error}`")
            st.info("💡 Не переживай! Проверь код или нажми «Подсказка».")
            narrator_error()
        else:
            st.success("✅ Код выполнен!")
            st.markdown("**Результат:**")
            st.code(output if output else "(пусто)", language="text")
            if data["check"](code, output):
                st.balloons()
                narrator_praise()
                st.markdown(
                    f'<div class="win-card">'
                    f'<h2>✓ {data["success"]}</h2>'
                    f'<p style="color:#a8a8a8; margin-top: 14px; font-size: 0.85em; letter-spacing: 0.15em; text-transform: uppercase;">+1 фрагмент</p>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                st.session_state.fragments += 1
                st.session_state.level += 1
                st.session_state.show_hint = False
                if st.button("➡️   Следующий уровень", use_container_width=True, key="next_after_win"):
                    st.rerun()
            else:
                st.warning("🤔 Почти! Проверь, всё ли сделано по заданию.")
                st.info("💡 Нажми «Подсказка», если застрял.")

    if skip_btn:
        narrator_skip()
        st.session_state.fragments += 1
        st.session_state.level += 1
        st.session_state.show_hint = False


def show_victory():
    st.balloons()

    if st.session_state.get("victory_spoken") != True:
        narrator_victory(st.session_state.name)
        st.session_state["victory_spoken"] = True

    st.markdown('<div class="victory-big">Победа</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="victory-sub">{st.session_state.name} · 8 / 8 фрагментов</div>',
        unsafe_allow_html=True
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(stat_box("Фрагменты", "8 / 8"), unsafe_allow_html=True)
    with c2:
        st.markdown(stat_box("Уровни", "8 / 8"), unsafe_allow_html=True)
    with c3:
        st.markdown(stat_box("Попытки", st.session_state.attempts), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("""
    <div class="card">
        <div class="card-label">Освоено</div>
        <p>✓ Переменные и типы &nbsp;·&nbsp; ✓ if / elif / else &nbsp;·&nbsp; ✓ Списки и циклы &nbsp;·&nbsp; ✓ Словари и функции &nbsp;·&nbsp; ✓ Анализ данных &nbsp;·&nbsp; ✓ ДНК как датчик</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="card" style="text-align:center; border-color: rgba(255,255,255,0.28);">
        <div class="card-label" style="text-align:center;">Сцена после титров</div>
        <p style="font-size:1.2em; color:#fff !important; font-weight:600; margin: 14px 0; font-style: italic;">«Ты нашёл меня. Но я — только начало.»</p>
        <p style="font-size:1.2em; color:#fff !important; font-weight:600; margin: 14px 0; font-style: italic;">«Хочешь стать Агентом CrossCorr?»</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🌟   Открыть Академию CrossCorr", use_container_width=True, key="open_academy"):
        st.session_state.show_branches = True
        st.session_state.branch = None
        st.rerun()


def show_branch_selection():
    st.markdown('<div class="crosscorr-logo" style="font-size: 2.4em;">Академия</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="crosscorr-tagline">выбери специализацию, {st.session_state.name}</div>', unsafe_allow_html=True)

    done = len(st.session_state.branches_done)
    st.markdown(
        f'<div style="text-align:center; margin-bottom: 40px;">{stat_box("Пройдено веток", f"{done} / 8")}</div>',
        unsafe_allow_html=True
    )

    if st.session_state.get("branch_select_spoken") != True:
        speak("Академия CrossCorr открыта. Выбери свою специализацию, исследователь.")
        st.session_state["branch_select_spoken"] = True

    keys = list(BRANCHES.keys())
    for row_start in range(0, len(keys), 2):
        cols = st.columns(2, gap="medium")
        for i in range(2):
            idx = row_start + i
            if idx >= len(keys):
                continue
            key = keys[idx]
            br = BRANCHES[key]
            completed = key in st.session_state.branches_done
            status_class = "done" if completed else ""
            status_text = "✓ Пройдено" if completed else "○ Доступно"

            with cols[i]:
                st.markdown(
                    f'<div class="branch-card">'
                    f'<div class="branch-name">{br["name"]}</div>'
                    f'<div class="branch-desc">{br["description"]}</div>'
                    f'<div class="branch-status {status_class}">{status_text}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                if not completed:
                    if st.button("▶️   Начать", key=f"start_{key}", use_container_width=True):
                        st.session_state.branch = key
                        st.session_state.branch_level = 1

    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        if st.button("🔄   Сбросить прогресс", use_container_width=True, key="reset_progress"):
            keep = {
                "music_vol": st.session_state.get("music_vol", 12),
                "music_muted": st.session_state.get("music_muted", False),
            }
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            for k, v in keep.items():
                st.session_state[k] = v
            st.rerun()


def show_branch_level():
    branch_key = st.session_state.branch
    branch_info = BRANCHES.get(branch_key)

    if branch_key not in BRANCH_LEVELS:
        st.warning(f"🚧 Ветка «{branch_info['name'] if branch_info else '?'}» пока в разработке.")
        if st.button("🔙 В Академию", key="back_dev"):
            st.session_state.branch = None
            st.session_state.branch_level = 1
            st.rerun()
        return

    levels = BRANCH_LEVELS[branch_key]
    total = len(levels)
    level = st.session_state.branch_level

    if level > total:
        if branch_key not in st.session_state.branches_done:
            st.session_state.branches_done.append(branch_key)
        st.balloons()
        narrator_branch_success()
        st.markdown(
            f'<div class="win-card">'
            f'<h2>✓ Ветка пройдена</h2>'
            f'<p style="color:#a8a8a8; margin-top: 14px; font-size: 0.85em; letter-spacing: 0.15em; text-transform: uppercase;">{branch_info["name"]}</p>'
            f'</div>',
            unsafe_allow_html=True
        )
        if st.button("🔙   В Академию", use_container_width=True, key="back_branch_done"):
            st.session_state.branch = None
            st.session_state.branch_level = 1
            st.rerun()
        return

    data = levels[level]

    if st.session_state.get(f"branch_intro_{branch_key}") != True:
        narrator_branch_intro(branch_info["name"])
        st.session_state[f"branch_intro_{branch_key}"] = True

    if st.session_state.get(f"branch_spoken_{branch_key}_{level}") != True:
        speak(f"Уровень {level}. {data['story'][:200]}")
        st.session_state[f"branch_spoken_{branch_key}_{level}"] = True

    st.markdown(f'<div class="level-title">{data["title"]}</div>', unsafe_allow_html=True)

    c_back, _ = st.columns([1, 3])
    with c_back:
        if st.button("🔙   В Академию", use_container_width=True, key="back_branch_top"):
            st.session_state.branch = None
            st.session_state.branch_level = 1
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(card("История", data["story"]), unsafe_allow_html=True)
    st.markdown(card("Задание", data["task"]), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**Введи код:**")
    code = st.text_area(
        "Код:",
        value=f"# {data['title']}\n\n",
        height=200,
        key=f"bcode_{branch_key}_{level}",
        label_visibility="collapsed"
    )

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        run_btn = st.button("▶️   Запустить", use_container_width=True, key=f"brun_{branch_key}_{level}")
    with col2:
        hint_btn = st.button("💡   Подсказка", use_container_width=True, key=f"bhint_{branch_key}_{level}")
    with col3:
        skip_btn = st.button("⏭️   Пропустить", use_container_width=True, key=f"bskip_{branch_key}_{level}")

    hint_key = f"bh_{branch_key}_{level}"
    if hint_btn:
        st.session_state[hint_key] = True
    if st.session_state.get(hint_key, False):
        st.info(f"💡 **Подсказка:**\n\n```python\n{data['hint']}\n```")

    if run_btn:
        output, error = run_code_safe(code)
        if error:
            st.error(f"❌ **Ошибка:**\n\n`{error}`")
            narrator_error()
        else:
            st.success("✅ Код выполнен!")
            st.markdown("**Результат:**")
            st.code(output if output else "(пусто)", language="text")
            if data["check"](code, output):
                st.balloons()
                narrator_branch_success()
                st.markdown(
                    f'<div class="win-card">'
                    f'<h2>✓ {data["success"]}</h2>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                st.session_state.branch_level += 1
                st.session_state[hint_key] = False
                if st.button("➡️   Дальше", use_container_width=True, key=f"bnext_{branch_key}_{level}"):
                    st.rerun()

    if skip_btn:
        narrator_skip()
        st.session_state.branch_level += 1


# ============================================================
# МАРШРУТИЗАЦИЯ
# ============================================================

if not st.session_state.game_started:
    show_start_screen()
elif st.session_state.branch is not None:
    show_branch_level()
elif st.session_state.get("show_branches", False):
    show_branch_selection()
else:
    show_level()
