import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

import gspread
from google.oauth2.service_account import Credentials

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

logging.basicConfig(level=logging.INFO)

# ================= GOOGLE =================
def init_google():
    try:
        creds = Credentials.from_service_account_file(
            "creds.json",
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )

        client = gspread.authorize(creds)
        sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1

        print("✅ Google подключен")
        return sheet

    except Exception as e:
        print("❌ Google error:", e)
        return None


sheet = init_google()

# ================= FSM =================
class Survey(StatesGroup):
    lang = State()
    name = State()
    phone = State()
    manager = State()
    foam = State()
    trash = State()
    rating = State()
    photo = State()
    comment = State()

# ================= BOT =================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ================= KEYBOARDS =================
def lang_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🇷🇺 Русский"), KeyboardButton(text="🇺🇿 O‘zbekcha")]
        ],
        resize_keyboard=True
    )

def yes_no_kb(lang="ru"):
    if lang == "uz":
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="HA"), KeyboardButton(text="YO‘Q")]],
            resize_keyboard=True
        )
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="ДА"), KeyboardButton(text="НЕТ")]],
        resize_keyboard=True
    )

def rating_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(text="⭐1"),
            KeyboardButton(text="⭐⭐2"),
            KeyboardButton(text="⭐⭐⭐3"),
            KeyboardButton(text="⭐⭐⭐⭐4"),
            KeyboardButton(text="⭐⭐⭐⭐⭐5")
        ]],
        resize_keyboard=True
    )

# ================= TEXT =================
TEXTS = {
    "ru": {
        "name": "Напишите своё имя:",
        "phone": "👷 Введите свой номер:",
        "manager": "👨‍💼 Кто ваш менеджер?",
        "foam": "Монтажный шов без щелей?",
        "trash": "Мусор убрали полностью?",
        "rating": "Оцените качество:",
        "photo": "📸 Пришлите фото или видео:",
        "comment": "💬 Напишите свой комментарий. Может вам что-то не понравилось? Или есть предложения по улучшению:",
        "done": "✅ Спасибо! Спасибо, что выбрали ISTEK 🙏"
    },
    "uz": {
        "name": "Ismingizni yozing:",
        "phone": "👷 Telefon raqam:",
        "manager": "👨‍💼 Sizning menejeringiz kim?",
        "foam": "Montaj sifati yaxshi?",
        "trash": "Chiqindi tozalandi?",
        "rating": "Baholang:",
        "photo": "📸 Rasm yoki video yuboring:",
        "comment": "💬 Izoh yozing. Sizga nima yoqmadi? Yoki qanday takliflaringiz bor:",
        "done": "✅ Rahmat! ISTEKni tanlaganingiz uchun rahmat 🙏"
    }
}

# ================= HANDLERS =================

@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Выберите язык / Tilni tanlang:", reply_markup=lang_kb())
    await state.set_state(Survey.lang)

@dp.message(Survey.lang)
async def set_lang(message: types.Message, state: FSMContext):
    lang = "ru" if "Рус" in message.text else "uz"
    await state.update_data(lang=lang)
    await message.answer(TEXTS[lang]["name"])
    await state.set_state(Survey.name)

@dp.message(Survey.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    data = await state.get_data()
    await message.answer(TEXTS[data["lang"]]["phone"])
    await state.set_state(Survey.phone)

@dp.message(Survey.phone)
async def get_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    data = await state.get_data()
    await message.answer(TEXTS[data["lang"]]["manager"])
    await state.set_state(Survey.manager)

@dp.message(Survey.manager)
async def get_manager(message: types.Message, state: FSMContext):
    await state.update_data(manager=message.text)
    data = await state.get_data()
    await message.answer(TEXTS[data["lang"]]["foam"], reply_markup=yes_no_kb(data["lang"]))
    await state.set_state(Survey.foam)

@dp.message(Survey.foam)
async def get_foam(message: types.Message, state: FSMContext):
    await state.update_data(foam=message.text)
    data = await state.get_data()
    await message.answer(TEXTS[data["lang"]]["trash"], reply_markup=yes_no_kb(data["lang"]))
    await state.set_state(Survey.trash)

@dp.message(Survey.trash)
async def get_trash(message: types.Message, state: FSMContext):
    await state.update_data(trash=message.text)
    data = await state.get_data()
    await message.answer(TEXTS[data["lang"]]["rating"], reply_markup=rating_kb())
    await state.set_state(Survey.rating)

@dp.message(Survey.rating)
async def get_rating(message: types.Message, state: FSMContext):
    await state.update_data(rating=message.text)
    data = await state.get_data()
    await message.answer(TEXTS[data["lang"]]["photo"])
    await state.set_state(Survey.photo)

@dp.message(F.photo | F.video, Survey.photo)
async def get_photo(message: types.Message, state: FSMContext):
    file_id = message.photo[-1].file_id if message.photo else message.video.file_id
    await state.update_data(photo=file_id)

    data = await state.get_data()
    await message.answer(TEXTS[data["lang"]]["comment"])
    await state.set_state(Survey.comment)

@dp.message(Survey.comment)
async def finish(message: types.Message, state: FSMContext):
    await state.update_data(comment=message.text)
    data = await state.get_data()

    # Google Sheets
    if sheet:
        try:
            sheet.append_row([
                message.from_user.id,
                data.get("name"),
                data.get("phone"),
                data.get("manager"),
                data.get("foam"),
                data.get("trash"),
                data.get("rating"),
                data.get("comment")
            ])
            print("✅ Записано в таблицу")
        except Exception as e:
            print("❌ Sheets error:", e)
    else:
        print("❌ sheet = None")

    # Admin report
    text = (
        f"📊 Новый отчёт\n\n"
        f"👤 {data.get('name')}\n"
        f"📞 {data.get('phone')}\n"
        f"👨‍💼 Менеджер: {data.get('manager')}\n"
        f"Шов: {data.get('foam')}\n"
        f"Мусор: {data.get('trash')}\n"
        f"⭐ {data.get('rating')}\n"
        f"💬 {data.get('comment')}"
    )

    for admin in ADMIN_IDS:
        try:
            await bot.send_photo(admin, data.get("photo"), caption=text)
        except:
            await bot.send_message(admin, text)

    await message.answer(TEXTS[data["lang"]]["done"])
    await state.clear()

# ================= MAIN =================
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
