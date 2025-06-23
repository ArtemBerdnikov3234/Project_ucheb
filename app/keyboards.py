from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu():
    return InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("🔍 Найти товар", callback_data="go_to_search"),
        InlineKeyboardButton("⭐ Избранное", callback_data="show_favorites"),
        InlineKeyboardButton("📊 Отслеживать цену", callback_data="track_price"),
        InlineKeyboardButton("📋 Мои отслеживания", callback_data="show_tracking")
    )

def get_search_menu():
    return InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("🔵 Только Ozon", callback_data="search_ozon"),
        InlineKeyboardButton("🍓 Только Wildberries", callback_data="search_wb"),
        InlineKeyboardButton("🏆 Найти лучшее (Ozon + WB)", callback_data="search_best"),
        InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="main_menu")
    )

def get_product_keyboard(product_url: str, store_name: str, article: str, is_favorite: bool = False):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(InlineKeyboardButton(f"🛍 Открыть в {store_name}", url=product_url))
    
    fav_text = "❤️ В избранном" if is_favorite else "⭐ В избранное"
    store_code = 'Ozon' if 'Ozon' in store_name else 'WB'
    fav_callback = f"del_fav_{article}" if is_favorite else f"add_fav_{store_code}_{article}"
    
    keyboard.add(InlineKeyboardButton(fav_text, callback_data=fav_callback))
    keyboard.add(InlineKeyboardButton("🔄 Новый поиск", callback_data="go_to_search"))
    return keyboard