# Local AI Gateway

Локальная веб-морда для OpenAI-compatible AI-серверов: `llama.cpp`, Ollama, vLLM, LM Studio и похожих.

Приложение работает на твоём ноуте и отправляет запросы только на те адреса, которые ты сам добавил в интерфейсе.

## Быстрый запуск на Windows

1. Запусти свой `llama-server`, например:

```powershell
C:\llama.cpp\llama-b9670-bin-win-cpu-x64\llama-server.exe -m "C:\models\gemma4-coding.gguf" --host 127.0.0.1 --port 18080 -t 4 -c 1024 -np 1 -b 64 -ub 64
```

2. Запусти:

```text
ai-gateway\run-windows.bat
```

3. Открой в браузере:

```text
http://127.0.0.1:18888
```

4. Добавь сервер:

```text
Название: llama.cpp local
Base URL: http://127.0.0.1:18080/v1
API key: dummy
```

5. Нажми `Проверить`, выбери модель и пиши в чат.

## Подключение своего удалённого сервера

Если модель крутится на твоём другом ПК/сервере в приватной сети:

```text
Base URL: http://IP_СЕРВЕРА:18080/v1
```

Безопаснее всего делать это через Tailscale, ZeroTier или WireGuard. Не открывай `llama-server` напрямую в интернет без авторизации и firewall.

## Где хранятся настройки

Серверы сохраняются в:

```text
ai-gateway\servers.json
```

API key хранится локально в этом файле. Для `llama.cpp` обычно достаточно `dummy`.
