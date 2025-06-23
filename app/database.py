import logging
import aiosqlite
from .config import DB_NAME

async def initialize_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS favorites (
                user_id INTEGER, product_id TEXT, name TEXT, price TEXT,
                PRIMARY KEY (user_id, product_id)
            )''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS tracking (
                user_id INTEGER, product_id TEXT, name TEXT, desired_price INTEGER,
                current_price INTEGER, last_check TEXT,
                PRIMARY KEY (user_id, product_id)
            )''')
        await db.commit()
    logging.info("База данных инициализирована.")

# Функции для избранного
async def add_favorite_to_db(user_id, product_id, name, price):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR REPLACE INTO favorites (user_id, product_id, name, price) VALUES (?, ?, ?, ?)",
            (user_id, product_id, name, f"{price} ₽")
        )
        await db.commit()

async def remove_favorite_from_db(user_id, product_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM favorites WHERE user_id = ? AND product_id = ?", (user_id, product_id))
        await db.commit()

async def get_favorites_from_db(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT product_id, name, price FROM favorites WHERE user_id = ?", (user_id,))
        return await cursor.fetchall()

async def is_favorite_in_db(user_id, product_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT 1 FROM favorites WHERE user_id = ? AND product_id = ?", (user_id, product_id))
        return await cursor.fetchone() is not None

# Функции для отслеживания
async def add_tracking_to_db(user_id, product_id, name, desired_price, current_price, last_check):
     async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR REPLACE INTO tracking (user_id, product_id, name, desired_price, current_price, last_check) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, product_id, name, desired_price, current_price, last_check)
        )
        await db.commit()

async def remove_tracking_from_db(user_id, product_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM tracking WHERE user_id = ? AND product_id = ?", (user_id, product_id))
        await db.commit()

async def get_tracking_from_db(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT product_id, name, desired_price, current_price FROM tracking WHERE user_id = ?", (user_id,))
        return await cursor.fetchall()

async def get_all_tracking_from_db():
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT user_id, product_id, name, desired_price, current_price FROM tracking")
        return await cursor.fetchall()

async def update_tracking_in_db(user_id, product_id, new_price, last_check):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE tracking SET current_price = ?, last_check = ? WHERE user_id = ? AND product_id = ?",
            (new_price, last_check, user_id, product_id)
        )
        await db.commit()