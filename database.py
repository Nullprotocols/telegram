# database.py
import aiosqlite
from datetime import datetime, timedelta

DB_PATH = "bot.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_seen TEXT,
                last_seen TEXT,
                total_lookups INTEGER
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS banned (
                user_id INTEGER PRIMARY KEY
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS lookups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                command TEXT,
                query TEXT,
                result TEXT,
                timestamp TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT,
                command TEXT,
                count INTEGER,
                PRIMARY KEY (date, command)
            )
        """)
        await db.commit()

async def add_user(user_id: int, first_seen: str, last_seen: str, total_lookups: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, first_seen, last_seen, total_lookups) VALUES (?, ?, ?, ?)",
            (user_id, first_seen, last_seen, total_lookups)
        )
        await db.commit()

async def update_user(user_id: int, last_seen: str, increment: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET last_seen = ?, total_lookups = total_lookups + ? WHERE user_id = ?",
            (last_seen, increment, user_id)
        )
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return await cursor.fetchone()

async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM users")
        return [row[0] for row in await cursor.fetchall()]

async def get_recent_users(limit: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id, last_seen FROM users ORDER BY last_seen DESC LIMIT ?", (limit,))
        return await cursor.fetchall()

async def get_user_lookups(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT * FROM lookups WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
        return await cursor.fetchall()

async def get_leaderboard(limit: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id, total_lookups FROM users ORDER BY total_lookups DESC LIMIT ?", (limit,))
        return await cursor.fetchall()

async def get_inactive_users():
    threshold = (datetime.utcnow() - timedelta(days=30)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id, last_seen FROM users WHERE last_seen < ?", (threshold,))
        return await cursor.fetchall()

async def get_total_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        users = (await cursor.fetchone())[0]
        cursor = await db.execute("SELECT COUNT(*) FROM lookups")
        lookups = (await cursor.fetchone())[0]
        return {"users": users, "lookups": lookups}

async def get_daily_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT date, SUM(count) FROM daily_stats GROUP BY date ORDER BY date DESC LIMIT 30")
        return await cursor.fetchall()

async def get_lookup_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT command, SUM(count) FROM daily_stats GROUP BY command")
        return await cursor.fetchall()

async def add_lookup(user_id: int, command: str, query: str, result: str, timestamp: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO lookups (user_id, command, query, result, timestamp) VALUES (?, ?, ?, ?, ?)",
            (user_id, command, query, result, timestamp)
        )
        await db.commit()

async def increment_daily_stat(date: str, command: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO daily_stats (date, command, count) VALUES (?, ?, COALESCE((SELECT count FROM daily_stats WHERE date = ? AND command = ?), 0) + 1)",
            (date, command, date, command)
        )
        await db.commit()

async def is_banned(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT 1 FROM banned WHERE user_id = ?", (user_id,))
        return bool(await cursor.fetchone())

async def ban_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO banned (user_id) VALUES (?)", (user_id,))
        await db.commit()

async def unban_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM banned WHERE user_id = ?", (user_id,))
        await db.commit()

async def delete_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM lookups WHERE user_id = ?", (user_id,))
        await db.commit()

async def is_admin(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
        return bool(await cursor.fetchone())

async def add_admin(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
        await db.commit()

async def remove_admin(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        await db.commit()

async def get_all_admins():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM admins")
        return await cursor.fetchall()

async def search_user(query: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT * FROM users WHERE user_id LIKE ? OR first_seen LIKE ? OR last_seen LIKE ?",
            (f"%{query}%", f"%{query}%", f"%{query}%")
        )
        return await cursor.fetchall()
