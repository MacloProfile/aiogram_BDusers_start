# Import necessary libraries/modules
import configparser  # For reading configuration settings
import random  # For generating random values
import string  # For working with strings
import time  # For time-related operations

from aiogram import Bot, types  # For working with the Telegram Bot API
from aiogram.contrib.fsm_storage.memory import MemoryStorage  # For managing states in the bot
from aiogram.dispatcher import Dispatcher, FSMContext  # For handling message dispatching and states
from aiogram.dispatcher.filters.state import State, StatesGroup  # For defining states
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)  # For defining message types and keyboards
from aiogram.utils import executor  # For handling bot execution

import db  # A custom module for database operations

# Read configuration settings from settings.ini
config = configparser.ConfigParser()
config.read("settings.ini")
token = config["bot"]["token"]
admin_id = int(config["bot"]["admin_id"])
admin_link = config["bot"]["admin_link"]
link = config["bot"]["link"]

# Create a bot instance using the provided token
bot = Bot(token=token)

# Initialize a dispatcher with a memory storage
dp = Dispatcher(bot, storage=MemoryStorage())


# Define states for the conversation flow
class States(StatesGroup):
    menu = State()  # Main menu state
    pay = State()  # Payment state
    pay_sum = State()  # Payment amount state
    admin_mail = State()  # Admin message state
    admin_mail_accept = State()  # Admin message confirmation state


# Define a function to generate a user profile + ref system
def profile(user_id):
    _data = db.get_info(user_id)
    return f"""<b>Привет, {_data[2]}!</b>

👤 <b>Ваш ID:</b> {_data[1]}
📅 <b>Дата регистрации:</b> {_data[3]}
💵 <b>Баланс:</b> {_data[5]}

🔥 <b>Text
💎 Text

Зарабатывай по {db.get_settings()[5]} койнов за каждого приглашенного друга!</b>

👤 <b>Приглашено:</b> {db.get_refs(user_id)}
<b>{link}?start={user_id}</b>

<b>Администратор:</b> {admin_link} 
"""


def get_user_info(user_id):
    _data = db.get_info(user_id)
    _pre_ref = db.get_pre_ref(user_id)
    _pre_ref_str = f"""{_pre_ref} (@{db.get_info(_pre_ref)[2]})""" if int(_pre_ref) != 0 else "Нет"
    return f"""INFO *@{_data[2]}*

👤 *ID:* {_data[1]}
📅 *Дата регистрации:* {_data[3]}
💵 *Баланс:* {_data[5]}

👤 *Реферал:* {_pre_ref_str}

👤 *Приглашено:* {db.get_refs(user_id)}
"""

# Define a function to create a reply keyboard
def reply_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton('💼 Профиль'))
    keyboard.add(KeyboardButton('💵 Пополнить баланс'))
    return keyboard

# Define a function to create a simple "back" keyboard
def just_back():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton('↪️ Назад'))
    return keyboard

# Define a function to create an inline payment keyboard
def inline_keyboard(pay_sum, comment, code):
    link = f"https://qiwi.com/payment/form/{code}?extra%5B%27account%27%5D={db.get_settings()[1]}&amountInteger={pay_sum}&amountFraction=0&extra%5B%27comment%27%5D={comment}&currency=643&blocked%5B0%5D=sum&blocked%5B1%5D=comment&blocked%5B2%5D=account"
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="💵 Оплатить", url=link))
    return keyboard

# Define a function to generate a random order ID
def random_order():
    return f"{random.randint(44, 77)}{random.choice(string.ascii_letters)}{random.choice(string.ascii_letters)}{random.randint(371, 984)}{random.choice(string.ascii_letters)}{random.randint(11, 24)}"


# Define a handler for the main menu and start command
@dp.message_handler(text=["💼 Профиль", "↪️ Назад"], state="*")
@dp.message_handler(commands=["start"], state="*")
async def menu(message: types.Message, state: FSMContext):
    _user_id = message.chat.id
    _username = message.chat.username
    if not (db.get_users_exist(message.chat.id)):
        if (message.text != "💼 Профиль" and message.text.startswith("/start ")):
            _ref = message.text.replace("/start ", "")
            if (int(message.chat.id) != int(_ref)):
                db.add_user_to_db(message.chat.id, message.chat.username, _ref, db.get_settings()[4])
                db.set_balance(_ref, db.get_balance(_ref) + db.get_settings()[5])
                await bot.send_message(chat_id=admin_id,
                                       text=f"Новый пользователь: {_user_id} (@{_username})\nПригласил: {_ref}")
                await bot.send_message(chat_id=_ref,
                                       text=f"*Кто-то перешел по твоей ссылке!*\nБаланс пополнен на {db.get_settings()[5]}",
                                       parse_mode='Markdown')
            else:
                db.add_user_to_db(message.chat.id, message.chat.username, 0, db.get_settings()[4])
                await bot.send_message(chat_id=admin_id, text=f"Новый пользователь: {_user_id} (@{_username})")
        else:
            db.add_user_to_db(message.chat.id, message.chat.username, 0, db.get_settings()[4])
            await bot.send_message(chat_id=admin_id, text=f"Новый пользователь: {_user_id} (@{_username})")
    db.update_nickname(_user_id, _username)
    await message.answer(profile(_user_id), reply_markup=reply_keyboard(), parse_mode="HTML")
    await States.menu.set()

# Define a handler for adding balance option in the main menu
@dp.message_handler(text=["💵 Пополнить баланс"], state=States.menu)
async def menu(message: types.Message, state: FSMContext):
    _user_id = message.chat.id
    _username = message.chat.username
    await message.answer(f"💵 *Введите сумму пополнения*", reply_markup=just_back(), parse_mode="Markdown")
    await States.pay.set()

# Define a handler for the payment state
@dp.message_handler(state=States.pay)
async def menu(message: types.Message, state: FSMContext):
    if (message.text.isdigit()):
        if (int(message.text) >= 10 and int(message.text) <= 500):
            _code = 99 if db.get_settings()[1].isdigit() else 99999
            _user_id = message.chat.id
            _username = message.chat.username
            _random = random_order()
            await message.answer(f"""
*📈 Пополнение ID{_random}*

*Для оплаты перейдите по кнопке ниже*
""",
                                 reply_markup=inline_keyboard(message.text, _random, _code), parse_mode="Markdown")
            await States.pay_sum.set()
            await States.menu.set()
        else:
            await message.answer(f"*Введите сумму от 10₽ до 500₽*", reply_markup=just_back(), parse_mode="Markdown")
    else:
        await message.answer(f"*Введите сумму числом*", reply_markup=just_back(), parse_mode="Markdown")

# Define a handler for admin commands
@dp.message_handler(commands="admin", state="*")
async def admin_menu(message: types.Message, state: FSMContext):
    if (message.chat.id == admin_id):
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(text="📬 Рассылка", callback_data=f"admin_mail"))
        _settings = db.get_settings()
        await message.answer(f"""💼 *Меню администратора*

👥 Пользователей всего: {len(db.get_all_users())}
👤 За неделю: {len(db.get_old_users(7))}
👤 За день: {len(db.get_old_users(1))}

🖼 Видео: {len(db.get_all_files('video'))}
🖼 Фото: {len(db.get_all_files('photo'))}

📝 *Настройки*

Qiwi - {_settings[1]}
Цена видео - {_settings[2]}
Цена фото - {_settings[3]}
Начальный баланс - {_settings[4]}
Бонус рефки - {_settings[5]}

*/help_admin* - Список команд админа
""", parse_mode="Markdown", reply_markup=keyboard)


# Define handlers for changing settings using admin commands
@dp.message_handler(commands=["qiwi", "video", "photo", "stbal", "bonus"], state="*")
async def admin_menu(message: types.Message, state: FSMContext):
    if (message.chat.id == admin_id):
        if (message.text.count(" ") > 0):
            _data = message.text.split(" ")
            _command = _data[0][1:]
            _value = _data[1]
            if (_value.isdigit() or _command == "qiwi"):
                db.update_settings(_command, _value)
                await message.answer(f"✅ Значение {_command} изменено на {_value}", parse_mode="Markdown")
            else:
                await bot.send_message(message.chat.id, f"Неверный формат команды")
        else:
            await bot.send_message(message.chat.id, f"Неверный формат команды")


# Define a handler for displaying admin commands
@dp.message_handler(commands="help_admin", state="*")
async def admin_help(message: types.Message, state: FSMContext):
    if (message.chat.id == admin_id):
        await message.answer(f'''💼 *Команды админа*

*/help_admin* - Список команд админа
*/top* - Рейтинг пользователей
*/pay 123 999* - Пополнение пользователю с ID 123 на 999
*/pay all 100* - Пополнение всем
*/info 123* - Информация о пользователе с ID 123

*/get 123* - Получить файл с ID 123
*/del 123* - Удалить файл с ID 123
*/dump* - Получить все файлы

*Чтобы загрузить новые файлы, отправьте их боту по одному*

📝 *Изменение настроек*

*/qiwi 89876543210* - номер Qiwi
*/video 123* - стоимость видео
*/photo 123* - стоимость фото
*/stbal 123* - начальный баланс
*/bonus 123* - бонус за приглашение
''', parse_mode="Markdown")


# Define a handler for getting and displaying all files
@dp.message_handler(commands="dump", state="*")
async def admin_get_all_files(message: types.Message, state: FSMContext):
    if (message.chat.id == admin_id):
        if message.text.startswith("/dump "):
            _type = message.text.replace("/dump ", "")
            files = db.get_all_files(_type)
        else:
            files = db.get_all_files()
        for file in files:
            if file[2] == 'photo':
                await bot.send_photo(message.chat.id, file[1], f"{file[2]} {file[0]}\nАвтор: {file[3]}")
            elif file[2] == 'video':
                await bot.send_video(message.chat.id, file[1], f"{file[2]} {file[0]}\nАвтор: {file[3]}")


# Define a callback query handler for admin mailing
@dp.callback_query_handler(state=States.admin_mail_accept)
async def admin_mail(call: types.CallbackQuery, state: FSMContext):
    if (call.data == "admin_back_2"):
        for i in range(4):
            await bot.delete_message(call.from_user.id, call.message.message_id - i)
        await States.menu.set()
        await bot.send_message(call.from_user.id, "Отменено")
    elif (call.from_user.id == admin_id):
        if (call.data == "admin_mail_accept"):
            _data = await state.get_data()
            text = _data['text']
            _type = _data['type']
            photo = _data['photo']
            users = db.get_all_users()
            a = 0
            for user in users:
                try:
                    if (_type == 'text_only'):
                        await bot.send_message(user[0], text, parse_mode="HTML")
                    elif (_type == 'photo'):
                        await bot.send_photo(user[0], photo, text, parse_mode="HTML")
                    a += 1
                    time.sleep(0.1)
                except:
                    pass
            for i in range(4):
                await bot.delete_message(call.from_user.id, call.message.message_id - i)
            await States.menu.set()
            await bot.send_message(call.from_user.id, f"✅ Рассылка успешно завершена\nПолучили {a} пользователей")


# Define a callback query handler for admin commands
@dp.callback_query_handler(state="*")
async def admin_calls(call: types.CallbackQuery, state: FSMContext):
    if (call.from_user.id == admin_id):
        if (call.data == "admin_back"):
            await bot.delete_message(call.from_user.id, call.message.message_id)
            await States.menu.set()
            await bot.send_message(call.from_user.id, "Отменено")
        elif (call.data == "admin_mail"):
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton(text="❌ Назад", callback_data=f"admin_back"))
            await bot.send_message(call.from_user.id, "Введите текст рассылки: ", reply_markup=keyboard)
            await States.admin_mail.set()
        await call.answer()


# Define a message handler for admin mailing text
@dp.message_handler(state=States.admin_mail)
async def admin_mail(message: types.Message, state: FSMContext):
    if (message.chat.id == admin_id):
        try:
            text = message.text
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton(text="✅ Начать", callback_data=f"admin_mail_accept"))
            keyboard.add(InlineKeyboardButton(text="❌ Назад", callback_data=f"admin_back_2"))
            await state.update_data(text=text)
            await state.update_data(photo=-1)
            await States.admin_mail_accept.set()
            await bot.send_message(message.chat.id, text, parse_mode="HTML")
            await bot.send_message(message.chat.id, f"Начать рассылку для {len(db.get_all_users())} пользователей?",
                                   reply_markup=keyboard)
            await state.update_data(type='text_only')
        except:
            await bot.send_message(message.chat.id, f"❌ Неверный текст")


# Define a message handler for admin mailing photo
@dp.message_handler(content_types=types.ContentTypes.PHOTO, state=States.admin_mail)
async def admin_mail_photo(message: types.Message, state: FSMContext):
    if (message.chat.id == admin_id):
        try:
            text = message.caption
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton(text="✅ Начать", callback_data=f"admin_mail_accept"))
            keyboard.add(InlineKeyboardButton(text="❌ Назад", callback_data=f"admin_back_2"))
            await state.update_data(text=text)
            await state.update_data(photo=message.photo[-1].file_id)
            await States.admin_mail_accept.set()
            await bot.send_photo(message.chat.id, message.photo[-1].file_id, text, parse_mode="HTML")
            await bot.send_message(message.chat.id, f"Начать рассылку для {len(db.get_all_users())} пользователей?",
                                   reply_markup=keyboard)
            await state.update_data(type='photo')
        except:
            await bot.send_message(message.chat.id, f"❌ Неверный текст")


# Define a message handler for admin user information command
@dp.message_handler(commands="info", state="*")
async def admin_info(message: types.Message, state: FSMContext):
    if (message.chat.id == admin_id):
        _ID = message.text.replace("/info ", "")
        _data = db.get_info(_ID)
        if not (_ID.isdigit()):
            await bot.send_message(message.chat.id, f"Неверный формат команды")
        elif (_data == None):
            await bot.send_message(message.chat.id, f"❌ Пользователь не найден")
        else:
            await message.answer(get_user_info(_ID), reply_markup=reply_keyboard(), parse_mode="Markdown")

# Define a message handler for admin top command
@dp.message_handler(commands="top", state="*")
async def admin_top(message: types.Message, state: FSMContext):
    if (message.chat.id == admin_id):
        _text = "<b>💵 Топ по балансу</b>"
        for i in db.get_top_balance(5):
            _text = _text + f"\n{i[5]} | {i[1]} (@{i[2]})"
        _text = _text + "\n\n"
        _text = _text + "<b>👥 Топ по рефералам</b>"
        top_refs = db.get_top_ref(5)
        if top_refs:
            for i in top_refs:
                _temp_name = db.get_info(i[2])[2]
                _text = _text + f"\n{i[0]} | {i[2]} (@{_temp_name})"
        else:
            _text = _text + f"\nНикто никого не пригласил"
        await message.answer(_text, reply_markup=reply_keyboard(), parse_mode="HTML")


# Define a message handler for admin payment command
@dp.message_handler(commands="pay", state="*")
async def admin_pay(message: types.Message, state: FSMContext):
    if (message.chat.id == admin_id):
        _data = message.text.split(" ")
        if (len(_data) > 2):
            _ID = _data[1]
            _sum = _data[2]
            if (_sum.isdigit()) or _sum.replace("-", "").isdigit():
                if (_ID.isdigit()):
                    if (db.get_users_exist(_ID)):
                        db.set_balance(_ID, db.get_balance(_ID) + int(_sum))
                        _info = db.get_info(_ID)
                        await bot.send_message(message.chat.id, f"✅ Баланс {_ID} (@{_info[2]}) пополнен на {_sum}")
                        await bot.send_message(_ID, f"Ваш баланс пополнен на {_sum}")
                    else:
                        await bot.send_message(message.chat.id, f"❌ Пользователь не найден")
                elif (_ID == "all"):
                    users = db.get_all_users()
                    a = 0
                    for user in users:
                        try:
                            db.set_balance(user[0], int(db.get_balance(user[0])) + int(_sum))
                            await bot.send_message(user[0], f"Ваш баланс пополнен на {_sum}")
                            a += 1
                        except:
                            pass
                    await bot.send_message(message.chat.id, f"✅ Баланс {a} пользователей пополнен на {_sum}")
                else:
                    await bot.send_message(message.chat.id, f"Неверный формат команды")
            else:
                await bot.send_message(message.chat.id, f"Неверный формат команды")
        else:
            await bot.send_message(message.chat.id, f"Неверный формат команды")


# The main execution block
if __name__ == "__main__":
    db.check_db()
    executor.start_polling(dp)
