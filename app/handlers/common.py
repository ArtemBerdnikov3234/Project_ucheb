from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from app.keyboards import get_main_menu

async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(
        "👋 Привет! Я бот для поиска товаров на Ozon.\nВыберите действие:",
        reply_markup=get_main_menu()
    )

async def back_to_main_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await callback.message.edit_text(
        "Главное меню. Выберите действие:",
        reply_markup=get_main_menu()
    )
    await callback.answer()

def register_handlers_common(dp: Dispatcher):
    dp.register_message_handler(cmd_start, commands=['start'], state='*')
    dp.register_callback_query_handler(back_to_main_menu, lambda c: c.data == 'main_menu', state='*')