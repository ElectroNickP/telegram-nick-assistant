# Техническое задание: проект «Telegram Nick Assistant»

## 1. Цель проекта

Отдельный минимальный проект, в котором:

- **Userbot** (Telethon) работает от имени одного Telegram-аккаунта и получает все входящие сообщения во всех чатах, где этот аккаунт состоит.
- **Модуль упоминаний** обрабатывает каждое входящее сообщение и определяет: это ответ на сообщение пользователя или прямое упоминание (@username / по ID).
- **Отдельный Telegram-бот** (Bot API) отправляет уведомление в указанный чат (например, в личку пользователя) с текстом «кто, в каком чате, что написал» и **кнопкой «Перейти к сообщению»**, по которой открывается исходное сообщение в Telegram.

Итог: пользователь получает уведомления о всех упоминаниях и ответах и может одним нажатием перейти в чат к сообщению. Остальной функционал (AI, папки, база, дашборд) в этом проекте **не нужен**.

---

## 2. Как это устроено в референсном проекте (Best My Assistant)

### 2.1. Общая схема

```
[Telegram] → входящие сообщения во все чаты пользователя
       ↓
[Userbot, Telethon] — получает события NewMessage(incoming=True)
       ↓
[MentionHandler] — проверяет: reply на меня? @мой_username? mention по ID?
       ↓ если да
[NotificationBot] — отправляет сообщение в личку пользователя через Bot API
       ↓
[Пользователь] видит уведомление и кнопку «Перейти к сообщению» → открывается чат на нужном сообщении
```

### 2.2. Userbot (Telethon)

- **Назначение:** войти в Telegram от имени пользователя (не бот) и получать все входящие сообщения.
- **Где в референсе:** `userbot/client.py`.
- **Ключевое:**
  - Используются `api_id` и `api_hash` с https://my.telegram.org (приложение пользователя).
  - Сессия хранится в файле по пути `{project_root}/{session_name}` (например `userbot_session.session`). Имя сессии задаётся в конфиге.
  - При первом запуске Telethon запросит номер телефона и код — после этого сессия сохраняется и повторный ввод не нужен.
  - После `client.start()` вызывается `get_me()`; из результата берутся `my_id` и `my_username` — это «кто я» для проверки упоминаний.
  - Один процесс держит одно соединение; работает до `run_until_disconnected()`.

### 2.3. Обработка упоминаний (MentionHandler)

- **Где в референсе:** `userbot/handlers/mentions.py`.
- **Подписка на события:**  
  `events.NewMessage(incoming=True)` — только входящие сообщения (не свои), во **всех** чатах, где есть пользователь (личка, группы, каналы, где он участник).
- **Порядок проверки для каждого сообщения:**
  1. Игнорировать, если отправитель — сам пользователь (`message.sender_id == my_id`).
  2. Игнорировать сообщения без текста (`message.text` и `message.raw_text` пусты).
  3. **Ответ на моё сообщение:**  
     Если есть `message.reply_to`, загрузить сообщение-ответ (`get_reply_message()`).  
     Если `replied_msg.sender_id == my_id` → тип «ответил на ваше сообщение».
  4. **Прямое упоминание в тексте:**  
     По полю `message.entities`:
     - `MessageEntityMention` — вырезать из текста подстроку по `entity.offset` и `entity.length`, убрать `@`, сравнить с `my_username` (без учёта регистра). Совпадение → «упомянул вас».
     - `MessageEntityMentionName` — проверить `entity.user_id == my_id`. Совпадение → «упомянул вас».
- **При срабатывании:** вызывается notifier и передаётся тип упоминания, отправитель, чат, текст сообщения и ссылка на сообщение (см. ниже).

### 2.4. Notifier (отдельный бот по Bot API)

- **Где в референсе:** `notifier/bot.py`.
- **Назначение:** от имени **другого** бота (не userbot) отправить уведомление в заданный чат (например, личка пользователя).
- **Инициализация:** `NotificationBot(bot_token, chat_id)`.
  - `bot_token` — токен бота от @BotFather (отдельный бот только для уведомлений).
  - `chat_id` — куда слать (обычно Telegram user ID пользователя = личные сообщения с этим ботом).
- **Методы:**
  - `send_mention_alert(sender_name, sender_username, chat_title, message_text, message_link, mention_type)` — форматирует текст (HTML): заголовок «Вас упомянули/ответили», от кого, чат, цитата сообщения (обрезать до 500 символов, экранировать HTML), и вызывает `send_notification`.
  - `send_notification(text, message_link, parse_mode="HTML")` — отправка через `sendMessage`; если передан `message_link`, добавляется `reply_markup` с одной inline-кнопкой (текст типа «📍 Перейти к сообщению», `url = message_link`).
  - `build_message_link(chat_id, message_id, is_private)` — формирует ссылку на сообщение:
    - Личный чат: `tg://openmessage?user_id={chat_id}&message_id={message_id}`.
    - Группа/супергруппа/канал: `chat_id` отрицательный; для формата `-100XXXXXXXXXX` взять число без `-100`; ссылка: `https://t.me/c/{link_chat_id}/{message_id}`.
- **HTTP:** запросы к `https://api.telegram.org/bot{token}/{method}` (POST, JSON), через aiohttp.

### 2.5. Связка в main

- Загружается конфиг (env).
- Создаётся userbot: `create_client(api_id, api_hash, session_name)`.
- Создаётся notifier: `NotificationBot(bot_token, notification_chat_id)`.
- `await userbot.start()` (логин, получение my_id / my_username).
- Регистрируется обработчик упоминаний: `create_mention_handler(userbot, notifier)` — внутри: `MentionHandler(userbot, notifier)`, затем `handler.register()` (вешает `_on_new_message` на `events.NewMessage(incoming=True)`).
- Запуск цикла: `await userbot.run_until_disconnected()`.

Остальные части референса (БД, папка БАЗА, AI-ассистент, веб, трей) для «Telegram Nick Assistant» не используются.

---

## 3. Требования к новому проекту «Telegram Nick Assistant»

### 3.1. Функциональные

- Запуск одного процесса: userbot + модуль упоминаний.
- Уведомления о:
  - ответах на сообщения пользователя (reply);
  - прямых упоминаниях по @username и по mention-by-ID.
- Уведомление приходит в заданный чат (как правило, личка пользователя) от отдельного бота.
- В уведомлении есть кнопка «Перейти к сообщению», открывающая исходное сообщение в клиенте Telegram (нормальный интерфейс).
- Работа во **всех** чатах, где есть аккаунт userbot (без привязки к папкам/спискам чатов).
- Конфигурация через переменные окружения (или .env); свои токены и chat_id для нового проекта.

### 3.2. Нефункциональные

- Минимум зависимостей: Telethon, aiohttp, python-dotenv (и стандартная библиотека).
- Один entry point (например `main.py`), без БД, без веб-сервера, без AI.
- Логирование в stdout (уровень и формат — на усмотрение реализации).
- Сессия userbot хранится в файле в директории проекта; имя файла/сессии задаётся в конфиге.

---

## 4. Структура проекта (рекомендуемая)

```
telegram-nick-assistant/
├── .env                    # не в git; см. .env.example
├── .env.example
├── .gitignore
├── config.py               # загрузка и валидация env
├── main.py                 # точка входа: config → userbot → notifier → mention handler → run_until_disconnected
├── requirements.txt
├── README.md
├── userbot/
│   ├── __init__.py
│   └── client.py           # Telethon-клиент, my_id, my_username, start, run_until_disconnected
├── notifier/
│   ├── __init__.py
│   └── bot.py              # NotificationBot: send_mention_alert, send_notification, build_message_link
└── userbot/
    └── handlers/
        ├── __init__.py
        └── mentions.py     # MentionHandler: register на NewMessage(incoming=True), _check_mention, _send_alert
```

(Примечание: в референсе `userbot/client.py` и `userbot/handlers/mentions.py` — в новом проекте можно повторить ту же структуру.)

---

## 5. Конфигурация (env)

Обязательные переменные:

| Переменная | Описание | Пример / где взять |
|------------|----------|--------------------|
| `API_ID` | ID приложения Telegram | Целое число с https://my.telegram.org |
| `API_HASH` | Hash приложения Telegram | Строка с https://my.telegram.org |
| `BOT_TOKEN` | Токен бота для уведомлений | @BotFather → создать бота → токен |
| `NOTIFICATION_CHAT_ID` | Куда слать уведомления (user id = личка) | Число, например из @userinfobot |
| `SESSION_NAME` | Имя файла сессии userbot (без расширения) | Например `nick_assistant_session` |

Опционально:

- `LOG_LEVEL` — уровень логирования (по умолчанию INFO).

В новом проекте **не** требуются: `ASSISTANT_BOT_TOKEN`, `OPENAI_API_KEY`, `FOLDER_NAME`, `HISTORY_START_DATE`, пути к БД.

---

## 6. Зависимости (requirements.txt)

Минимальный набор:

```
telethon>=1.37.0
aiohttp>=3.9.0
python-dotenv>=1.0.0
```

Версии можно зафиксировать по аналогии с референсом.

---

## 7. Алгоритм запуска (main.py)

1. Настроить логирование.
2. Загрузить конфиг из env (через config.py); при отсутствии обязательных переменных — вывести ошибки и выйти.
3. Создать userbot: `UserbotClient(api_id, api_hash, session_name)` или фабрика `create_client(...)`.
4. Создать notifier: `NotificationBot(bot_token=config.BOT_TOKEN, chat_id=config.NOTIFICATION_CHAT_ID)`.
5. Запустить userbot: `await userbot.start()` (при первом запуске — ввод телефона/кода).
6. Зарегистрировать обработчик упоминаний: `create_mention_handler(userbot, notifier)` (внутри — подписка на `events.NewMessage(incoming=True)`).
7. Запустить цикл: `await userbot.run_until_disconnected()`.
8. При завершении (Ctrl+C / исключение) — вызвать `userbot.disconnect()` и `notifier.close()` при наличии таких методов.

Никакой инициализации БД, папок, AI, веб-сервера, трея.

---

## 8. Поведение модуля упоминаний (детально)

- **Событие:** любое входящее сообщение (`NewMessage(incoming=True)`).
- **Фильтры:** не обрабатывать сообщения от самого пользователя; не обрабатывать сообщения без текста (и без raw_text).
- **Определение «ответил на ваше сообщение»:**  
  `message.reply_to` есть → `get_reply_message()` → не None и `replied_msg.sender_id == my_id`.
- **Определение «упомянул вас»:**  
  В `message.entities`:  
  - тип `MessageEntityMention` → подстрока по offset/length, убрать `@`, сравнить с `my_username` (case-insensitive);  
  - тип `MessageEntityMentionName` → `entity.user_id == my_id`.
- **Формирование уведомления:**  
  Отправитель (имя + @username при наличии), название чата (для лички — «ЛС с …», для групп/каналов — title), тип («ответил на ваше сообщение» / «упомянул вас»), текст сообщения (обрезка и экранирование в notifier), ссылка на сообщение — через `notifier.build_message_link(chat_id, message.id, is_private)` и `notifier.send_mention_alert(...)`.
- **Ссылка на сообщение:**  
  Реализация как в референсе в `notifier/bot.py`: личка — `tg://openmessage?user_id=...&message_id=...`; группы/каналы — `https://t.me/c/{id}/{message_id}` с правильным преобразованием отрицательного chat_id.

---

## 9. Критерии приёмки

- При упоминании пользователя (по @username или по reply) в любом чате, где есть аккаунт userbot, в указанный чат (NOTIFICATION_CHAT_ID) приходит сообщение от бота BOT_TOKEN с текстом уведомления и кнопкой «Перейти к сообщению».
- По нажатию на кнопку открывается клиент Telegram и переход к этому сообщению в нужном чате.
- Проект запускается одной командой (например `python main.py`) после заполнения .env своими API_ID, API_HASH, BOT_TOKEN, NOTIFICATION_CHAT_ID, SESSION_NAME.
- В новом проекте используются **свои** токены и chat_id; референсный проект (Best My Assistant) не используется и не зависит от него.

---

## 10. Референсные файлы в текущем проекте

Для копирования/адаптации логики использовать:

- **Userbot:** `userbot/client.py` (инициализация Telethon, session path, my_id, my_username, start, run_until_disconnected).
- **Упоминания:** `userbot/handlers/mentions.py` (MentionHandler целиком: register, _on_new_message, _check_mention, _send_alert, _get_display_name, _get_chat_title, create_mention_handler).
- **Notifier:** `notifier/bot.py` (NotificationBot: _api_call, send_notification, send_mention_alert, _escape_html, build_message_link, close).
- **Конфиг:** взять за основу часть `config.py`, оставив только API_ID, API_HASH, BOT_TOKEN, NOTIFICATION_CHAT_ID, SESSION_NAME (и при необходимости LOG_LEVEL).
- **main:** за основу взять фрагмент `main.py` до и после регистрации mention_handler и `run_until_disconnected`, без БД, folder_monitor, assistant_bot, scheduler, notifier.send_notification для прогресса/стартапа при желании можно оставить один раз при старте для проверки.

Данное ТЗ достаточно для воспроизведения поведения «упоминания и ответы → уведомление с переходом к сообщению» в отдельном проекте «Telegram Nick Assistant» с другими токенами и настройками.

---

## 11. Точные ссылки на референсный проект (Best My Assistant)

Путь к репозиторию референса: корень проекта, где лежат `main.py`, `config.py`, папки `userbot/`, `notifier/`.

| Компонент | Файл | Строки / что брать |
|-----------|------|--------------------|
| Userbot client | `userbot/client.py` | Весь файл: класс `UserbotClient`, `create_client`, сессия `Path(__file__).parent.parent / session_name`, `my_id`, `my_username`, `start()`, `run_until_disconnected()`. |
| Mention handler | `userbot/handlers/mentions.py` | Весь файл: класс `MentionHandler`, `create_mention_handler`, подписка на `events.NewMessage(incoming=True)`, `_check_mention` (reply + `MessageEntityMention` + `MessageEntityMentionName`), `_send_alert`, `_get_display_name`, `_get_chat_title`. |
| Notifier | `notifier/bot.py` | Весь файл: класс `NotificationBot`, `send_mention_alert`, `send_notification`, `build_message_link`, `_escape_html`, `close`. |
| Конфиг | `config.py` | Взять только: загрузка .env, поля API_ID, API_HASH, BOT_TOKEN, NOTIFICATION_CHAT_ID, SESSION_NAME; валидация (int для API_ID и NOTIFICATION_CHAT_ID); без ASSISTANT_BOT_TOKEN, OPENAI_API_KEY, FOLDER_NAME, DATABASE_PATH. |
| Main | `main.py` | Стр. ~86–105: импорты config, create_client, NotificationBot, create_mention_handler. Стр. ~112–124: создание userbot, notifier (без database, ai_client, folder_monitor, assistant_bot, scheduler). Стр. ~167–172: userbot.start(), create_mention_handler(userbot, notifier). Стр. ~252–256: asyncio.gather(userbot.run_until_disconnected()) и в finally: notifier.close(), userbot.disconnect(). Остальное (БД, folder_monitor, assistant_bot, scheduler, collect_history) не копировать. |

### .env.example для нового проекта

```env
# Telegram API (https://my.telegram.org)
API_ID=your_api_id
API_HASH=your_api_hash

# Bot for mention notifications (@BotFather)
BOT_TOKEN=your_bot_token

# Where to send notifications (e.g. your user ID from @userinfobot)
NOTIFICATION_CHAT_ID=your_telegram_user_id

# Userbot session file name (no extension)
SESSION_NAME=nick_assistant_session
```
