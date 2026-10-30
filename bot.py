import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import database # Импортируем наш файл

TOKEN = "ТВОЙ_ТОКЕН"
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start_handler(message: types.Message):
  # Регистрируем пользователя в БД
  await database.add_user(
    user_id=message.from_user.id,
    username=message.from_user.first_name
  )
  keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="♟ Шахматы", web_app=WebAppInfo(url="https://твой-домен/chess"))]
  ])

  await message.answer("Выбирай игру:", reply_markup=keyboard)

@dp.message(Command("top"))
async def top_handler(message: types.Message):
  top_players = await database.get_top_players(5)

if not top_players:
    await message.answer("Таблица лидеров пока пуста.")
    return

  text = "🏆 <b>Топ-5 игроков:</b>\n\n"
  for i, (name, score) in enumerate(top_players, start=1):
      text += f"{i}. {name} — {score} очков\n"
    
  await message.answer(text, parse_mode="HTML")

async def main():
  # Создаем таблицы до запуска бота
  await database.init_db()
  await dp.start_polling(bot)

if name == "main":
  asyncio.run(main())
