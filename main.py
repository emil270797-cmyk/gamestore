import asyncio
import hmac
import hashlib
import json
import os
from urllib.parse import parse_qsl
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
А
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

import database

# Загружаем токен бота из переменных окружения
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("Переменная BOT_TOKEN не найдена!")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Управление жизненным циклом (запуск БД и фонового бота)
@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.init_db()
    task = asyncio.create_task(dp.start_polling(bot))
    yield
    await bot.session.close()
    task.cancel()
    await database.close_db()

app = FastAPI(lifespan=lifespan)

# Разрешаем запросы от игр, размещенных на других доменах
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Для большей безопасности можно указать ["https://emil270797-cmyk.github.io/checkers/"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Проверка подлинности данных от Telegram
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

# Эндпоинт, на который игра отправляет результаты
@app.post("/api/save_score")
async def save_score(request: ScoreRequest):
    user_data = validate_webapp_data(request.initData, TOKEN)
    await database.update_score(user_id=user_data["id"], points=request.points)
    
    return {
        "status": "success", 
        "user_id": user_data["id"], 
        "added_points": request.points
    }

# ================= ЛОГИКА БОТА ================= #

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    # Регистрируем пользователя при старте
    await database.add_user(message.from_user.id, message.from_user.first_name)
    
    # Ссылки на веб-версии твоих игр (замени на свои URL)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="♟ Шахматы", web_app=WebAppInfo(url="https://твой-домен/chess.html"))],
        [InlineKeyboardButton(text="🔴 Шашки", web_app=WebAppInfo(url="https://твой-домен/checkers.html"))],
        [InlineKeyboardButton(text="🎲 Нарды", web_app=WebAppInfo(url="https://твой-домен/backgammon.html"))]
    ])
    
    await message.answer("Добро пожаловать в Магазин Игр! 🎮\nВыбирай игру:", reply_markup=keyboard)

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
