import asyncio
import sys
import logging
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

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        [KeyboardButton(text='➕ Добавить работника')]
    ],
    resize_keyboard=True
)

# Состояния для создания заявки
class CreateRequest(StatesGroup):
    category = State()
    address = State()
    contact_number = State()
    description = State()

# Состояния для управления заявками и работниками
class ManageRequests(StatesGroup):
    view_requests = State()
    view_workers = State()

# Состояние для добавления работника
class AddWorker(StatesGroup):
    user_id = State()

# Функция для удаления предыдущих сообщений
async def delete_previous_messages(chat_id, message_ids):
    for message_id in message_ids:
        try:
            await bot.delete_message(chat_id, message_id)
        except Exception as e:
            logger.error(f"Ошибка при удалении сообщения: {e}")

# Обработка команды /start
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.update_data(last_messages=[])  # Инициализация списка последних сообщений
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
    user_id = message.from_user.id
    user = get_user_by_user_id(user_id)
    
    if not user:
        add_user(user_id, phone, name=message.from_user.full_name)
        await message.answer("✅ Вы зарегистрированы как клиент.", reply_markup=main_menu_client)
    else:
        cursor.execute('UPDATE users SET phone = ? WHERE user_id = ?', (phone, user_id))
        conn.commit()
        role = user[3]
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

    if message.text:
        description = message.text

    if message.photo:
        photo = message.photo[-1].file_id

    await state.update_data(description=description, photo=photo)

    if message.photo and not message.caption:
        skip_button = KeyboardButton(text='⏭ Пропустить')
        await message.answer("📝 Пожалуйста, опишите проблему (или нажмите 'Пропустить'):", reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [skip_button]
            ],
            resize_keyboard=True
        ))
        return

    if message.text == '⏭ Пропустить':
        await finish_request(message, state)
        return

    await finish_request(message, state)

# Завершение создания заявки
async def finish_request(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    user_id = message.from_user.id
    user = get_user_by_user_id(user_id)
    
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден. Пожалуйста, зарегистрируйтесь снова.")
        await state.clear()
        return
    
    add_request(
        category=user_data.get('category'),
        description=user_data.get('description', 'Описание не указано'),
        client_id=user_id
    )
    
    await message.answer("✅ Заявка успешно создана!", reply_markup=main_menu_client)
    await state.clear()

# Обработка кнопки "📋 Мои заявки"
@dp.message(lambda message: message.text == '📋 Мои заявки')
async def my_requests(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user = get_user_by_user_id(user_id)
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден. Пожалуйста, зарегистрируйтесь снова.")
        return
    
    requests = get_user_requests(user_id)
    if not requests:
        await message.answer("📭 У вас нет активных заявок.")
        return
    
    for req in requests:
        request_number = f"{str(user_id)[:4]}{10 + req[0]}"
        status = "✅ Принята" if req[4] == "in_progress" else "⏳ Ожидает принятия"
        contact_number = user[1]
        text = f"🛠️ Категория: {req[1]}\n📞 Номер для связи: {contact_number}\n📝 Описание: {req[2]}\n📝 Статус: {status}"
        
        delete_button = InlineKeyboardButton(text='🗑️ Удалить заявку', callback_data=f"confirm_delete_{req[0]}")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[delete_button]])
        
        await message.answer(text, reply_markup=keyboard)

# Подтверждение удаления заявки
@dp.callback_query(lambda c: c.data.startswith('confirm_delete_'))
async def confirm_delete_request(callback_query: types.CallbackQuery, state: FSMContext):
    request_id = callback_query.data.split('_')[2]
    
    confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='✅ Подтвердить', callback_data=f"delete_request_{request_id}"),
            InlineKeyboardButton(text='❌ Отменить', callback_data=f"cancel_delete_{request_id}")
        ]
    ])
    
    await callback_query.message.edit_reply_markup(reply_markup=confirm_keyboard)
    await callback_query.answer()

# Обработка отмены удаления
@dp.callback_query(lambda c: c.data.startswith('cancel_delete_'))
async def cancel_delete(callback_query: types.CallbackQuery, state: FSMContext):
    request_id = callback_query.data.split('_')[2]
    
    user_id = callback_query.from_user.id
    user = get_user_by_user_id(user_id)
    if not user:
        await callback_query.answer("❌ Ошибка: пользователь не найден.")
        return
    
    req = get_request_by_id(request_id)
    if not req:
        await callback_query.answer("❌ Заявка не найдена.")
        return
    
    request_number = f"{str(user_id)[:4]}{10 + req[0]}"
    status = "✅ Принята" if req[4] == "in_progress" else "⏳ Ожидает принятия"
    text = f"🛠️ Категория: {req[1]}\n📞 Номер для связи: {req[2]}\n📝 Описание: {req[2]}\n📝 Статус: {status}"
    
    delete_button = InlineKeyboardButton(text='🗑️ Удалить заявку', callback_data=f"confirm_delete_{req[0]}")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[delete_button]])
        
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer("❌ Удаление отменено.")

# Обработка удаления заявки
@dp.callback_query(lambda c: c.data.startswith('delete_request_'))
async def delete_request(callback_query: types.CallbackQuery, state: FSMContext):
    request_id = callback_query.data.split('_')[2]
    
    cursor.execute('UPDATE requests SET is_deleted = 1 WHERE id = ?', (request_id,))
    conn.commit()
    
    await callback_query.message.delete()
    await callback_query.answer("🗑️ Заявка успешно удалена!")

# Обработка кнопки "📋 Управление заявками" (для админа)
@dp.message(lambda message: message.text == '📋 Управление заявками')
async def admin_manage_requests(message: types.Message, state: FSMContext):
    user = get_user_by_user_id(message.from_user.id)
    if not user or user[3] != 'admin':
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Активные заявки', callback_data='view_active_requests_0')],
        [InlineKeyboardButton(text='Неактивные заявки', callback_data='view_inactive_requests_0')],
        [InlineKeyboardButton(text='Удаленные заявки', callback_data='view_deleted_requests_0')],
        [InlineKeyboardButton(text='🔙 Назад', callback_data='back_to_admin_menu')]
    ])
    
    await message.answer("📋 Выберите категорию заявок:", reply_markup=keyboard)
    await state.set_state(ManageRequests.view_requests)

# Обработка выбора категории заявок
@dp.callback_query(lambda c: c.data.startswith('view_') and ManageRequests.view_requests)
async def view_requests(callback_query: types.CallbackQuery, state: FSMContext):
    data = callback_query.data.split('_')
    category = data[1]
    offset = int(data[3])
    
    if category == 'active':
        requests = get_all_requests(include_deleted=False)
    elif category == 'inactive':
        requests = get_all_requests(include_deleted=False)
    else:
        requests = get_all_requests(include_deleted=True)
    
    requests_to_show = requests[offset:offset+5]
    
    if not requests_to_show:
        await callback_query.answer("Нет заявок для отображения.")
        return
    
    # Удаляем предыдущие сообщения
    user_data = await state.get_data()
    last_messages = user_data.get('last_messages', [])
    await delete_previous_messages(callback_query.message.chat.id, last_messages)
    
    # Отправляем новые сообщения
    new_messages = []
    for req in requests_to_show:
        status = "✅ Принята" if req[4] == "in_progress" else "⏳ Ожидает принятия"
        text = f"🛠️ Категория: {req[1]}\n📞 Номер для связи: {req[2]}\n📝 Описание: {req[2]}\n📝 Статус: {status}"
        
        delete_button = InlineKeyboardButton(text='🗑️ Удалить', callback_data=f"delete_request_{req[0]}")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[delete_button]])
        
        sent_message = await callback_query.message.answer(text, reply_markup=keyboard)
        new_messages.append(sent_message.message_id)
    
    # Обновляем список последних сообщений
    await state.update_data(last_messages=new_messages)
    
    # Кнопки для навигации
    nav_buttons = []
    if offset > 0:
        nav_buttons.append(InlineKeyboardButton(text='⬅️ Назад', callback_data=f"view_{category}_requests_{offset-5}"))
    if offset + 5 < len(requests):
        nav_buttons.append(InlineKeyboardButton(text='Далее ➡️', callback_data=f"view_{category}_requests_{offset+5}"))
    
    if nav_buttons:
        nav_keyboard = InlineKeyboardMarkup(inline_keyboard=[nav_buttons])
        sent_message = await callback_query.message.answer("Навигация:", reply_markup=nav_keyboard)
        new_messages.append(sent_message.message_id)
    
    await callback_query.answer()

# Обработка кнопки "👷 Управление работниками"
@dp.message(lambda message: message.text == '👷 Управление работниками')
async def admin_manage_workers(message: types.Message, state: FSMContext):
    user = get_user_by_user_id(message.from_user.id)
    if not user or user[3] != 'admin':
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    
    workers = get_all_workers()
    if not workers:
        await message.answer("👷 Нет работников.")
        return
    
    workers_to_show = workers[:5]
    
    # Удаляем предыдущие сообщения
    user_data = await state.get_data()
    last_messages = user_data.get('last_messages', [])
    await delete_previous_messages(message.chat.id, last_messages)
    
    # Отправляем новые сообщения
    new_messages = []
    for worker in workers_to_show:
        text = f"👷 ID: {worker[0]}\n📞 Телефон: {worker[1]}\n👤 Имя: {worker[2]}"
        
        delete_button = InlineKeyboardButton(text='🗑️ Удалить', callback_data=f"delete_worker_{worker[0]}")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[delete_button]])
        
        sent_message = await message.answer(text, reply_markup=keyboard)
        new_messages.append(sent_message.message_id)
    
    # Обновляем список последних сообщений
    await state.update_data(last_messages=new_messages)
    
    # Кнопки для навигации
    nav_buttons = []
    if len(workers) > 5:
        nav_buttons.append(InlineKeyboardButton(text='Далее ➡️', callback_data='view_workers_5'))
    
    if nav_buttons:
        nav_keyboard = InlineKeyboardMarkup(inline_keyboard=[nav_buttons])
        sent_message = await message.answer("Навигация:", reply_markup=nav_keyboard)
        new_messages.append(sent_message.message_id)
    
    await state.set_state(ManageRequests.view_workers)

# Обработка навигации по работникам
@dp.callback_query(lambda c: c.data.startswith('view_workers_') and ManageRequests.view_workers)
async def view_workers(callback_query: types.CallbackQuery, state: FSMContext):
    offset = int(callback_query.data.split('_')[2])
    workers = get_all_workers()
    
    workers_to_show = workers[offset:offset+5]
    
    if not workers_to_show:
        await callback_query.answer("Нет работников для отображения.")
        return
    
    # Удаляем предыдущие сообщения
    user_data = await state.get_data()
    last_messages = user_data.get('last_messages', [])
    await delete_previous_messages(callback_query.message.chat.id, last_messages)
    
    # Отправляем новые сообщения
    new_messages = []
    for worker in workers_to_show:
        text = f"👷 ID: {worker[0]}\n📞 Телефон: {worker[1]}\n👤 Имя: {worker[2]}"
        
        delete_button = InlineKeyboardButton(text='🗑️ Удалить', callback_data=f"delete_worker_{worker[0]}")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[delete_button]])
        
        sent_message = await callback_query.message.answer(text, reply_markup=keyboard)
        new_messages.append(sent_message.message_id)
    
    # Обновляем список последних сообщений
    await state.update_data(last_messages=new_messages)
    
    # Кнопки для навигации
    nav_buttons = []
    if offset > 0:
        nav_buttons.append(InlineKeyboardButton(text='⬅️ Назад', callback_data=f"view_workers_{offset-5}"))
    if offset + 5 < len(workers):
        nav_buttons.append(InlineKeyboardButton(text='Далее ➡️', callback_data=f"view_workers_{offset+5}"))
    
    if nav_buttons:
        nav_keyboard = InlineKeyboardMarkup(inline_keyboard=[nav_buttons])
        sent_message = await callback_query.message.answer("Навигация:", reply_markup=nav_keyboard)
        new_messages.append(sent_message.message_id)
    
    await callback_query.answer()

# Обработка кнопки "📊 Статистика"
@dp.message(lambda message: message.text == '📊 Статистика')
async def admin_statistics(message: types.Message, state: FSMContext):
    user = get_user_by_user_id(message.from_user.id)
    if not user or user[3] != 'admin':
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    
    requests = get_all_requests(include_deleted=True)
    active_requests = [req for req in requests if req[6] == 0]
    inactive_requests = [req for req in requests if req[6] == 1]
    in_progress_requests = [req for req in requests if req[4] == "in_progress"]
    
    text = f"""
📊 Статистика по заявкам:
🟢 Активные заявки: {len(active_requests)}
🔴 Неактивные заявки: {len(inactive_requests)}
🟡 В процессе: {len(in_progress_requests)}
"""
    # Удаляем предыдущие сообщения
    user_data = await state.get_data()
    last_messages = user_data.get('last_messages', [])
    await delete_previous_messages(message.chat.id, last_messages)
    
    # Отправляем новое сообщение
    sent_message = await message.answer(text)
    await state.update_data(last_messages=[sent_message.message_id])

# Обработка кнопки "🔙 Назад" в админской панели
@dp.callback_query(lambda c: c.data == 'back_to_admin_menu')
async def back_to_admin_menu(callback_query: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback_query.message.answer("🔙 Вы вернулись в админское меню.", reply_markup=main_menu_admin)
    await callback_query.answer()

# Обработка кнопки "➕ Добавить работника"
@dp.message(lambda message: message.text == '➕ Добавить работника')
async def add_worker_command(message: types.Message, state: FSMContext):
    user = get_user_by_user_id(message.from_user.id)
    if not user or user[3] != 'admin':
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
    
    add_worker(int(user_id))
    await message.answer(f"✅ Пользователь с user_id {user_id} теперь работник!", reply_markup=main_menu_admin)
    await state.clear()

# Обработка удаления работника
@dp.callback_query(lambda c: c.data.startswith('delete_worker_'))
async def delete_worker(callback_query: types.CallbackQuery, state: FSMContext):
    worker_id = callback_query.data.split('_')[2]
    
    demote_worker_to_client(worker_id)
    await callback_query.message.delete()
    await callback_query.answer("👷 Работник понижен до пользователя!")

# Обработка кнопки "📋 Доступные заявки" (для работника)
@dp.message(lambda message: message.text == '📋 Доступные заявки')
async def show_available_requests(message: types.Message):
    user_id = message.from_user.id
    user = get_user_by_user_id(user_id)
    
    if not user or user[3] != 'worker':
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    
    requests = get_available_requests()
    
    if not requests:
        await message.answer("📭 Нет доступных заявок.")
        return
    
    for req in requests:
        request_number = f"{str(user_id)[:4]}{10 + req[0]}"
        text = f"🛠️ Категория: {req[1]}\n📝 Описание: {req[2]}\n📝 Статус: {req[4]}"
        
        take_button = InlineKeyboardButton(text='✅ Принять заявку', callback_data=f"take_request_{req[0]}")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[take_button]])
        
        await message.answer(text, reply_markup=keyboard)

# Обработка принятия заявки (для работника)
@dp.callback_query(lambda c: c.data.startswith('take_request_'))
async def take_request(callback_query: types.CallbackQuery):
    request_id = callback_query.data.split('_')[2]
    worker_id = callback_query.from_user.id
    
    take_request(request_id, worker_id)
    
    await callback_query.message.edit_text("✅ Заявка принята!")
    await callback_query.answer()

# Запуск бота
if __name__ == '__main__':
    asyncio.run(dp.start_polling(bot))