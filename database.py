import aiosqlite

DB_NAME = "games.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                score INTEGER DEFAULT 0
            )
        """)
        await db.commit()

async def add_user(user_id: int, username: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username)
        )
        await db.commit()

async def update_score(user_id: int, points: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET score = score + ? WHERE user_id = ?",
            (points, user_id)
        )
        await db.commit()

async def get_top_players(limit: int = 5):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT username, score FROM users ORDER BY score DESC LIMIT ?", 
            (limit,)
        ) as cursor:
            return await cursor.fetchall()
