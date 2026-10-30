import os
import ssl
import asyncpg

# Получаем ссылку на базу данных из переменных окружения
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("Переменная DATABASE_URL не найдена!")

pool = None

async def init_db():
    global pool
    
    # Настраиваем SSL для безопасного подключения к Supabase
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    # Создаем пул соединений
    pool = await asyncpg.create_pool(DATABASE_URL, ssl=ssl_ctx)
    
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                score INTEGER DEFAULT 0
            )
        """)

async def close_db():
    if pool:
        await pool.close()

async def add_user(user_id: int, username: str):
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (user_id, username) VALUES ($1, $2) 
            ON CONFLICT (user_id) DO NOTHING
        """, user_id, username)

async def update_score(user_id: int, points: int):
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET score = score + $1 WHERE user_id = $2", 
            points, user_id
        )

async def get_top_players(limit: int = 5):
    async with pool.acquire() as conn:
        # Возвращает список объектов Record, работающих как кортежи
        return await conn.fetch(
            "SELECT username, score FROM users ORDER BY score DESC LIMIT $1", 
            limit
        )
