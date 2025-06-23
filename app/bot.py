import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.utils.exceptions import BotBlocked, ChatNotFound, TerminatedByOtherGetUpdates

from app.config import BOT_TOKEN, PRICE_CHECK_INTERVAL
from app import database as db
from app.handlers.common import register_handlers_common
from app.handlers.actions import register_handlers_actions
from app.services.ozon_parser import OzonParser
from app.services.wildberries_parser import WildberriesParser


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class ParsersMiddleware(BaseMiddleware):
    def __init__(self, ozon_parser: OzonParser, wb_parser: WildberriesParser):
        super().__init__()
        self.ozon_parser = ozon_parser
        self.wb_parser = wb_parser

    async def on_process_message(self, message: types.Message, data: dict):
        data['ozon_parser'] = self.ozon_parser
        data['wb_parser'] = self.wb_parser

    async def on_process_callback_query(self, callback_query: types.CallbackQuery, data: dict):
        data['ozon_parser'] = self.ozon_parser
        data['wb_parser'] = self.wb_parser


async def check_prices_periodically(bot: Bot, parser: OzonParser):

    await asyncio.sleep(20)
    logging.info("Фоновая задача проверки цен запущена.")
    
    while True:
        logging.info("Начинаю плановую проверку цен Ozon...")
        try:
            all_tracked_items = await db.get_all_tracking_from_db()
            
            if not all_tracked_items:
                logging.info("Нет товаров для отслеживания. Следующая проверка через {} секунд.".format(PRICE_CHECK_INTERVAL))
            else:
                logging.info(f"Найдено {len(all_tracked_items)} товаров для проверки.")
                for user_id, product_id, name, desired_price, old_price in all_tracked_items:
                    logging.info(f"Проверяю товар {product_id} для пользователя {user_id}...")
                    
                    product_data = await parser.get_product_data(product_id)
                    # Добавляем задержку между запросами, чтобы не получить бан
                    await asyncio.sleep(5) 
                    
                    if product_data and product_data.get('price'):
                        # Используем цену с картой, если она выгоднее
                        new_price = product_data.get('price_with_card') or product_data.get('price')
                        
                        # Обновляем текущую цену в БД
                        await db.update_tracking_in_db(user_id, product_id, int(new_price), datetime.now().isoformat())
                        
                        # Сравниваем с желаемой ценой
                        if new_price <= desired_price:
                            logging.info(f"ЦЕНА СНИЖЕНА! Товар {product_id}, новая цена {new_price} <= желаемой {desired_price}.")
                            text = (f"🎉 <b>Цена снижена!</b>\n\n"
                                    f"<b>{name}</b>\n"
                                    f"Старая цена: {old_price} ₽\n"
                                    f"Новая цена: <b>{int(new_price)} ₽</b> (ваша цель: {desired_price} ₽)\n\n"
                                    f"https://ozon.ru/product/{product_id}/")
                            try:
                                await bot.send_message(user_id, text)
                                # После успешной отправки удаляем товар из отслеживания
                                await db.remove_tracking_from_db(user_id, product_id)
                                logging.info(f"Уведомление отправлено пользователю {user_id} и товар удален из отслеживания.")
                            except (BotBlocked, ChatNotFound):
                                logging.warning(f"Пользователь {user_id} заблокировал бота. Удаляем все его отслеживания.")
                                await db.remove_tracking_from_db(user_id, product_id)
                        else:
                            logging.info(f"Цена на товар {product_id} не изменилась значительно ({new_price} > {desired_price}).")
                    else:
                        logging.warning(f"Не удалось получить данные для товара {product_id} при плановой проверке.")

        except Exception as e:
            logging.error(f"Критическая ошибка в фоновой задаче проверки цен: {e}")
        
        # Ждем следующей проверки
        await asyncio.sleep(PRICE_CHECK_INTERVAL)

# Функции запуска и остановки
async def on_startup(dp: Dispatcher):
    await db.initialize_db()
    
    ozon_parser = OzonParser()
    wb_parser = WildberriesParser()
    
    dp.middleware.setup(ParsersMiddleware(ozon_parser, wb_parser))
    dp['ozon_parser'] = ozon_parser
    
    asyncio.create_task(check_prices_periodically(dp.bot, ozon_parser))

async def on_shutdown(dp: Dispatcher):
    ozon_parser = dp.get('ozon_parser')
    if ozon_parser:
        ozon_parser.quit()
    logging.warning('Бот остановлен.')

# Главная функция
def main():
    bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.HTML)
    storage = MemoryStorage()
    dp = Dispatcher(bot, storage=storage)

    # Регистрация всех обработчиков
    register_handlers_common(dp)
    register_handlers_actions(dp)

    try:
        executor.start_polling(dp, skip_updates=True, on_startup=on_startup, on_shutdown=on_shutdown)
    except TerminatedByOtherGetUpdates:
        logging.critical("ЗАПУЩЕНА ДРУГАЯ КОПИЯ БОТА! Остановите все процессы python.exe и попробуйте снова.")
    except Exception as e:
        logging.critical(f"Непредвиденная ошибка при запуске: {e}")

if __name__ == '__main__':
    main()