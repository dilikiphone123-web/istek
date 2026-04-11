import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ---------------- НАСТРОЙКИ ----------------
API_TOKEN = "YOUR_BOT_TOKEN"
ADMIN_ID = 123456789  # id руководителя

# Google Sheets
scope = ["https://spreadsheets.google.com/feeds"]
creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
client = gspread.authorize(creds)
sheet = client.open("BotData").sheet1

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# ---------------- СОСТОЯНИЯ ----------------
class Form(StatesGroup):
    lang = State()
    name = State()
    phone = State()
    foam = State()
    trash = State()
    rating = State()
    photo = State()
    comment = State()

# ---------------- ТЕКСТЫ ----------------
texts = {
    "ru": {
        "name": "Напишите своё имя:",
        "phone": "👷 Введите свой номер:",
        "foam": "Монтажный шов (пена) без щелей и пустот?",
        "trash": "Мусор после монтажа убрали полностью?",
        "rating": "Оцените качество монтажа:",
        "photo": "📸 Пришлите фото или видео:",
        "comment": "💬 Напишите комментарий:",
        "done": "✅ Спасибо! Данные отправлены."
    },
    "uz": {
        "name": "Ismingizni yozing:",
        "phone": "👷 Telefon raqamingizni kiriting:",
        "foam": "Montaj ko‘pigi bo‘shliqsiz bajarildimi?",
        "trash": "Ishdan keyin chiqindi tozalandi?",
        "rating": "Ish sifatini baholang:",
        "photo": "📸 Rasm yoki video yuboring:",
        "comment": "💬 Izoh qoldiring:",
        "done": "✅ Rahmat! Ma'lumot yuborildi."
    }
}

# ---------------- КНОПКИ ----------------
def lang_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🇷🇺 Русский", "🇺🇿 O‘zbekcha")
    return kb

def yes_no_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("ДА", "НЕТ")
    return kb

def rating_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⭐1","⭐⭐2","⭐⭐⭐3","⭐⭐⭐⭐4","⭐⭐⭐⭐⭐5")
    return kb

# ---------------- СТАРТ ----------------
@dp.message_handler(commands="start")
async def start(msg: types.Message):
    await msg.answer("Выберите язык / Tilni tanlang:", reply_markup=lang_kb())
    await Form.lang.set()

# ---------------- ЯЗЫК ----------------
@dp.message_handler(state=Form.lang)
async def set_lang(msg: types.Message, state: FSMContext):
    if "Русский" in msg.text:
        lang = "ru"
    else:
        lang = "uz"

    await state.update_data(lang=lang)
    await msg.answer(texts[lang]["name"])
    await Form.name.set()

# ---------------- ИМЯ ----------------
@dp.message_handler(state=Form.name)
async def get_name(msg: types.Message, state: FSMContext):
    await state.update_data(name=msg.text)
    data = await state.get_data()
    await msg.answer(texts[data["lang"]]["phone"])
    await Form.phone.set()

# ---------------- ТЕЛЕФОН ----------------
@dp.message_handler(state=Form.phone)
async def get_phone(msg: types.Message, state: FSMContext):
    await state.update_data(phone=msg.text)
    data = await state.get_data()
    await msg.answer(texts[data["lang"]]["foam"], reply_markup=yes_no_kb())
    await Form.foam.set()

# ---------------- ПЕНА ----------------
@dp.message_handler(state=Form.foam)
async def get_foam(msg: types.Message, state: FSMContext):
    await state.update_data(foam=msg.text)
    data = await state.get_data()
    await msg.answer(texts[data["lang"]]["trash"], reply_markup=yes_no_kb())
    await Form.trash.set()

# ---------------- МУСОР ----------------
@dp.message_handler(state=Form.trash)
async def get_trash(msg: types.Message, state: FSMContext):
    await state.update_data(trash=msg.text)
    data = await state.get_data()
    await msg.answer(texts[data["lang"]]["rating"], reply_markup=rating_kb())
    await Form.rating.set()

# ---------------- ОЦЕНКА ----------------
@dp.message_handler(state=Form.rating)
async def get_rating(msg: types.Message, state: FSMContext):
    await state.update_data(rating=msg.text)
    data = await state.get_data()
    await msg.answer(texts[data["lang"]]["photo"])
    await Form.photo.set()

# ---------------- ФОТО ----------------
@dp.message_handler(content_types=["photo", "video"], state=Form.photo)
async def get_photo(msg: types.Message, state: FSMContext):
    file_id = msg.photo[-1].file_id if msg.photo else msg.video.file_id
    await state.update_data(photo=file_id)

    data = await state.get_data()
    await msg.answer(texts[data["lang"]]["comment"])
    await Form.comment.set()

# ---------------- КОММЕНТ ----------------
@dp.message_handler(state=Form.comment)
async def get_comment(msg: types.Message, state: FSMContext):
    await state.update_data(comment=msg.text)
    data = await state.get_data()

    # --- СОХРАНЕНИЕ В GOOGLE SHEETS ---
    sheet.append_row([
        data.get("name"),
        data.get("phone"),
        data.get("foam"),
        data.get("trash"),
        data.get("rating"),
        data.get("comment")
    ])

    # --- ОТПРАВКА АДМИНУ ---
    text = f"""
📊 Новый отчёт

👤 Имя: {data.get("name")}
📞 Телефон: {data.get("phone")}
🧱 Шов: {data.get("foam")}
🧹 Мусор: {data.get("trash")}
⭐ Оценка: {data.get("rating")}
💬 Комментарий: {data.get("comment")}
"""

    await bot.send_message(ADMIN_ID, text)
    await bot.send_photo(ADMIN_ID, data.get("photo"))

    await msg.answer(texts[data["lang"]]["done"])

    await state.finish()

# ---------------- ЗАПУСК ----------------
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
