from __future__ import annotations

import json
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import uuid4


APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "servers.json"
DEFAULT_PORT = 18888


INDEX_HTML = r"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Local AI Gateway</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0b0b10;
      --panel: #17171f;
      --panel-2: #20202a;
      --border: #30303a;
      --text: #f4f4f5;
      --muted: #a1a1aa;
      --accent: #ccc2ff;
      --danger: #fb7185;
      --ok: #34d399;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, Segoe UI, Arial, sans-serif;
    }

    button, input, select, textarea {
      font: inherit;
    }

    button {
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--panel-2);
      color: var(--text);
      padding: 9px 12px;
      cursor: pointer;
    }

    button:hover {
      border-color: var(--accent);
    }

    button.primary {
      background: var(--accent);
      color: #111018;
      border-color: var(--accent);
    }

    input, select, textarea {
      width: 100%;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: #101018;
      color: var(--text);
      padding: 10px 11px;
      outline: none;
    }

    textarea {
      min-height: 90px;
      resize: vertical;
    }

    label {
      display: block;
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 6px;
    }

    .app {
      display: grid;
      grid-template-columns: 340px minmax(0, 1fr);
      min-height: 100vh;
    }

    .sidebar {
      border-right: 1px solid var(--border);
      background: var(--panel);
      padding: 18px;
    }

    .main {
      display: flex;
      flex-direction: column;
      min-width: 0;
      height: 100vh;
    }

    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      border-bottom: 1px solid var(--border);
      padding: 14px 18px;
    }

    .title {
      font-size: 18px;
      font-weight: 600;
    }

    .hint {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.5;
    }

    .stack {
      display: grid;
      gap: 12px;
    }

    .row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }

    .server {
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 10px;
      background: #111119;
      cursor: pointer;
    }

    .server.active {
      border-color: var(--accent);
    }

    .server-name {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      font-weight: 600;
      margin-bottom: 5px;
    }

    .pill {
      border-radius: 999px;
      padding: 2px 8px;
      color: #111018;
      background: var(--accent);
      font-size: 12px;
      font-weight: 600;
      white-space: nowrap;
    }

    .messages {
      flex: 1;
      overflow: auto;
      padding: 18px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .message {
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 13px 14px;
      max-width: 880px;
      line-height: 1.55;
      white-space: pre-wrap;
    }

    .message.user {
      align-self: flex-end;
      background: #171729;
    }

    .message.assistant {
      align-self: flex-start;
      background: var(--panel);
    }

    .composer {
      border-top: 1px solid var(--border);
      padding: 14px 18px;
      display: grid;
      gap: 10px;
    }

    .actions {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      flex-wrap: wrap;
    }

    .status {
      color: var(--muted);
      font-size: 13px;
    }

    .status.ok {
      color: var(--ok);
    }

    .status.bad {
      color: var(--danger);
    }

    .spacer {
      height: 8px;
    }

    @media (max-width: 850px) {
      .app {
        grid-template-columns: 1fr;
      }

      .sidebar {
        border-right: 0;
        border-bottom: 1px solid var(--border);
      }

      .main {
        height: auto;
        min-height: 70vh;
      }
    }
  </style>
</head>
<body>
  <div class="app">
    <aside class="sidebar">
      <div class="title">Local AI Gateway</div>
      <p class="hint">Локальная морда для твоих OpenAI-compatible серверов: llama.cpp, Ollama, vLLM, LM Studio. Всё крутится на твоей машине, запросы идут только на добавленные тобой адреса.</p>

      <div class="stack">
        <div>
          <label for="serverName">Название</label>
          <input id="serverName" placeholder="Мой llama.cpp">
        </div>
        <div>
          <label for="baseUrl">Base URL</label>
          <input id="baseUrl" placeholder="http://127.0.0.1:18080/v1">
        </div>
        <div>
          <label for="apiKey">API key</label>
          <input id="apiKey" placeholder="dummy" type="password">
        </div>
        <div class="row">
          <button id="saveServer">Сохранить</button>
          <button id="testServer">Проверить</button>
        </div>
        <div id="serverStatus" class="status"></div>
      </div>

      <div class="spacer"></div>
      <div class="title" style="font-size: 15px;">Серверы</div>
      <div id="serverList" class="stack" style="margin-top: 10px;"></div>
    </aside>

    <main class="main">
      <div class="topbar">
        <div>
          <div id="activeTitle" class="title">Сервер не выбран</div>
          <div id="activeUrl" class="hint">Добавь или выбери сервер слева</div>
        </div>
        <div style="min-width: 260px;">
          <label for="model">Модель</label>
          <select id="model"></select>
        </div>
      </div>

      <section id="messages" class="messages"></section>

      <section class="composer">
        <textarea id="prompt" placeholder="Напиши сообщение. Enter — отправить, Shift+Enter — новая строка."></textarea>
        <div class="actions">
          <div class="row" style="max-width: 330px;">
            <div>
              <label for="temperature">temperature</label>
              <input id="temperature" value="0.2">
            </div>
            <div>
              <label for="maxTokens">max tokens</label>
              <input id="maxTokens" value="512">
            </div>
          </div>
          <div style="display: flex; gap: 10px; align-items: center;">
            <span id="chatStatus" class="status"></span>
            <button id="clearChat">Очистить</button>
            <button id="send" class="primary">Отправить</button>
          </div>
        </div>
      </section>
    </main>
  </div>

  <script>
    const state = {
      servers: [],
      activeId: null,
      messages: []
    };

    const els = {
      serverName: document.querySelector('#serverName'),
      baseUrl: document.querySelector('#baseUrl'),
      apiKey: document.querySelector('#apiKey'),
      saveServer: document.querySelector('#saveServer'),
      testServer: document.querySelector('#testServer'),
      serverStatus: document.querySelector('#serverStatus'),
      serverList: document.querySelector('#serverList'),
      activeTitle: document.querySelector('#activeTitle'),
      activeUrl: document.querySelector('#activeUrl'),
      model: document.querySelector('#model'),
      messages: document.querySelector('#messages'),
      prompt: document.querySelector('#prompt'),
      temperature: document.querySelector('#temperature'),
      maxTokens: document.querySelector('#maxTokens'),
      chatStatus: document.querySelector('#chatStatus'),
      clearChat: document.querySelector('#clearChat'),
      send: document.querySelector('#send')
    };

    function setStatus(el, text, kind) {
      el.textContent = text;
      el.className = 'status' + (kind ? ' ' + kind : '');
    }

    async function api(path, options = {}) {
      const res = await fetch(path, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...(options.headers || {})
        }
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Request failed');
      }
      return data;
    }

    function activeServer() {
      return state.servers.find(server => server.id === state.activeId) || null;
    }

    function renderServers() {
      els.serverList.innerHTML = '';
      if (state.servers.length === 0) {
        els.serverList.innerHTML = '<div class="hint">Пока пусто. Добавь http://127.0.0.1:18080/v1 для текущего llama.cpp.</div>';
        return;
      }

      for (const server of state.servers) {
        const item = document.createElement('div');
        item.className = 'server' + (server.id === state.activeId ? ' active' : '');
        item.innerHTML = `
          <div class="server-name">
            <span>${escapeHtml(server.name)}</span>
            ${server.id === state.activeId ? '<span class="pill">active</span>' : ''}
          </div>
          <div class="hint">${escapeHtml(server.base_url)}</div>
        `;
        item.addEventListener('click', () => selectServer(server.id));
        els.serverList.appendChild(item);
      }
    }

    function renderActive() {
      const server = activeServer();
      els.model.innerHTML = '';
      if (!server) {
        els.activeTitle.textContent = 'Сервер не выбран';
        els.activeUrl.textContent = 'Добавь или выбери сервер слева';
        return;
      }

      els.activeTitle.textContent = server.name;
      els.activeUrl.textContent = server.base_url;
      const placeholder = document.createElement('option');
      placeholder.value = '';
      placeholder.textContent = 'Загружаю модели...';
      els.model.appendChild(placeholder);
      loadModels(server.id);
    }

    function renderMessages() {
      els.messages.innerHTML = '';
      if (state.messages.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'hint';
        empty.textContent = 'Готово. Для OpenHands лучше сначала убедиться здесь, что модель реально отвечает.';
        els.messages.appendChild(empty);
        return;
      }

      for (const msg of state.messages) {
        const item = document.createElement('div');
        item.className = 'message ' + msg.role;
        item.textContent = msg.content;
        els.messages.appendChild(item);
      }
      els.messages.scrollTop = els.messages.scrollHeight;
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
    }

    async function loadConfig() {
      const data = await api('/api/config');
      state.servers = data.servers;
      state.activeId = data.active_id || (state.servers[0] && state.servers[0].id) || null;
      renderServers();
      renderActive();
      renderMessages();
    }

    async function saveServer() {
      const payload = {
        name: els.serverName.value.trim() || 'Local AI',
        base_url: els.baseUrl.value.trim(),
        api_key: els.apiKey.value || 'dummy'
      };

      if (!payload.base_url) {
        setStatus(els.serverStatus, 'Укажи Base URL', 'bad');
        return;
      }

      const data = await api('/api/servers', {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      state.servers = data.servers;
      state.activeId = data.active_id;
      setStatus(els.serverStatus, 'Сохранено локально', 'ok');
      renderServers();
      renderActive();
    }

    async function testServer() {
      const server = activeServer();
      const payload = server ? {
        base_url: server.base_url,
        api_key: server.api_key
      } : {
        base_url: els.baseUrl.value.trim(),
        api_key: els.apiKey.value || 'dummy'
      };

      if (!payload.base_url) {
        setStatus(els.serverStatus, 'Укажи Base URL или выбери сервер', 'bad');
        return;
      }

      setStatus(els.serverStatus, 'Проверяю...', '');
      try {
        const data = await api('/api/test', {
          method: 'POST',
          body: JSON.stringify(payload)
        });
        setStatus(els.serverStatus, `OK: моделей ${data.models.length}`, 'ok');
      } catch (err) {
        setStatus(els.serverStatus, err.message, 'bad');
      }
    }

    async function selectServer(id) {
      await api('/api/active-server', {
        method: 'POST',
        body: JSON.stringify({ id })
      });
      state.activeId = id;
      state.messages = [];
      renderServers();
      renderActive();
      renderMessages();
    }

    async function loadModels(serverId) {
      try {
        const data = await api(`/api/models?server_id=${encodeURIComponent(serverId)}`);
        els.model.innerHTML = '';
        for (const model of data.models) {
          const option = document.createElement('option');
          option.value = model;
          option.textContent = model;
          els.model.appendChild(option);
        }
        if (data.models.length === 0) {
          const option = document.createElement('option');
          option.value = '';
          option.textContent = 'Модели не найдены';
          els.model.appendChild(option);
        }
      } catch (err) {
        els.model.innerHTML = '';
        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'Ошибка подключения';
        els.model.appendChild(option);
        setStatus(els.chatStatus, err.message, 'bad');
      }
    }

    async function sendMessage() {
      const server = activeServer();
      const content = els.prompt.value.trim();
      if (!server) {
        setStatus(els.chatStatus, 'Выбери сервер', 'bad');
        return;
      }
      if (!els.model.value) {
        setStatus(els.chatStatus, 'Выбери модель', 'bad');
        return;
      }
      if (!content) {
        return;
      }

      state.messages.push({ role: 'user', content });
      els.prompt.value = '';
      renderMessages();
      setStatus(els.chatStatus, 'Генерирую...', '');
      els.send.disabled = true;

      try {
        const started = performance.now();
        const data = await api('/api/chat', {
          method: 'POST',
          body: JSON.stringify({
            server_id: server.id,
            model: els.model.value,
            messages: state.messages,
            temperature: Number(els.temperature.value || 0.2),
            max_tokens: Number(els.maxTokens.value || 512)
          })
        });
        state.messages.push({ role: 'assistant', content: data.content });
        renderMessages();
        setStatus(els.chatStatus, `Готово за ${((performance.now() - started) / 1000).toFixed(1)} сек`, 'ok');
      } catch (err) {
        setStatus(els.chatStatus, err.message, 'bad');
      } finally {
        els.send.disabled = false;
      }
    }

    els.saveServer.addEventListener('click', saveServer);
    els.testServer.addEventListener('click', testServer);
    els.send.addEventListener('click', sendMessage);
    els.clearChat.addEventListener('click', () => {
      state.messages = [];
      renderMessages();
      setStatus(els.chatStatus, '', '');
    });
    els.prompt.addEventListener('keydown', event => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
      }
    });

    els.serverName.value = 'llama.cpp local';
    els.baseUrl.value = 'http://127.0.0.1:18080/v1';
    els.apiKey.value = 'dummy';
    loadConfig().catch(err => setStatus(els.serverStatus, err.message, 'bad'));
  </script>
</body>
</html>
"""


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {"servers": [], "active_id": None}

    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"servers": [], "active_id": None}

    return {
        "servers": data.get("servers", []),
        "active_id": data.get("active_id"),
    }


def save_config(data: dict) -> None:
    CONFIG_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def normalize_base_url(value: str) -> str:
    base_url = value.strip().rstrip("/")
    if not base_url:
        raise ValueError("Base URL is required")
    if not base_url.startswith(("http://", "https://")):
        raise ValueError("Base URL must start with http:// or https://")
    return base_url


def request_json(url: str, method: str = "GET", body: dict | None = None, api_key: str = "dummy", timeout: int = 180) -> dict:
    data = None
    headers = {
        "Accept": "application/json",
        "User-Agent": "local-ai-gateway/1.0",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            raw = res.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        error = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{exc.code}: {error[:400]}") from exc
    except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        raise RuntimeError(f"Connection error: {exc}") from exc

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Bad JSON response: {raw[:400]}") from exc


def extract_models(data: dict) -> list[str]:
    items = data.get("data") or data.get("models") or []
    models = []
    for item in items:
        if isinstance(item, str):
            models.append(item)
        elif isinstance(item, dict):
            model = item.get("id") or item.get("model") or item.get("name")
            if model:
                models.append(str(model))
    return models


def get_server(config: dict, server_id: str) -> dict:
    for server in config["servers"]:
        if server["id"] == server_id:
            return server
    raise ValueError("Server not found")


class Handler(BaseHTTPRequestHandler):
    server_version = "LocalAIGateway/1.0"

    def do_GET(self) -> None:
        if self.path == "/" or self.path.startswith("/?"):
            self.respond_html(INDEX_HTML)
            return

        if self.path == "/api/config":
            self.respond_json(load_config())
            return

        if self.path.startswith("/api/models"):
            query = self.path.split("?", 1)[1] if "?" in self.path else ""
            params = urllib.parse.parse_qs(query)
            server_id = params.get("server_id", [""])[0]
            try:
                config = load_config()
                server = get_server(config, server_id)
                data = request_json(f"{server['base_url']}/models", api_key=server.get("api_key") or "dummy", timeout=20)
                self.respond_json({"models": extract_models(data)})
            except Exception as exc:
                self.respond_error(str(exc))
            return

        self.respond_error("Not found", status=404)

    def do_POST(self) -> None:
        try:
            payload = self.read_body()
        except Exception as exc:
            self.respond_error(str(exc))
            return

        if self.path == "/api/servers":
            try:
                config = load_config()
                server = {
                    "id": uuid4().hex,
                    "name": str(payload.get("name") or "Local AI").strip(),
                    "base_url": normalize_base_url(str(payload.get("base_url") or "")),
                    "api_key": str(payload.get("api_key") or "dummy"),
                }
                config["servers"].append(server)
                config["active_id"] = server["id"]
                save_config(config)
                self.respond_json(config)
            except Exception as exc:
                self.respond_error(str(exc))
            return

        if self.path == "/api/active-server":
            try:
                config = load_config()
                server_id = str(payload.get("id") or "")
                get_server(config, server_id)
                config["active_id"] = server_id
                save_config(config)
                self.respond_json(config)
            except Exception as exc:
                self.respond_error(str(exc))
            return

        if self.path == "/api/test":
            try:
                base_url = normalize_base_url(str(payload.get("base_url") or ""))
                api_key = str(payload.get("api_key") or "dummy")
                data = request_json(f"{base_url}/models", api_key=api_key, timeout=20)
                self.respond_json({"models": extract_models(data)})
            except Exception as exc:
                self.respond_error(str(exc))
            return

        if self.path == "/api/chat":
            try:
                config = load_config()
                server = get_server(config, str(payload.get("server_id") or ""))
                body = {
                    "model": str(payload.get("model") or ""),
                    "messages": payload.get("messages") or [],
                    "temperature": float(payload.get("temperature") or 0.2),
                    "max_tokens": int(payload.get("max_tokens") or 512),
                    "stream": False,
                }
                data = request_json(
                    f"{server['base_url']}/chat/completions",
                    method="POST",
                    body=body,
                    api_key=server.get("api_key") or "dummy",
                    timeout=300,
                )
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                self.respond_json({"content": content, "raw": data})
            except Exception as exc:
                self.respond_error(str(exc))
            return

        self.respond_error("Not found", status=404)

    def read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw) if raw else {}

    def respond_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def respond_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def respond_error(self, message: str, status: int = 400) -> None:
        self.respond_json({"error": message}, status=status)

    def log_message(self, format: str, *args: object) -> None:
        ts = time.strftime("%H:%M:%S")
        print(f"[{ts}] {self.address_string()} {format % args}")


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Local AI Gateway: http://127.0.0.1:{port}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
