import asyncio
import sys
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from database import *

# Исправление для Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Инициализация хранилища состояний
storage = MemoryStorage()

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# Клавиатуры
main_menu_client = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='🛠️ Оставить заявку')],
        [KeyboardButton(text='📋 Мои заявки')],
        [KeyboardButton(text='📞 Связаться с поддержкой')]
    ],
    resize_keyboard=True
)

main_menu_worker = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='📋 Доступные заявки')],
        [KeyboardButton(text='📋 Мои заявки')],
        [KeyboardButton(text='👤 Профиль')]
    ],
    resize_keyboard=True
)

main_menu_admin = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='📋 Управление заявками')],
        [KeyboardButton(text='👷 Управление работниками')],
        [KeyboardButton(text='📊 Статистика')],
        [KeyboardButton(text='➕ Добавить работника')]  # Новая кнопка
    ],
    resize_keyboard=True
)

# Состояния для создания заявки
class CreateRequest(StatesGroup):
    category = State()
    address = State()  # Изменено с city на address
    contact_number = State()
    description = State()

# Состояние для добавления работника
class AddWorker(StatesGroup):
    user_id = State()  # Оставляем только user_id

# Обработка команды /start
@dp.message(Command("start"))
async def start(message: types.Message):
    welcome_text = """
👋 Добро пожаловать в бота для заказа мастеров! 🛠️

Здесь вы можете оставить заявку на ремонт мебели, сантехники или электрики у вас дома. 🪑🚿💡

📋 Что умеет бот:
- 🛠️ Оставить заявку на ремонт
- 📋 Просмотреть свои заявки
- 🗑️ Удалить заявку
- 📞 Связаться с поддержкой

Нажмите кнопку "🛠️ Оставить заявку", чтобы начать! �
"""
    await message.answer(welcome_text, reply_markup=ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='📱 Отправить номер телефона', request_contact=True)]
        ],
        resize_keyboard=True
    ))

# Обработка номера телефона
@dp.message(lambda message: message.contact is not None)
async def handle_contact(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number
    user_id = message.from_user.id  # Получаем user_id из Telegram
    user = get_user_by_user_id(user_id)
    
    if not user:
        # Регистрируем пользователя, если он не найден
        add_user(user_id, phone, name=message.from_user.full_name)  # Передаем user_id, phone и name
        await message.answer("✅ Вы зарегистрированы как клиент.", reply_markup=main_menu_client)
    else:
        # Если пользователь уже существует, обновляем его данные (например, номер телефона)
        cursor.execute('UPDATE users SET phone = ? WHERE user_id = ?', (phone, user_id))
        conn.commit()
        role = user[3]  # Роль находится на 4-й позиции (индекс 3)
        if role == 'client':
            await message.answer("👋 Добро пожаловать, клиент!", reply_markup=main_menu_client)
        elif role == 'worker':
            await message.answer("👋 Добро пожаловать, работник!", reply_markup=main_menu_worker)
        elif role == 'admin':
            await message.answer("👋 Добро пожаловать, админ!", reply_markup=main_menu_admin)
    
    await state.update_data(phone=phone, user_id=user_id)

# Обработка кнопки "🛠️ Оставить заявку"
@dp.message(lambda message: message.text == '🛠️ Оставить заявку')
async def create_request(message: types.Message, state: FSMContext):
    await message.answer("🛠️ Выберите категорию:", reply_markup=ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='🪑 Ремонт мебели')],
            [KeyboardButton(text='🚿 Сантехника')],
            [KeyboardButton(text='💡 Электрика')],
            [KeyboardButton(text='🔙 Назад')]
        ],
        resize_keyboard=True
    ))
    await state.set_state(CreateRequest.category)

# Обработка кнопки "🔙 Назад"
@dp.message(lambda message: message.text == '🔙 Назад')
async def back_to_main_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🔙 Вы вернулись в главное меню.", reply_markup=main_menu_client)

# Обработка категории
@dp.message(CreateRequest.category)
async def process_category(message: types.Message, state: FSMContext):
    if message.text == '🔙 Назад':
        await back_to_main_menu(message, state)
        return
    await state.update_data(category=message.text)
    await state.set_state(CreateRequest.address)
    await message.answer("🏙️ Введите полный адрес:", reply_markup=ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='🔙 Назад')]
        ],
        resize_keyboard=True
    ))

# Обработка адреса
@dp.message(CreateRequest.address)
async def process_address(message: types.Message, state: FSMContext):
    if message.text == '🔙 Назад':
        await back_to_main_menu(message, state)
        return
    await state.update_data(address=message.text)
    await state.set_state(CreateRequest.contact_number)
    await message.answer("📞 Введите номер для связи:", reply_markup=ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='🔙 Назад')]
        ],
        resize_keyboard=True
    ))

# Обработка номера для связи
@dp.message(CreateRequest.contact_number)
async def process_contact_number(message: types.Message, state: FSMContext):
    if message.text == '🔙 Назад':
        await back_to_main_menu(message, state)
        return
    await state.update_data(contact_number=message.text)
    await state.set_state(CreateRequest.description)
    await message.answer("📝 Опишите проблему (можно приложить фото):", reply_markup=ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='🔙 Назад')]
        ],
        resize_keyboard=True
    ))

# Обработка описания и фото
@dp.message(CreateRequest.description)
async def process_description(message: types.Message, state: FSMContext):
    if message.text == '🔙 Назад':
        await back_to_main_menu(message, state)
        return
    
    user_data = await state.get_data()
    description = user_data.get('description', '')
    photo = user_data.get('photo', None)

    # Если есть текст, добавляем его к описанию
    if message.text:
        description = message.text

    # Если есть фото, сохраняем его
    if message.photo:
        photo = message.photo[-1].file_id

    # Обновляем данные в состоянии
    await state.update_data(description=description, photo=photo)

    # Если пользователь отправил фото без текста, предлагаем добавить описание
    if message.photo and not message.caption:
        skip_button = KeyboardButton(text='⏭ Пропустить')
        await message.answer("📝 Пожалуйста, опишите проблему (или нажмите 'Пропустить'):", reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [skip_button]
            ],
            resize_keyboard=True
        ))
        return

    # Если пользователь нажимает "Пропустить", завершаем создание заявки
    if message.text == '⏭ Пропустить':
        await finish_request(message, state)
        return

    # Если есть и текст, и фото, завершаем создание заявки
    await finish_request(message, state)

# Завершение создания заявки
async def finish_request(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    user_id = message.from_user.id  # Используем user_id напрямую из сообщения
    user = get_user_by_user_id(user_id)
    
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден. Пожалуйста, зарегистрируйтесь снова.")
        await state.clear()
        return
    
    # Добавляем заявку в базу данных
    add_request(
        category=user_data.get('category'),
        description=user_data.get('description', 'Описание не указано'),  # Если описание не указано
        client_id=user_id  # Используем user_id напрямую
    )
    
    await message.answer("✅ Заявка успешно создана!", reply_markup=main_menu_client)
    await state.clear()

# Обработка кнопки "📋 Мои заявки"
@dp.message(lambda message: message.text == '📋 Мои заявки')
async def my_requests(message: types.Message):
    user_id = message.from_user.id
    user = get_user_by_user_id(user_id)
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден. Пожалуйста, зарегистрируйтесь снова.")
        return
    
    requests = get_user_requests(user_id)  # Используем user_id напрямую
    if not requests:
        await message.answer("📭 У вас нет активных заявок.")
        return
    
    for req in requests:
        request_number = f"{str(user_id)[:4]}{10 + req[0]}"  # Формируем номер заявки
        status = "✅ Принята" if req[4] == "in_progress" else "⏳ Ожидает принятия"
        
        # Получаем номер телефона из данных пользователя
        contact_number = user[1]  # Номер телефона находится на 2-й позиции (индекс 1)
        
        text = f"🛠️ Категория: {req[1]}\n📞 Номер для связи: {contact_number}\n📝 Описание: {req[2]}\n📝 Статус: {status}"
        
        # Кнопка "🗑️ Удалить заявку"
        delete_button = InlineKeyboardButton(text='🗑️ Удалить заявку', callback_data=f"confirm_delete_{req[0]}")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[delete_button]])
        
        await message.answer(text, reply_markup=keyboard)

# Подтверждение удаления заявки
@dp.callback_query(lambda c: c.data.startswith('confirm_delete_'))
async def confirm_delete_request(callback_query: types.CallbackQuery):
    request_id = callback_query.data.split('_')[2]
    
    # Создаем клавиатуру для подтверждения удаления
    confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='✅ Подтвердить', callback_data=f"delete_request_{request_id}"),
            InlineKeyboardButton(text='❌ Отменить', callback_data=f"cancel_delete_{request_id}")
        ]
    ])
    
    # Редактируем сообщение с заявкой, добавляя кнопки подтверждения
    await callback_query.message.edit_reply_markup(reply_markup=confirm_keyboard)
    await callback_query.answer()

# Обработка отмены удаления
@dp.callback_query(lambda c: c.data.startswith('cancel_delete_'))
async def cancel_delete(callback_query: types.CallbackQuery):
    request_id = callback_query.data.split('_')[2]
    
    # Возвращаем исходное сообщение с кнопкой "🗑️ Удалить заявку"
    user_id = callback_query.from_user.id
    user = get_user_by_user_id(user_id)
    if not user:
        await callback_query.answer("❌ Ошибка: пользователь не найден.")
        return
    
    req = get_request_by_id(request_id)
    if not req:
        await callback_query.answer("❌ Заявка не найдена.")
        return
    
    request_number = f"{str(user_id)[:4]}{10 + req[0]}"  # Формируем номер заявки
    status = "✅ Принята" if req[4] == "in_progress" else "⏳ Ожидает принятия"
    text = f"🛠️ Категория: {req[1]}\n📞 Номер для связи: {req[2]}\n📝 Описание: {req[2]}\n📝 Статус: {status}"
    
    delete_button = InlineKeyboardButton(text='🗑️ Удалить заявку', callback_data=f"confirm_delete_{req[0]}")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[delete_button]])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer("❌ Удаление отменено.")

# Обработка удаления заявки
@dp.callback_query(lambda c: c.data.startswith('delete_request_'))
async def delete_request(callback_query: types.CallbackQuery):
    request_id = callback_query.data.split('_')[2]
    
    # Удаляем заявку (помечаем как удаленную)
    cursor.execute('UPDATE requests SET is_deleted = 1 WHERE id = ?', (request_id,))
    conn.commit()
    
    # Удаляем сообщение с заявкой
    await callback_query.message.delete()
    
    # Отправляем подтверждение об удалении
    await callback_query.answer("🗑️ Заявка успешно удалена!")

# Обработка кнопки "📋 Управление заявками" (для админа)
@dp.message(lambda message: message.text == '📋 Управление заявками')
async def admin_manage_requests(message: types.Message):
    user_id = message.from_user.id
    user = get_user_by_user_id(user_id)
    if not user or user[3] != 'admin':  # Проверяем, что пользователь — админ (роль на 4-й позиции)
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    
    # Получаем все заявки, включая удаленные
    requests = get_all_requests(include_deleted=True)
    if not requests:
        await message.answer("📭 Нет заявок.")
        return
    
    for req in requests:
        request_number = f"{str(user_id)[:4]}{10 + req[0]}"  # Формируем номер заявки
        status = "✅ Принята" if req[4] == "in_progress" else "⏳ Ожидает принятия"
        deleted_status = "🗑️ Удалена" if req[6] == 1 else "✅ Активна"
        text = f"🛠️ Категория: {req[1]}\n📞 Номер для связи: {req[2]}\n📝 Описание: {req[2]}\n📝 Статус: {status}\n🗑️ Статус удаления: {deleted_status}"
        await message.answer(text)

# Обработка кнопки "📞 Связаться с поддержкой"
@dp.message(lambda message: message.text == '📞 Связаться с поддержкой')
async def contact_support(message: types.Message):
    await message.answer("📞 Свяжитесь с нами:\nТелефон: +79319638381\nTelegram: @mercu3", reply_markup=main_menu_client)

# Обработка кнопки "➕ Добавить работника"
@dp.message(lambda message: message.text == '➕ Добавить работника')
async def add_worker_command(message: types.Message, state: FSMContext):
    user = get_user_by_user_id(message.from_user.id)
    if not user or user[3] != 'admin':  # Проверяем, что пользователь — админ
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    
    await message.answer("Введите user_id нового работника:")
    await state.set_state(AddWorker.user_id)

# Обработка user_id
@dp.message(AddWorker.user_id)
async def process_user_id(message: types.Message, state: FSMContext):
    user_id = message.text
    if not user_id.isdigit():
        await message.answer("❌ user_id должен быть числом. Попробуйте снова.")
        return
    
    # Добавляем работника
    add_worker(int(user_id))
    await message.answer(f"✅ Пользователь с user_id {user_id} теперь работник!", reply_markup=main_menu_admin)
    await state.clear()

# Запуск бота
if __name__ == '__main__':
    asyncio.run(dp.start_polling(bot))
