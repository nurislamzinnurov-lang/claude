"""
Clay-RU — Премиальный клон Clay.com с автономным ИИ-Скульптором (Claygent).
Локальный Streamlit-интерфейс + Ollama (llama3.1) + DuckDuckGo + Jina + DaData.
"""

import io
import json
import time
import re
import requests
import pandas as pd
import streamlit as st

from tools import (
    search_companies_ddg,
    scrape_website_emails,
    enrich_via_dadata,
)


# ──────────────────────────────────────────────────────────────────────────────
# КОНФИГУРАЦИЯ СТРАНИЦЫ
# ──────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Clay-RU · Claygent",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)


OLLAMA_URL = "http://localhost:11434"

DEFAULT_COLUMNS = ["Название", "Сайт", "Email", "Директор", "ИНН", "Выручка"]


# ──────────────────────────────────────────────────────────────────────────────
# ПРЕМИАЛЬНЫЙ CSS — ТЁМНАЯ ТЕМА A-LA CLAY.COM
# ──────────────────────────────────────────────────────────────────────────────

CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"], .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background: #0B0C10 !important;
        color: #E8ECF1 !important;
    }

    .stApp {
        background:
            radial-gradient(1200px 600px at 10% -10%, rgba(102, 252, 241, 0.06), transparent 60%),
            radial-gradient(1000px 500px at 90% 0%, rgba(168, 102, 246, 0.08), transparent 60%),
            #0B0C10 !important;
    }

    #MainMenu, footer, header { visibility: hidden; }

    .block-container {
        padding-top: 2.2rem !important;
        padding-bottom: 2rem !important;
        max-width: 1400px !important;
    }

    .clay-hero {
        text-align: center;
        margin: 0.4rem 0 1.6rem 0;
    }
    .clay-hero h1 {
        font-size: 3.0rem;
        font-weight: 800;
        letter-spacing: -0.04em;
        margin: 0;
        background: linear-gradient(135deg, #FFFFFF 0%, #66FCF1 55%, #A866F6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .clay-hero p {
        color: #9BA4B5;
        font-size: 1.02rem;
        margin-top: 0.6rem;
        letter-spacing: 0.01em;
    }
    .clay-badge {
        display: inline-block;
        padding: 4px 10px;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #66FCF1;
        background: rgba(102, 252, 241, 0.08);
        border: 1px solid rgba(102, 252, 241, 0.25);
        border-radius: 999px;
        margin-bottom: 0.8rem;
    }

    .stTextInput > div > div > input {
        background: #1F2833 !important;
        color: #FFFFFF !important;
        border: 1px solid #2C3742 !important;
        border-radius: 14px !important;
        padding: 18px 20px !important;
        font-size: 1.05rem !important;
        font-weight: 500 !important;
        box-shadow: 0 8px 28px rgba(0, 0, 0, 0.35) !important;
        transition: all 0.2s ease;
    }
    .stTextInput > div > div > input:focus {
        border-color: #66FCF1 !important;
        box-shadow: 0 0 0 3px rgba(102, 252, 241, 0.15), 0 8px 28px rgba(0, 0, 0, 0.35) !important;
    }
    .stTextInput > div > div > input::placeholder {
        color: #6B7480 !important;
        font-weight: 400 !important;
    }

    .stButton > button {
        background: linear-gradient(135deg, #66FCF1 0%, #45A29E 100%) !important;
        color: #0B0C10 !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 14px 28px !important;
        font-weight: 700 !important;
        font-size: 0.98rem !important;
        letter-spacing: 0.02em !important;
        box-shadow: 0 6px 22px rgba(102, 252, 241, 0.22) !important;
        transition: all 0.18s ease;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 10px 30px rgba(102, 252, 241, 0.35) !important;
    }
    .stButton > button:active { transform: translateY(0); }

    .stDownloadButton > button {
        background: #1F2833 !important;
        color: #66FCF1 !important;
        border: 1px solid #2C3742 !important;
        border-radius: 12px !important;
        padding: 12px 22px !important;
        font-weight: 600 !important;
    }
    .stDownloadButton > button:hover {
        border-color: #66FCF1 !important;
        background: #243341 !important;
    }

    [data-testid="stSidebar"] {
        background: #0E1116 !important;
        border-right: 1px solid #1A1F27;
    }
    [data-testid="stSidebar"] * { color: #C5CCD6 !important; }
    [data-testid="stSidebar"] .stTextInput > div > div > input,
    [data-testid="stSidebar"] .stSelectbox > div > div {
        background: #161B22 !important;
        border: 1px solid #232A33 !important;
        border-radius: 10px !important;
        color: #FFFFFF !important;
    }

    [data-testid="stDataFrame"], [data-testid="stDataEditor"] {
        background: #1F2833 !important;
        border-radius: 16px !important;
        border: 1px solid #2A3340 !important;
        overflow: hidden;
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
    }
    [data-testid="stDataFrame"] *, [data-testid="stDataEditor"] * {
        font-family: 'Inter', sans-serif !important;
    }

    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #66FCF1, #A866F6) !important;
    }
    .stProgress > div > div > div {
        background: #1F2833 !important;
        border-radius: 999px !important;
    }

    .clay-status {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 12px 16px;
        background: rgba(31, 40, 51, 0.7);
        border: 1px solid #2A3340;
        border-radius: 12px;
        font-size: 0.92rem;
        color: #C5CCD6;
        margin: 0.6rem 0;
    }
    .clay-dot {
        width: 8px; height: 8px; border-radius: 50%;
        background: #66FCF1;
        box-shadow: 0 0 12px #66FCF1;
        animation: pulse 1.4s infinite ease-in-out;
    }
    @keyframes pulse {
        0%, 100% { opacity: 0.4; transform: scale(0.9); }
        50% { opacity: 1; transform: scale(1.1); }
    }

    .stAlert {
        background: #1F2833 !important;
        border: 1px solid #2A3340 !important;
        border-radius: 12px !important;
        color: #E8ECF1 !important;
    }

    hr { border-color: #1A1F27 !important; }
    .stMarkdown, .stMarkdown p { color: #C5CCD6; }
    label, .stSelectbox label { color: #9BA4B5 !important; font-size: 0.85rem !important; }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# СОСТОЯНИЕ СЕССИИ
# ──────────────────────────────────────────────────────────────────────────────

if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=DEFAULT_COLUMNS)
if "agent_log" not in st.session_state:
    st.session_state.agent_log = []
if "running" not in st.session_state:
    st.session_state.running = False


# ──────────────────────────────────────────────────────────────────────────────
# SIDEBAR — НАСТРОЙКИ
# ──────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ◆ Claygent")
    st.markdown("<p style='color:#6B7480;font-size:0.82rem;margin-top:-8px;'>Локальный ИИ-скульптор данных</p>", unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("#### Модель Ollama")
    available_models = ["llama3.1", "llama3.1:8b", "llama3.1:70b", "llama3.2", "qwen2.5", "mistral"]
    ollama_model = st.selectbox(
        "Выберите модель",
        options=available_models,
        index=0,
        label_visibility="collapsed",
    )

    st.markdown("#### DaData токен")
    dadata_token = st.text_input(
        "Токен",
        type="password",
        placeholder="Введите API-ключ DaData",
        label_visibility="collapsed",
    )

    st.markdown("#### Лимит результатов")
    max_results = st.slider("Компаний", min_value=3, max_value=25, value=10, label_visibility="collapsed")

    st.markdown("---")
    st.markdown("<p style='color:#6B7480;font-size:0.78rem;'>Ollama: <code>http://localhost:11434</code></p>", unsafe_allow_html=True)

    if st.button("🗑 Очистить таблицу", use_container_width=True):
        st.session_state.df = pd.DataFrame(columns=DEFAULT_COLUMNS)
        st.session_state.agent_log = []
        st.rerun()


# ──────────────────────────────────────────────────────────────────────────────
# OLLAMA — JSON-РОБАСТНЫЙ ВЫЗОВ
# ──────────────────────────────────────────────────────────────────────────────

def call_ollama(prompt: str, model: str, system: str = "") -> str:
    """Запрос к локальной Ollama. Возвращает текст ответа или пустую строку."""
    payload = {
        "model": model,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 512},
    }
    try:
        resp = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=60)
        if resp.status_code != 200:
            return ""
        data = resp.json()
        return (data.get("response") or "").strip()
    except Exception:
        return ""


def extract_json(text: str) -> dict:
    """Железобетонное извлечение JSON-объекта из ответа LLM."""
    if not text:
        return {}
    cleaned = text.strip()

    fence_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", cleaned, re.IGNORECASE)
    if fence_match:
        cleaned = fence_match.group(1)

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}

    candidate = cleaned[start:end + 1]
    try:
        return json.loads(candidate)
    except Exception:
        pass

    repaired = candidate.replace("'", '"')
    repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
    try:
        return json.loads(repaired)
    except Exception:
        return {}


AGENT_SYSTEM_PROMPT = (
    "Ты — Claygent, автономный ИИ-агент по обогащению данных о компаниях. "
    "Тебе доступен один инструмент: search_companies_ddg(query, max_results). "
    "Твоя задача — преобразовать запрос пользователя на естественном языке в JSON-команду "
    "для вызова поиска компаний. "
    "ВАЖНО: отвечай ТОЛЬКО валидным JSON-объектом без пояснений, без markdown, без префиксов. "
    "Формат строго:\n"
    '{"tool": "search_companies_ddg", "query": "<оптимизированная поисковая строка на русском>", "max_results": <число>}\n'
    "Если запрос пользователя содержит число — используй его как max_results, иначе ставь 10. "
    "Поисковую строку формулируй кратко и предметно, добавляя слова 'официальный сайт' если уместно."
)


def plan_search(user_query: str, model: str, default_limit: int) -> dict:
    """ИИ преобразует запрос пользователя в JSON-команду на вызов инструмента."""
    raw = call_ollama(user_query, model=model, system=AGENT_SYSTEM_PROMPT)
    parsed = extract_json(raw)

    query = parsed.get("query") if isinstance(parsed, dict) else None
    limit = parsed.get("max_results") if isinstance(parsed, dict) else None

    if not query or not isinstance(query, str):
        query = user_query

    try:
        limit = int(limit) if limit is not None else default_limit
    except Exception:
        limit = default_limit
    limit = max(1, min(limit, default_limit))

    return {"tool": "search_companies_ddg", "query": query.strip(), "max_results": limit}


# ──────────────────────────────────────────────────────────────────────────────
# ИНТЕРФЕЙС — HERO + ПОИСКОВАЯ СТРОКА
# ──────────────────────────────────────────────────────────────────────────────

st.markdown(
    """
    <div class="clay-hero">
        <span class="clay-badge">◆ Clay-RU · v1.0</span>
        <h1>Claygent</h1>
        <p>Автономный ИИ-скульптор данных. Один запрос — готовая таблица обогащённых компаний.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

col_input, col_btn = st.columns([6, 1])
with col_input:
    user_query = st.text_input(
        "query",
        placeholder="Спросите Claygent... (например: найди мне 10 премиум отелей в санкт петербурге)",
        label_visibility="collapsed",
        key="user_query_input",
    )
with col_btn:
    run_clicked = st.button("Run Agent ▸", use_container_width=True)


# ──────────────────────────────────────────────────────────────────────────────
# ОБЛАСТИ ДЛЯ ДИНАМИЧЕСКИХ ОБНОВЛЕНИЙ
# ──────────────────────────────────────────────────────────────────────────────

status_slot = st.empty()
progress_slot = st.empty()
table_slot = st.empty()


def render_table(df: pd.DataFrame):
    """Рендер премиальной таблицы Clay через st.data_editor."""
    with table_slot.container():
        st.data_editor(
            df,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            disabled=False,
            column_config={
                "Название": st.column_config.TextColumn("Название", width="large"),
                "Сайт": st.column_config.LinkColumn("Сайт", width="medium"),
                "Email": st.column_config.TextColumn("Email", width="medium"),
                "Директор": st.column_config.TextColumn("Директор", width="medium"),
                "ИНН": st.column_config.TextColumn("ИНН", width="small"),
                "Выручка": st.column_config.TextColumn("Выручка", width="small"),
            },
            key=f"editor_{len(df)}_{int(time.time() * 1000) % 1_000_000}",
        )


def set_status(msg: str, active: bool = True):
    icon = '<span class="clay-dot"></span>' if active else "◆"
    status_slot.markdown(
        f'<div class="clay-status">{icon}<span>{msg}</span></div>',
        unsafe_allow_html=True,
    )


# ──────────────────────────────────────────────────────────────────────────────
# ЗАПУСК ЦИКЛА АГЕНТА (Reasoning + Acting)
# ──────────────────────────────────────────────────────────────────────────────

if run_clicked and user_query.strip():
    st.session_state.running = True
    st.session_state.df = pd.DataFrame(columns=DEFAULT_COLUMNS)

    # ── Шаг 1: ИИ планирует поиск ────────────────────────────────────────────
    set_status("Claygent анализирует запрос и формирует JSON-команду...")
    progress_slot.progress(0.05)
    plan = plan_search(user_query.strip(), model=ollama_model, default_limit=max_results)

    set_status(f"Запуск инструмента: search_companies_ddg('{plan['query']}', max_results={plan['max_results']})")
    progress_slot.progress(0.15)

    # ── Шаг 2: Поиск компаний через DuckDuckGo ───────────────────────────────
    companies = search_companies_ddg(plan["query"], max_results=plan["max_results"])

    if not companies:
        progress_slot.empty()
        status_slot.empty()
        st.warning("Claygent не нашёл компаний по этому запросу. Попробуйте переформулировать.")
        st.session_state.running = False
    else:
        rows = [
            {"Название": c["name"], "Сайт": c["site"], "Email": "", "Директор": "", "ИНН": "", "Выручка": ""}
            for c in companies
        ]
        st.session_state.df = pd.DataFrame(rows, columns=DEFAULT_COLUMNS)
        render_table(st.session_state.df)
        set_status(f"Найдено компаний: {len(companies)}. Запускаю обогащение по каждой строке...")
        progress_slot.progress(0.25)

        total = len(companies)

        # ── Шаг 3: Обогащение каждой строки по очереди ───────────────────────
        for idx, comp in enumerate(companies):
            name = comp["name"]
            site = comp["site"]

            # 3a. scrape emails
            set_status(f"[{idx + 1}/{total}] scrape_website_emails → {site}")
            email = scrape_website_emails(site)
            st.session_state.df.at[idx, "Email"] = email or "—"
            render_table(st.session_state.df)
            progress_slot.progress(0.25 + (idx + 0.5) / total * 0.75)

            # 3b. enrich via DaData
            set_status(f"[{idx + 1}/{total}] enrich_via_dadata → {name}")
            enriched = enrich_via_dadata(name, dadata_token)
            st.session_state.df.at[idx, "ИНН"] = enriched.get("inn") or "—"
            st.session_state.df.at[idx, "Директор"] = enriched.get("director") or "—"
            st.session_state.df.at[idx, "Выручка"] = enriched.get("revenue") or "—"
            render_table(st.session_state.df)
            progress_slot.progress(0.25 + (idx + 1) / total * 0.75)

        progress_slot.progress(1.0)
        set_status(f"✓ Скульптура завершена. Обогащено {total} компаний.", active=False)
        st.session_state.running = False
        time.sleep(0.4)
        progress_slot.empty()


# ──────────────────────────────────────────────────────────────────────────────
# ОТРИСОВКА ТАБЛИЦЫ + ЭКСПОРТ
# ──────────────────────────────────────────────────────────────────────────────

if st.session_state.df.empty and not st.session_state.running:
    empty_df = pd.DataFrame(
        [{col: "" for col in DEFAULT_COLUMNS} for _ in range(5)],
        columns=DEFAULT_COLUMNS,
    )
    render_table(empty_df)
else:
    render_table(st.session_state.df)


if not st.session_state.df.empty and not st.session_state.running:
    buffer = io.BytesIO()
    try:
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            st.session_state.df.to_excel(writer, index=False, sheet_name="Claygent")
        buffer.seek(0)
        st.markdown("<br>", unsafe_allow_html=True)
        col_a, col_b, col_c = st.columns([2, 1, 2])
        with col_b:
            st.download_button(
                label="📥 Export to Excel",
                data=buffer,
                file_name=f"clay_ru_{int(time.time())}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
    except Exception as exc:
        st.error(f"Ошибка экспорта: {exc}")


st.markdown(
    "<div style='text-align:center;color:#4A5260;font-size:0.78rem;margin-top:2.4rem;letter-spacing:0.08em;'>"
    "CLAY-RU · POWERED BY OLLAMA · LOCAL & PRIVATE"
    "</div>",
    unsafe_allow_html=True,
)
