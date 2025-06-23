import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Не найден токен бота в .env файле! Создайте .env и добавьте BOT_TOKEN=...")

ITEMS_PER_SEARCH = 3
PRICE_CHECK_INTERVAL = 3600  # 1 час
DB_NAME = 'ozon_bot.db'