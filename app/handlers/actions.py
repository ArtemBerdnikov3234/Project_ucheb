import asyncio
import logging
import math
from datetime import datetime

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.keyboards import get_product_keyboard, get_main_menu, get_search_menu
from app.services.ozon_parser import OzonParser
from app.services.wildberries_parser import WildberriesParser
from app import database as db
from app.config import ITEMS_PER_SEARCH

class UserStates(StatesGroup):
    search_query = State()
    track_price_article = State()
    track_price_amount = State()

async def _send_product_card(message: types.Message, product_data: dict, rank: int = None):
    is_favorite = await db.is_favorite_in_db(message.from_user.id, str(product_data['article']))
    rank_text = f"🏆 <b>Топ #{rank}</b>\n" if rank else ""
    store_text = f"Магазин: {product_data['store']}\n\n"
    text = f"{rank_text}<b>{product_data['name']}</b>\n{store_text}"

    price = product_data.get('price')
    price_card = product_data.get('price_with_card')

    if price and price > 0:
        if price_card and price_card > price:
            card_price_text = "Цена с Ozon картой:" if product_data['store'] == "🔵 Ozon" else "Цена без скидки:"
            text += f"💰 {card_price_text} {int(price)} ₽\n"
            text += f"💳 Обычная цена: {int(price_card)} ₽\n"
        else:
            text += f"💰 Цена: {int(price)} ₽\n"
    else: text += "Нет в наличии\n"

    rating = product_data.get('rating', 0)
    reviews_count = product_data.get('reviews_count', 0)
    if rating > 0 and reviews_count > 0: text += f"⭐️ {rating} • {reviews_count:,} отзывов\n".replace(",", " ")
    elif reviews_count > 0: text += f"⭐️ {reviews_count:,} отзывов\n".replace(",", " ")

    purchases = product_data.get('purchases_count', 0)
    if purchases > 0: text += f"📈 Покупок: >{purchases:,}".replace(",", " ")

    store_name_for_kb = product_data['store'].replace(' ', '').replace('🔵', '').replace('🍓', '')
    if product_data.get('image_url'):
        try:
            await message.answer_photo(
                product_data['image_url'], caption=text.strip(),
                reply_markup=get_product_keyboard(
                    product_data['url'], store_name_for_kb, str(product_data['article']), is_favorite
                ))
        except Exception:
            await message.answer(
                text.strip(), reply_markup=get_product_keyboard(
                    product_data['url'], store_name_for_kb, str(product_data['article']), is_favorite
                ))
    else:
        await message.answer(
            text.strip(), reply_markup=get_product_keyboard(
                product_data['url'], store_name_for_kb, str(product_data['article']), is_favorite
            ))

def _calculate_score(product: dict) -> float:
    price = product.get('price', 0)
    reviews = product.get('reviews_count', 0)
    purchases = product.get('purchases_count', 0)
    rating = product.get('rating', 0)
    if price == 0: return 0
    w_price, w_reviews, w_purchases, w_rating = 0.4, 0.2, 0.1, 0.3
    price_score = 1000 / price
    reviews_score = math.log(reviews + 1)
    purchases_score = math.log(purchases + 1)
    rating_score = rating * 10
    return (price_score*w_price) + (reviews_score*w_reviews) + (purchases_score*w_purchases) + (rating_score*w_rating)

async def go_to_search(callback: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await callback.message.edit_text("Выберите, где будем искать товары:", reply_markup=get_search_menu())
    await callback.answer()

async def start_search(callback: types.CallbackQuery, state: FSMContext):
    store = callback.data.split('_')[-1]
    await state.update_data(store=store)
    await state.set_state(UserStates.search_query)
    store_name_map = {'ozon': 'Ozon', 'wb': 'Wildberries', 'best': 'Ozon и Wildberries'}
    await callback.message.edit_text(f"🔍 Введите название товара для поиска в <b>{store_name_map.get(store, '')}</b>:")
    await callback.answer()

async def handle_search_query(message: types.Message, state: FSMContext, ozon_parser: OzonParser, wb_parser: WildberriesParser):
    user_data = await state.get_data()
    store = user_data.get('store')
    await state.finish()
    status_msg = await message.answer(f"Ищу \"{message.text}\"...")
    try:
        if store == 'best':
            await status_msg.edit_text("Ищу товары на Ozon и WB... Это может занять до минуты.")
           
            ozon_articles_task = ozon_parser.search_and_get_articles(message.text, count=20)
            wb_products_task = wb_parser.search_products(message.text, count=20)
            ozon_articles, wb_products = await asyncio.gather(ozon_articles_task, wb_products_task)
            
           
            ozon_products_tasks = [ozon_parser.get_product_data(article) for article in ozon_articles]
            ozon_results = await asyncio.gather(*ozon_products_tasks)
            ozon_products = [p for p in ozon_results if p]

            all_products = ozon_products + wb_products
            if not all_products:
                await status_msg.edit_text("😕 Ничего не найдено ни в одном магазине.", reply_markup=get_main_menu())
                return
            
            for p in all_products: p['score'] = _calculate_score(p)
            sorted_products = sorted(all_products, key=lambda p: p['score'], reverse=True)
            
            await status_msg.edit_text("🏆 <b>Топ-5 лучших товаров по цене и популярности:</b>")
            for i, product in enumerate(sorted_products[:5], 1):
                await _send_product_card(message, product, rank=i)
        
        
        else:
            products = []
            if store == 'ozon':
                
                articles = await ozon_parser.search_and_get_articles(message.text, count=ITEMS_PER_SEARCH)
                if articles:
                   
                    tasks = [ozon_parser.get_product_data(article) for article in articles]
                    results = await asyncio.gather(*tasks)
                    products = [p for p in results if p]
            
            elif store == 'wb':
                
                products = await wb_parser.search_products(message.text, count=ITEMS_PER_SEARCH)

            await status_msg.delete()
            if not products:
                await message.answer("😕 К сожалению, ничего не найдено.", reply_markup=get_main_menu())
                return
            
            for product in products:
                await _send_product_card(message, product)
        
        await message.answer("Поиск завершен.", reply_markup=get_main_menu())

    except Exception as e:
        logging.error(f"Критическая ошибка при поиске '{message.text}': {e}")
        await status_msg.edit_text("😔 Произошла непредвиденная ошибка при поиске.", reply_markup=get_main_menu())



async def add_favorite(callback: types.CallbackQuery, ozon_parser: OzonParser, wb_parser: WildberriesParser):
    try:
        _, _, store_code, article = callback.data.split('_')
        if store_code == "WB":
            await callback.answer("Добавление в избранное для WB в разработке.", show_alert=True)
            return

        product_data = await ozon_parser.get_product_data(article)

        if not product_data:
            await callback.answer("❌ Не удалось обновить данные о товаре", show_alert=True)
            return
        
        price = product_data.get('price_with_card') or product_data.get('price')
        await db.add_favorite_to_db(callback.from_user.id, article, product_data['name'], int(price))
        await callback.message.edit_reply_markup(reply_markup=get_product_keyboard(
            product_data['url'], store_code, article, is_favorite=True
        ))
        await callback.answer("✅ Добавлено в избранное!", show_alert=True)
    except Exception as e:
        logging.error(f"Ошибка добавления в избранное: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)

async def delete_favorite(callback: types.CallbackQuery):
    article = callback.data.split('_')[-1]
    await db.remove_favorite_from_db(callback.from_user.id, article)
    if callback.message.photo or '<b>' in callback.message.text:
        try:
            url = callback.message.reply_markup.inline_keyboard[0][0].url
            store_name = 'Ozon' if 'ozon' in url else 'WB'
            await callback.message.edit_reply_markup(reply_markup=get_product_keyboard(url, store_name, article, is_favorite=False))
        except Exception: await callback.message.delete()
    else: await callback.message.delete()
    await callback.answer("🗑️ Удалено из избранного", show_alert=True)

async def show_favorites(callback: types.CallbackQuery, state: FSMContext):
    await state.finish()
    favorites = await db.get_favorites_from_db(callback.from_user.id)
    if not favorites:
        await callback.answer("⭐ Ваш список избранного пуст", show_alert=True)
        return
    await callback.message.edit_text("⭐ Ваше избранное:")
    for product_id, name, price in favorites:
        text = f"<b>{name}</b>\nЦена: {price} ₽"
        keyboard = InlineKeyboardMarkup().add(
            InlineKeyboardButton("🛍 Открыть", url=f"https://ozon.ru/product/{product_id}/"),
            InlineKeyboardButton("🗑️ Удалить", callback_data=f"del_fav_{product_id}")
        )
        await callback.message.answer(text, reply_markup=keyboard)
    await callback.message.answer("Главное меню", reply_markup=get_main_menu())
    await callback.answer()

async def start_price_tracking(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.track_price_article)
    await callback.message.edit_text("📊 Введите артикул товара <b>Ozon</b> для отслеживания:")
    await callback.answer()

async def process_tracking_article(message: types.Message, state: FSMContext, ozon_parser: OzonParser):
    if not message.text.isdigit():
        await message.reply("⚠️ Артикул должен содержать только цифры!")
        return
    article = message.text
    status_msg = await message.answer(f"Проверяю товар Ozon {article}...")
    product_data = await ozon_parser.get_product_data(article)
    if not product_data:
        await status_msg.edit_text(f"❌ Не удалось найти товар на Ozon.", reply_markup=get_main_menu())
        await state.finish()
        return
    await state.update_data(product=product_data)
    await state.set_state(UserStates.track_price_amount)
    price = product_data.get('price_with_card') or product_data.get('price')
    await status_msg.edit_text(
        f"Товар: <b>{product_data['name']}</b>\nТекущая цена: {int(price)} ₽\n\n"
        "Введите желаемую цену (например, 1500)."
    )

async def process_tracking_price(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.reply("⚠️ Цена должна быть числом!")
        return
    desired_price = int(message.text)
    user_data = await state.get_data()
    product = user_data.get('product')
    price = product.get('price_with_card') or product.get('price')
    await db.add_tracking_to_db(
        message.from_user.id, product['article'], product['name'],
        desired_price, int(price), datetime.now().isoformat()
    )
    await state.finish()
    await message.answer("✅ Отслеживание установлено!", reply_markup=get_main_menu())

async def show_tracking(callback: types.CallbackQuery, state: FSMContext):
    await state.finish()
    tracked_items = await db.get_tracking_from_db(callback.from_user.id)
    if not tracked_items:
        await callback.answer("📊 У вас нет отслеживаемых товаров", show_alert=True)
        return
    await callback.message.edit_text("📊 Ваши отслеживаемые товары (Ozon):")
    for product_id, name, desired_price, current_price in tracked_items:
        status = "✅ Цена достигнута!" if current_price <= desired_price else "⏳ Ожидаем"
        text = f"<b>{name}</b>\nЖелаемая цена: {desired_price} ₽\nТекущая цена: {current_price} ₽\nСтатус: {status}"
        keyboard = InlineKeyboardMarkup().add(
            InlineKeyboardButton("🛍 Открыть", url=f"https://ozon.ru/product/{product_id}/"),
            InlineKeyboardButton("❌ Прекратить", callback_data=f"del_track_{product_id}")
        )
        await callback.message.answer(text, reply_markup=keyboard)
    await callback.message.answer("Главное меню", reply_markup=get_main_menu())
    await callback.answer()

async def delete_tracking(callback: types.CallbackQuery):
    article = callback.data.split('_')[-1]
    await db.remove_tracking_from_db(callback.from_user.id, article)
    await callback.message.delete()
    await callback.answer("❌ Отслеживание прекращено", show_alert=True)

def register_handlers_actions(dp: Dispatcher):
    dp.register_callback_query_handler(go_to_search, lambda c: c.data == 'go_to_search', state='*')
    dp.register_callback_query_handler(start_search, lambda c: c.data.startswith('search_'), state='*')
    dp.register_message_handler(handle_search_query, state=UserStates.search_query)
    dp.register_callback_query_handler(add_favorite, lambda c: c.data.startswith('add_fav_'))
    dp.register_callback_query_handler(delete_favorite, lambda c: c.data.startswith('del_fav_'))
    dp.register_callback_query_handler(show_favorites, lambda c: c.data == 'show_favorites', state='*')
    dp.register_callback_query_handler(start_price_tracking, lambda c: c.data == 'track_price', state='*')
    dp.register_message_handler(process_tracking_article, state=UserStates.track_price_article)
    dp.register_message_handler(process_tracking_price, state=UserStates.track_price_amount)
    dp.register_callback_query_handler(show_tracking, lambda c: c.data == 'show_tracking', state='*')
    dp.register_callback_query_handler(delete_tracking, lambda c: c.data.startswith('del_track_'))