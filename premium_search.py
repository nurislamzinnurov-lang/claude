import re
import time
import random
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urljoin, unquote, parse_qs
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
]

QUERIES = [
    ("официальный дилер BMW {city}", "Автодилер премиум"),
    ("официальный дилер Mercedes {city}", "Автодилер премиум"),
    ("официальный дилер Lexus {city}", "Автодилер премиум"),
    ("официальный дилер Audi {city}", "Автодилер премиум"),
    ("премиум автосалон {city}", "Автосалон"),
    ("агентство элитной недвижимости {city}", "Элитная недвижимость"),
    ("застройщик премиум класса {city}", "Застройщик"),
    ("ювелирный бутик {city}", "Ювелирный бутик"),
    ("швейцарские часы {city} бутик", "Часовой бутик"),
    ("private banking {city}", "Private banking"),
    ("премиум банк {city}", "Премиум банк"),
    ("частная клиника премиум {city}", "Премиум клиника"),
    ("платная стоматология {city}", "Стоматология"),
    ("студия дизайна интерьера премиум {city}", "Дизайн интерьера"),
    ("бутик отель {city}", "Бутик-отель"),
    ("отель 5 звезд {city}", "Отель 5*"),
    ("бизнес школа {city}", "Бизнес-школа"),
    ("организация мероприятий {city}", "Event-агентство"),
    ("интернет-магазин премиум {city}", "Премиум e-commerce"),
]

EXCLUDED_DOMAINS = (
    "2gis.", "google.", "youtube.", "vk.com", "vk.ru", "facebook.", "instagram.",
    "twitter.", "x.com", "ok.ru", "yandex.", "ya.ru", "maps.", "telegram.",
    "t.me", "wikipedia.", "tripadvisor.", "booking.", "avito.", "cian.",
    "yell.", "zoon.", "flamp.", "spr.ru", "rutube.", "dzen.", "pikabu.",
    "linkedin.", "pinterest.", "tiktok.", "wb.ru", "wildberries.", "ozon.",
    "drom.", "auto.ru", "irr.ru", "youla.", "domclick.", "n1.ru",
)

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
IMG_EXT = ("png", "jpg", "jpeg", "gif", "svg", "webp", "ico", "bmp", "tiff")
EMAIL_PRIORITY = ("marketing@", "info@", "sales@", "pr@", "director@")

CONTACT_KEYWORDS = ("контакт", "contact", "о нас", "about", "связ")


def rand_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    }


def is_valid_domain(url):
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    if not host:
        return False
    for bad in EXCLUDED_DOMAINS:
        if bad in host:
            return False
    return True


def extract_real_url(href):
    if not href:
        return None
    if href.startswith("/url?"):
        qs = parse_qs(urlparse(href).query)
        if "q" in qs:
            return qs["q"][0]
    if href.startswith("http"):
        return href
    return None


def google_search(query, max_results=20, session=None):
    sess = session or requests.Session()
    urls = []
    seen = set()
    for start in (0, 10):
        if len(urls) >= max_results:
            break
        params = {"q": query, "hl": "ru", "num": 10, "start": start}
        try:
            r = sess.get(
                "https://www.google.com/search",
                params=params,
                headers=rand_headers(),
                timeout=15,
            )
            if r.status_code != 200:
                break
        except Exception:
            break

        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            real = extract_real_url(a["href"])
            if not real:
                continue
            if not is_valid_domain(real):
                continue
            parsed = urlparse(real)
            root = f"{parsed.scheme}://{parsed.netloc}"
            if root in seen:
                continue
            seen.add(root)
            urls.append((root, a.get_text(strip=True) or parsed.netloc))
            if len(urls) >= max_results:
                break
        time.sleep(random.uniform(1.0, 2.0))
    return urls


def filter_emails(emails):
    cleaned = []
    seen = set()
    for e in emails:
        e = e.strip().strip(".,;:")
        low = e.lower()
        if low in seen:
            continue
        if any(low.endswith("." + ext) for ext in IMG_EXT):
            continue
        if any(x in low for x in ("example.", "sentry", "wixpress", "@2x", "@3x")):
            continue
        seen.add(low)
        cleaned.append(e)

    def rank(e):
        low = e.lower()
        for i, p in enumerate(EMAIL_PRIORITY):
            if low.startswith(p):
                return i
        return len(EMAIL_PRIORITY)

    cleaned.sort(key=rank)
    return cleaned


def fetch_html(url, session):
    try:
        r = session.get(url, headers=rand_headers(), timeout=12, allow_redirects=True)
        if r.status_code == 200 and r.text:
            return r.text, r.url
    except Exception:
        return None, None
    return None, None


def find_contact_links(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    links = []
    seen = set()
    base_host = urlparse(base_url).netloc
    for a in soup.find_all("a", href=True):
        text = (a.get_text() or "").lower()
        href = a["href"].lower()
        if any(k in text for k in CONTACT_KEYWORDS) or any(k in href for k in CONTACT_KEYWORDS):
            full = urljoin(base_url, a["href"])
            if urlparse(full).netloc != base_host:
                continue
            if full in seen:
                continue
            seen.add(full)
            links.append(full)
        if len(links) >= 3:
            break
    return links


def extract_title(html):
    try:
        soup = BeautifulSoup(html, "html.parser")
        if soup.title and soup.title.string:
            return soup.title.string.strip()[:150]
    except Exception:
        pass
    return ""


def scrape_site(url, category, fallback_name, session):
    html, final_url = fetch_html(url, session)
    if not html:
        return {"name": fallback_name, "category": category, "email": "", "site": url}

    name = extract_title(html) or fallback_name
    emails = EMAIL_RE.findall(html)

    if not any(e.lower().startswith(EMAIL_PRIORITY) for e in emails):
        for link in find_contact_links(html, final_url or url):
            chtml, _ = fetch_html(link, session)
            if chtml:
                emails.extend(EMAIL_RE.findall(chtml))
                if any(e.lower().startswith(EMAIL_PRIORITY) for e in emails):
                    break
            time.sleep(random.uniform(0.3, 0.8))

    emails = filter_emails(emails)
    best = emails[0] if emails else ""
    return {"name": name, "category": category, "email": best, "site": url}


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Поиск премиум-бизнесов РФ")
        self.root.geometry("950x600")

        self.results = []
        self.stop_event = threading.Event()
        self.worker_thread = None
        self.ui_queue = queue.Queue()

        self._build_ui()
        self.root.after(100, self._drain_queue)

    def _build_ui(self):
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Город:").pack(side=tk.LEFT)
        self.city_var = tk.StringVar(value="Санкт-Петербург")
        self.city_entry = ttk.Entry(top, textvariable=self.city_var, width=30)
        self.city_entry.pack(side=tk.LEFT, padx=(6, 12))

        self.start_btn = ttk.Button(top, text="Запустить поиск", command=self.start_search)
        self.start_btn.pack(side=tk.LEFT)

        self.stop_btn = ttk.Button(top, text="Остановить", command=self.stop_search, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=6)

        self.save_btn = ttk.Button(top, text="Сохранить в Excel", command=self.save_excel, state=tk.DISABLED)
        self.save_btn.pack(side=tk.LEFT, padx=6)

        cols = ("name", "category", "email", "site")
        frame = ttk.Frame(self.root, padding=(10, 0))
        frame.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(frame, columns=cols, show="headings")
        for col, title, width in zip(
            cols,
            ("Название", "Категория", "Email", "Сайт"),
            (280, 180, 200, 260),
        ):
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, anchor=tk.W)
        vsb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        bottom = ttk.Frame(self.root, padding=10)
        bottom.pack(fill=tk.X)
        self.status_var = tk.StringVar(value="Готов к работе")
        ttk.Label(bottom, textvariable=self.status_var).pack(side=tk.LEFT)
        self.progress = ttk.Progressbar(bottom, mode="determinate", length=300)
        self.progress.pack(side=tk.RIGHT)

    def _drain_queue(self):
        try:
            while True:
                fn = self.ui_queue.get_nowait()
                fn()
        except queue.Empty:
            pass
        self.root.after(100, self._drain_queue)

    def _post(self, fn):
        self.ui_queue.put(fn)

    def set_status(self, text):
        self._post(lambda: self.status_var.set(text))

    def set_progress(self, value, maximum=None):
        def upd():
            if maximum is not None:
                self.progress["maximum"] = maximum
            self.progress["value"] = value
        self._post(upd)

    def add_row(self, item):
        def upd():
            self.tree.insert("", tk.END, values=(item["name"], item["category"], item["email"], item["site"]))
        self._post(upd)

    def start_search(self):
        if self.worker_thread and self.worker_thread.is_alive():
            return
        city = self.city_var.get().strip() or "Санкт-Петербург"
        self.results.clear()
        self._post(lambda: [self.tree.delete(i) for i in self.tree.get_children()])
        self.stop_event.clear()
        self.start_btn.config(state=tk.DISABLED)
        self.save_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.worker_thread = threading.Thread(target=self._run, args=(city,), daemon=True)
        self.worker_thread.start()

    def stop_search(self):
        self.stop_event.set()
        self.set_status("Остановка...")

    def _run(self, city):
        session = requests.Session()
        all_targets = []
        self.set_status(f"Сбор ссылок по запросам ({len(QUERIES)})...")
        self.set_progress(0, len(QUERIES))

        for idx, (q_tmpl, category) in enumerate(QUERIES, 1):
            if self.stop_event.is_set():
                break
            query = q_tmpl.format(city=city)
            self.set_status(f"Google: {query}")
            try:
                urls = google_search(query, max_results=15, session=session)
            except Exception:
                urls = []
            for url, name in urls:
                all_targets.append((url, category, name))
            self.set_progress(idx)
            time.sleep(random.uniform(1.0, 2.0))

        seen = set()
        unique_targets = []
        for url, cat, name in all_targets:
            key = urlparse(url).netloc.lower().lstrip("www.")
            if key in seen:
                continue
            seen.add(key)
            unique_targets.append((url, cat, name))

        total = len(unique_targets)
        self.set_status(f"Найдено сайтов: {total}. Сканирование...")
        self.set_progress(0, max(total, 1))

        if not total:
            self._finish()
            return

        with ThreadPoolExecutor(max_workers=12) as ex:
            futures = {}
            for url, cat, name in unique_targets:
                if self.stop_event.is_set():
                    break
                s = requests.Session()
                futures[ex.submit(scrape_site, url, cat, name, s)] = (url, cat)

            done = 0
            for fut in as_completed(futures):
                if self.stop_event.is_set():
                    break
                try:
                    item = fut.result()
                except Exception:
                    item = None
                done += 1
                self.set_progress(done)
                if item:
                    self.results.append(item)
                    self.add_row(item)
                self.set_status(f"Обработано {done}/{total} (с email: {sum(1 for r in self.results if r['email'])})")

        self._finish()

    def _finish(self):
        self.results.sort(key=lambda r: (0 if r["email"] else 1, r["category"]))
        def upd():
            for i in self.tree.get_children():
                self.tree.delete(i)
            for r in self.results:
                self.tree.insert("", tk.END, values=(r["name"], r["category"], r["email"], r["site"]))
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.save_btn.config(state=tk.NORMAL if self.results else tk.DISABLED)
            with_email = sum(1 for r in self.results if r["email"])
            self.status_var.set(f"Готово. Всего: {len(self.results)}, с email: {with_email}")
        self._post(upd)

    def save_excel(self):
        if not self.results:
            messagebox.showinfo("Нет данных", "Сначала выполните поиск.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile="premium_business.xlsx",
        )
        if not path:
            return
        wb = Workbook()
        ws = wb.active
        ws.title = "Бизнесы"
        ws.append(["Название", "Категория", "Email", "Сайт"])
        for r in self.results:
            ws.append([r["name"], r["category"], r["email"], r["site"]])
        for col, width in zip("ABCD", (45, 28, 32, 45)):
            ws.column_dimensions[col].width = width
        try:
            wb.save(path)
            messagebox.showinfo("Сохранено", f"Файл сохранён:\n{path}")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))


def main():
    root = tk.Tk()
    try:
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
    except Exception:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
