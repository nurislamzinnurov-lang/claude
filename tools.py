"""
Clay-RU Tools Module
=====================
Автономные функции-инструменты для ИИ-агента Claygent.
Каждая функция — это "рука" конвейера, выполняющая один шаг обогащения данных.
Все функции обернуты в try-except для устойчивости цепочки.
"""

import re
import time
import json
import requests
from urllib.parse import urlparse

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}

EMAIL_REGEX = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

JUNK_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp",
    ".ico", ".bmp", ".tiff", ".pdf", ".css", ".js",
)

JUNK_PREFIXES = (
    "example@", "test@", "user@", "name@", "your-email@",
    "email@example", "noreply@example", "support@example",
)


def search_companies_ddg(query: str, max_results: int = 10) -> list:
    """
    Поиск компаний по запросу через DuckDuckGo.

    Использует open-source библиотеку duckduckgo_search для мгновенного
    получения списка компаний (название + URL сайта) по поисковому запросу.

    Args:
        query: Поисковый запрос, например "премиум отели санкт-петербург".
        max_results: Максимальное число результатов (по умолчанию 10).

    Returns:
        Список словарей вида [{"name": "...", "site": "https://..."}, ...].
        В случае ошибки возвращает пустой список.
    """
    if DDGS is None:
        return []

    results: list = []
    seen_domains: set = set()

    try:
        with DDGS() as ddgs:
            raw = list(ddgs.text(
                keywords=query,
                region="ru-ru",
                safesearch="moderate",
                max_results=max_results * 3,
            ))
    except Exception:
        try:
            with DDGS() as ddgs:
                raw = list(ddgs.text(keywords=query, max_results=max_results * 3))
        except Exception:
            return []

    for item in raw:
        try:
            href = item.get("href") or item.get("url") or ""
            title = (item.get("title") or "").strip()
            if not href or not title:
                continue

            parsed = urlparse(href)
            domain = parsed.netloc.lower().replace("www.", "")
            if not domain or domain in seen_domains:
                continue

            blacklist = (
                "wikipedia.org", "youtube.com", "facebook.com",
                "instagram.com", "vk.com", "ok.ru", "twitter.com",
                "x.com", "tripadvisor", "booking.com", "yandex.ru/maps",
                "2gis.ru", "dzen.ru", "habr.com", "pikabu.ru",
            )
            if any(b in domain for b in blacklist):
                continue

            clean_name = re.sub(r"\s*[—\-|·•].*$", "", title).strip()
            clean_name = re.sub(r"\s+", " ", clean_name)[:120]

            seen_domains.add(domain)
            results.append({
                "name": clean_name or domain,
                "site": f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme else f"https://{domain}",
            })

            if len(results) >= max_results:
                break
        except Exception:
            continue

    return results


def _is_valid_email(email: str) -> bool:
    """Внутренняя проверка валидности email — отсекает мусорные расширения и плейсхолдеры."""
    if not email or len(email) > 120:
        return False
    low = email.lower()
    if any(low.endswith(ext) for ext in JUNK_EXTENSIONS):
        return False
    if any(low.startswith(p) for p in JUNK_PREFIXES):
        return False
    if "@" not in low:
        return False
    local, _, domain = low.partition("@")
    if not local or not domain or "." not in domain:
        return False
    if any(ch in local for ch in ("/", "\\", "?", "#", "%")):
        return False
    return True


def scrape_website_emails(domain: str) -> str:
    """
    Извлечение email-адресов с сайта компании через Jina AI Reader.

    Использует паттерн open-source проекта Jina AI Reader (https://r.jina.ai/{url}),
    который возвращает чистый markdown-контент любой страницы без JS-рендеринга.
    Сканирует главную и страницу /contacts, выковыривает регуляркой все email,
    очищая мусор (.png, .jpg, .svg и т.п.).

    Args:
        domain: URL сайта компании, например "https://example.com".

    Returns:
        Строка с первым валидным email или пустая строка, если ничего не найдено.
    """
    if not domain:
        return ""

    if not domain.startswith(("http://", "https://")):
        domain = "https://" + domain

    parsed = urlparse(domain)
    base = f"{parsed.scheme}://{parsed.netloc}"

    candidate_paths = [
        base,
        base + "/contacts",
        base + "/contact",
        base + "/about",
        base + "/kontakty",
    ]

    found_emails: list = []
    seen: set = set()

    for url in candidate_paths:
        try:
            jina_url = f"https://r.jina.ai/{url}"
            resp = requests.get(jina_url, headers=HEADERS, timeout=15)
            if resp.status_code != 200 or not resp.text:
                continue
            text = resp.text
        except Exception:
            try:
                resp = requests.get(url, headers=HEADERS, timeout=10)
                if resp.status_code != 200:
                    continue
                text = resp.text
            except Exception:
                continue

        try:
            matches = EMAIL_REGEX.findall(text)
            for raw in matches:
                em = raw.strip().strip(".,;:()[]<>\"'")
                low = em.lower()
                if low in seen:
                    continue
                if not _is_valid_email(low):
                    continue
                seen.add(low)
                found_emails.append(em)
        except Exception:
            continue

        if found_emails:
            break

    if not found_emails:
        return ""

    preferred_prefixes = ("info@", "contact@", "office@", "hello@", "sales@", "reception@")
    for em in found_emails:
        if em.lower().startswith(preferred_prefixes):
            return em
    return found_emails[0]


def enrich_via_dadata(company_name: str, api_key: str) -> dict:
    """
    Обогащение данных о компании через официальный API DaData.

    Отправляет POST-запрос к https://suggestions.dadata.ru для получения
    ИНН, ФИО директора и официальной выручки компании по её названию.

    Args:
        company_name: Название компании для поиска.
        api_key: API-ключ DaData (получается на dadata.ru).

    Returns:
        Словарь {"inn": "...", "director": "...", "revenue": "..."}.
        В случае ошибки/отсутствия ключа — пустые значения.
    """
    empty = {"inn": "", "director": "", "revenue": ""}
    if not company_name or not api_key:
        return empty

    url = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/party"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Token {api_key}",
    }
    payload = {"query": company_name, "count": 1}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code != 200:
            return empty
        data = resp.json()
    except Exception:
        return empty

    try:
        suggestions = data.get("suggestions") or []
        if not suggestions:
            return empty
        first = suggestions[0]
        d = first.get("data") or {}

        inn = d.get("inn") or ""

        director = ""
        mgmt = d.get("management") or {}
        if isinstance(mgmt, dict):
            director = mgmt.get("name") or ""
        if not director:
            fio = d.get("fio") or {}
            if isinstance(fio, dict):
                parts = [fio.get("surname"), fio.get("name"), fio.get("patronymic")]
                director = " ".join(p for p in parts if p)

        revenue = ""
        finance = d.get("finance") or {}
        if isinstance(finance, dict):
            inc = finance.get("income")
            if inc is not None:
                try:
                    inc_int = int(inc)
                    if inc_int >= 1_000_000_000:
                        revenue = f"{inc_int / 1_000_000_000:.2f} млрд ₽"
                    elif inc_int >= 1_000_000:
                        revenue = f"{inc_int / 1_000_000:.2f} млн ₽"
                    elif inc_int >= 1_000:
                        revenue = f"{inc_int / 1_000:.0f} тыс ₽"
                    else:
                        revenue = f"{inc_int} ₽"
                except Exception:
                    revenue = str(inc)

        return {"inn": inn, "director": director, "revenue": revenue}
    except Exception:
        return empty
