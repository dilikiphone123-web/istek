import asyncio
import logging
import os
import json

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

import gspread
from google.oauth2.service_account import Credentials

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")

# ================= LOGGING =================
logging.basicConfig(level=logging.INFO)

# ================= GOOGLE SHEETS =================
def init_google():
    creds_dict = json.loads(GOOGLE_CREDENTIALS)
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1
    return sheet

sheet = init_google()

# ================= FSM =================
class Survey(StatesGroup):
    q1 = State()
    q2 = State()
    q3 = State()
    photo = State()

# ================= BOT =================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ================= KEYBOARDS =================
def yes_no_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👍 Да"), KeyboardButton(text="👎 Нет")]
        ],
        resize_keyboard=True
    )

# ================= HANDLERS =================

@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("👋 Привет! Начнём опрос.\n\n1. Вам понравился сервис?", reply_markup=yes_no_kb())
    await state.set_state(Survey.q1)

@dp.message(Survey.q1)
async def q1(message: types.Message, state: FSMContext):
    await state.update_data(q1=message.text)
    await message.answer("2. Всё ли было понятно?", reply_markup=yes_no_kb())
    await state.set_state(Survey.q2)

@dp.message(Survey.q2)
async def q2(message: types.Message, state: FSMContext):
    await state.update_data(q2=message.text)
    await message.answer("3. Будете рекомендовать?", reply_markup=yes_no_kb())
    await state.set_state(Survey.q3)

@dp.message(Survey.q3)
async def q3(message: types.Message, state: FSMContext):
    await state.update_data(q3=message.text)
    await message.answer("📸 Отправьте фото (или /skip)")
    await state.set_state(Survey.photo)

@dp.message(Command("skip"), Survey.photo)
async def skip_photo(message: types.Message, state: FSMContext):
    await finish(message, state, photo=None)

@dp.message(F.photo, Survey.photo)
async def get_photo(message: types.Message, state: FSMContext):
    photo = message.photo[-1].file_id
    await finish(message, state, photo=photo)

# ================= FINISH =================
async def finish(message: types.Message, state: FSMContext, photo=None):
    data = await state.get_data()

    # Save to Google Sheets
    sheet.append_row([
        message.from_user.id,
        message.from_user.username,
        data.get("q1"),
        data.get("q2"),
        data.get("q3")
    ])

    # Send to admins
    text = (
        f"📊 Новый опрос:\n\n"
        f"User: @{message.from_user.username}\n"
        f"1: {data.get('q1')}\n"
        f"2: {data.get('q2')}\n"
        f"3: {data.get('q3')}"
    )

    for admin in ADMIN_IDS:
        if photo:
            await bot.send_photo(admin, photo, caption=text)
        else:
            await bot.send_message(admin, text)

    await message.answer("✅ Спасибо за участие!")
    await state.clear()

# ================= CANCEL =================
@dp.message(Command("cancel"))
async def cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Опрос отменён")

# ================= MAIN =================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
