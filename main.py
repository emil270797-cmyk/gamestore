import asyncio
import hmac
import hashlib
import json from urllib.parse import parse_qsl
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

import database
import os

from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
  raise ValueError("Переменная BOT_TOKEN не найдена!")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Жизненный цикл сервера
@asynccontextmanager
async def lifespan(app: FastAPI):
  await database.init_db()
  task = asyncio.create_task(dp.start_polling(bot))
  yield
  await bot.session.close()
  task.cancel()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
  CORSMiddleware,
  allow_origins=[""],
  allow_credentials=True,
  allow_methods=[""],
  allow_headers=["*"],
)
# Валидация данных от Telegram
def validate_webapp_data(init_data: str, token: str) -> dict:
  try:
    parsed_data = dict(parse_qsl(init_data))
    if "hash" not in parsed_data:
      raise ValueError("Hash is missing")
    
    hash_to_check = parsed_data.pop("hash")
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))
    
    secret_key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    
    if calculated_hash != hash_to_check:
        raise ValueError("Invalid hash")
        
    return json.loads(parsed_data["user"])
except Exception as e:
    raise HTTPException(status_code=403, detail=str(e))

class ScoreRequest(BaseModel):
  initData: str
  points: int
  
@app.post("/api/save_score")
async def save_score(request: ScoreRequest):
  user_data = validate_webapp_data(request.initData, TOKEN)
  await database.update_score(user_id=user_data["id"], points=request.points)
  return {"status": "success", "user_id": user_data["id"], "added_points": request.points}

# Логика Telegram-бота
@dp.message(CommandStart())
async def start_handler(message: types.Message):
  await database.add_user(message.from_user.id, message.from_user.first_name)

  keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="♟ Тестовая игра", web_app=WebAppInfo(url="https://твой-домен.github.io/game.html"))]
])
await message.answer("Магазин игр открыт! Выбирай:", reply_markup=keyboard)

@dp.message(Command("top"))
async def top_handler(message: types.Message):
  top_players = await database.get_top_players(5)
  if not top_players:
    await message.answer("Таблица лидеров пуста.")
    return

  text = "🏆 <b>Топ-5 игроков:</b>\n\n"
  for i, (name, score) in enumerate(top_players, start=1):
      text += f"{i}. {name} — {score} очков\n"
  await message.answer(text, parse_mode="HTML")
