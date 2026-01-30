# Telegram Nick Assistant

Минимальный проект: userbot (Telethon) получает все входящие сообщения во всех чатах; при ответе на ваше сообщение или при упоминании (@username / по ID) отдельный бот отправляет уведомление в указанный чат с кнопкой «Перейти к сообщению».

## Запуск

1. Установите зависимости:

   ```bash
   pip install -r requirements.txt
   ```

2. Скопируйте `.env.example` в `.env` и заполните переменные:

   ```bash
   cp .env.example .env
   ```

3. Запустите:

   ```bash
   python main.py
   ```

При первом запуске Telethon запросит номер телефона и код подтверждения; после этого сессия сохраняется в файл (имя задаётся в `SESSION_NAME`) и повторный ввод не нужен.

## Переменные окружения

| Переменная | Описание | Где взять |
|------------|----------|-----------|
| `API_ID` | ID приложения Telegram | [my.telegram.org](https://my.telegram.org) — создать приложение |
| `API_HASH` | Hash приложения Telegram | Там же |
| `BOT_TOKEN` | Токен бота для уведомлений | [@BotFather](https://t.me/BotFather) — создать бота |
| `NOTIFICATION_CHAT_ID` | Куда слать уведомления (обычно ваш user ID = личка с ботом) | Например [@userinfobot](https://t.me/userinfobot) |
| `SESSION_NAME` | Имя файла сессии userbot (без расширения) | Например `nick_assistant_session` |
| `LOG_LEVEL` | Уровень логирования (по умолчанию INFO) | Опционально |

Сессия userbot хранится в корне проекта в файле `{SESSION_NAME}.session`; этот файл не должен попадать в репозиторий (указан в `.gitignore`).

## Зависимости

- Python 3.10+
- telethon
- aiohttp
- python-dotenv

Без БД, веб-сервера и AI: один процесс, один entry point `main.py`.
