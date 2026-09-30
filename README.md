# 🌍 Travel Bot - Telegram Travel Assistant

Умный Telegram-бот для планирования путешествий с поиском билетов, отелей и ИИ-составлением маршрутов.

## ✨ Возможности

- ✈️ **Поиск авиабилетов** — прямой/обратный, многородковые, гибкие даты
- 🚂 **Поиск билетов на поезда** — РЖД, скоростные (Сапсан/Ласточка), ночные
- 🏨 **Поиск отелей и апартаментов** — с фильтрами по цене, рейтингу, удобствам
- 🗺️ **ИИ-планировщик маршрутов** — описываешь пожелания текстом, бот создаёт детальный день-за-днём план
- 👤 **Профиль пользователя** — домашний город, стиль путешествий, валюта, бюджет
- ⭐ **Избранное** — сохранение понравившихся отелей, рейсов, мест
- 📋 **История поисков** — быстрый доступ к недавним запросам
- 💾 **PostgreSQL** — все данные хранятся в надёжной внешней базе

## 🛠 Технологии

- **Python 3.11+** / **asyncio**
- **python-telegram-bot 21.x** — современный асинхронный API
- **SQLAlchemy 2.0** + **asyncpg** — асинхронная работа с PostgreSQL
- **OpenRouter** — доступ к бесплатным LLM моделям (Llama 3.1 8B Instruct)
- **Docker / docker-compose** — простое развёртывание

## 🚀 Быстрый старт

### 1. Клонирование и настройка

```bash
cd D:/вайбкодин/Long_member_VPg01
cp .env.example .env
```

### 2. Получите токены

| Токен | Где получить |
|-------|--------------|
| `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/BotFather) в Telegram |
| `OPENROUTER_API_KEY` | [OpenRouter Keys](https://openrouter.ai/keys) |

Вставьте их в файл `.env`

### 3. Запуск с Docker (рекомендуется)

```bash
# Собрать и запустить
docker-compose up --build -d

# Логи
docker-compose logs -f bot

# Остановка
docker-compose down
```

### 4. Локальный запуск (без Docker)

```bash
# Установить зависимости
pip install -r requirements.txt

# Запустить PostgreSQL (нужен установленный Postgres)
# Или используйте только БД из docker-compose:
docker-compose up -d postgres

# Запустить бота
python bot.py
```

## 📁 Структура проекта

```
Long_member_VPg01/
├── bot.py                 # Точка входа
├── config.py              # Настройки (pydantic-settings)
├── database.py            # Подключение к БД, сессии
├── models.py              # SQLAlchemy модели
├── api_clients.py         # Клиенты OpenRouter и Travel APIs
├── keyboards.py           # Клавиатуры Telegram
├── requirements.txt       # Зависимости
├── docker-compose.yml     # PostgreSQL + Bot
├── Dockerfile             # Образ бота
├── setup.sh               # Скрипт инициализации
├── .env                   # Секреты (не в git!)
├── .env.example           # Пример конфигурации
└── handlers/              # Обработчики команд
    ├── basic.py           # Старт, меню, профиль, ИИ-чат
    ├── flights.py         # Поиск авиабилетов
    ├── hotels.py          # Поиск отелей
    ├── trains.py          # Поиск поездов
    ├── itineraries.py     # Маршруты и ИИ-планировщик
    └── callbacks.py       # Inline-кнопки
```

## 🤖 Использование

### Основные команды

| Команда | Описание |
|---------|----------|
| `/start` | Начать работу, регистрация |
| `/menu` | Главное меню |
| `/help` | Справка |
| `/profile` | Профиль пользователя |
| `/trips` | Мои поездки |

### ИИ-планировщик маршрутов

Напишите боту свободным текстом:

> «Хочу поехать в Японию на 10 дней в апреле. Люблю аниме, вкусную еду и храмы. Еду один, бюджет средний. Хочу увидеть Токио, Киото и Осаку.»

Бот:
1. Проанализирует запрос
2. Составит детальный маршрут на каждый день
3. Предложит сохранить как поездку
4. Поможет найти билеты и отели

### Поиск билетов и отелей

1. Нажмите кнопку в меню (🔍 Найти билеты / 🏨 Отели / 🚂 Поезда)
2. Следуйте подсказкам: введите города, даты, пассажиров
3. Просмотрите результаты с ценами и деталями
4. Сохраните в избранное или добавьте в поездку

## 🗄️ База данных (PostgreSQL)

### Основные таблицы

| Таблица | Описание |
|---------|----------|
| `users` | Пользователи Telegram с настройками |
| `trips` | Поездки/маршруты пользователей |
| `itinerary_items` | Детали маршрута по дням |
| `bookings` | Бронирования (рейсы, отеля, поезда) |
| `search_history` | История поисков |
| `bookmarks` | Избранное |
| `conversation_context` | Контекст диалогов |

### Миграции (Alembic)

```bash
# Создать миграцию после изменений в models.py
alembic revision --autogenerate -m "description"

# Применить миграции
alembic upgrade head
```

## 🔧 Настройка моделей OpenRouter

В `.env` можно сменить модель:

```bash
# Бесплатные модели (хорошие для путешествий):
OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct:free      # Рекомендуемая
OPENROUTER_MODEL=microsoft/phi-3-mini-128k-instruct:free   # Быстрая
OPENROUTER_MODEL=google/gemma-2-9b-it:free                 # Качественная

# Платные (лучше качество):
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
OPENROUTER_MODEL=openai/gpt-4o-mini
```

Полный список: [OpenRouter Models](https://openrouter.ai/models)

## 🌐 Интеграция с реальными API

Сейчас используются **мок-данные** для демонстрации. Для продакшена подключите:

### Авиабилеты
- **Amadeus Self-Service API** — бесплатный тиер (500 запросов/мес)
- **Aviasales Travel API** — партнёрская программа
- **Skyscanner API** — по приглашению
- **Kiwi.com Tequila API** — бесплатно для аффилиатов

### Отели
- **Booking.com Affiliate API**
- **Hotels.com API** (Expedia)
- **Amadeus Hotel API**

### Поезда
- **РЖД API** — официальное API (требует регистрации)
- **Tutu.ru API** — партнёрская программа

Добавьте ключи в `.env` и обновите методы в `api_clients.py`.

## 📝 Логирование

Логи пишутся в консоль и файл `bot.log`. Уровень настраивается в `.env`:

```bash
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR
```

## 🐳 Docker команды

```bash
# Только база данных
docker-compose up -d postgres

# Полный стек
docker-compose up --build -d

# Пересобрать бота после изменений
docker-compose build bot && docker-compose up -d bot

# Очистка (удалит БД!)
docker-compose down -v

# Войти в контейнер бота
docker-compose exec bot bash

# Войти в БД
docker-compose exec postgres psql -U postgres -d travel_bot
```

## 🔒 Безопасность

- Никогда не коммитьте `.env` в git!
- Используйте разные БД для dev/prod
- Ограничьте доступ к БД фаерволом
- Регулярно обновляйте зависимости: `pip-audit`

## 🤝 Развитие

### Добавить новый тип поиска

1. Создайте `handlers/new_type.py`
2. Добавьте ConversationHandler в `bot.py`
3. Добавьте клавиатуры в `keyboards.py`
4. Добавьте API метод в `api_clients.py`
5. Зарегистрируйте callback в `callbacks.py`

### Добавить поле в профиль

1. Добавьте колонку в `models.py` (class User)
2. Создайте миграцию: `alembic revision --autogenerate -m "add field"`
3. Обновите `handlers/basic.py` (show_profile)
4. Добавьте настройку в клавиатуру профиля

## 📄 Лицензия

MIT License — используйте свободно для личных и коммерческих проектов.

## 💬 Поддержка

- Issues: [GitHub Issues](https://github.com/your-repo/issues)
- Telegram: @your_support_bot

---

**Сделано с ❤️ для удобных путешествий**