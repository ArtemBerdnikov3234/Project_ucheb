# Ozon & Wildberries Tracker Bot

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![aiogram 2.25.1](https://img.shields.io/badge/aiogram-2.25.1-green.svg)](https://docs.aiogram.dev/en/v2.25.1/)
[![Selenium 4.x](https://img.shields.io/badge/Selenium-4.x-orange.svg)](https://www.selenium.dev/documentation/)
[![License MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Мощный Telegram-бот для удобного шопинга на Ozon и Wildberries. Находит лучшие предложения, отслеживает цены и сохраняет избранные товары.

## ✨ Основные возможности

- **Поиск на двух платформах**:
  - Ищите товары на Ozon или Wildberries отдельно.
  - Функция "🏆 Найти лучшее" сравнивает предложения с обеих платформ и выдаёт топ-5 по умному алгоритму.

- **Умная оценка товаров**:
  - Учитывает цену, рейтинг (1–5), количество отзывов и покупок (для Wildberries).

- **Отслеживание цен (только Ozon)**:
  - Укажите желаемую цену для товара.
  - Бот проверяет цену ежедневно (интервал настраивается) и уведомляет, если она достигла или ниже заданной.

- **Избранное (только Ozon)**:
  - Сохраняйте товары в личный список для быстрого доступа.

## 🛠️ Технологии

| Компонент         | Технология       | Назначение                                                     |
|-------------------|------------------|----------------------------------------------------------------|
| Telegram Bot      | aiogram 2.x      | Асинхронное взаимодействие с Telegram API                      |
| Парсинг Ozon      | Selenium         | Обход защиты Ozon (Cloudflare, JS) через автоматизацию браузера |
| Парсинг Wildberries | aiohttp        | Быстрый доступ к публичному API Wildberries                    |
| База данных       | SQLite (aiosqlite) | Хранение избранного и отслеживаемых товаров                  |
| Асинхронность     | asyncio          | Эффективное выполнение операций                              |
| Конфигурация      | .env             | Безопасное хранение токена бота                              |

### Архитектурные особенности
- **Модульность**: Логика разделена на слои (обработчики, сервисы, база данных, клавиатуры, конфигурация) для удобства поддержки.
- **Стабильность парсинга**: Используется `asyncio.Semaphore(1)` для синхронизации доступа к Selenium, предотвращая ошибки.

## ⚙️ Установка и запуск

### Требования
- Python 3.10+.
- Google Chrome (последняя версия).
- [ChromeDriver](https://chromedriver.chromium.org/downloads) (соответствующий версии Chrome). Поместите его в корень проекта.

### Инструкция
1. **Клонируйте репозиторий**:
   ```bash
   git clone https://your-repository-link.git
   cd tracker_bot
   ```

2. **Создайте виртуальное окружение**:
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Установите зависимости**:
   ```bash
   python -m pip install -r requirements.txt
   ```

4. **Настройте конфигурацию**:
   - Создайте файл `.env` в корне проекта.
   - Добавьте токен от @BotFather:
     ```env
     BOT_TOKEN="....."
     ```

5. **Запустите бота**:
   ```bash
   python -m app.bot
   ```
   Для остановки используйте `Ctrl + C`.

## 📂 Структура проекта

```
/tracker_bot/
├── .env                # Токен бота
├── requirements.txt    # Зависимости
├── README.md          # Документация
├── app/               # Исходный код
│   ├── __init__.py    # Пакет
│   ├── bot.py         # Точка входа
│   ├── config.py      # Конфигурация
│   ├── database.py    # Работа с SQLite
│   ├── keyboards.py   # Inline-клавиатуры
│   ├── handlers/      # Обработчики команд
│   │   ├── __init__.py
│   │   ├── common.py  # Общие команды (/start, меню)
│   │   └── actions.py # Действия пользователя
│   └── services/      # Бизнес-логика
│       ├── __init__.py
│       ├── ozon_parser.py      # Парсинг Ozon
│       └── wildberries_parser.py # Парсинг Wildberries
└── ozon_bot.db        # База данных (создаётся автоматически)
```

## 📝 Планы развития
- Постраничная навигация для результатов поиска.
- Кэширование популярных запросов.
- Переход на RedisStorage для сохранения состояний.
- Выбор города для точных цен и наличия.