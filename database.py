import time
import aiosqlite
from config import DB_PATH


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # --- Пользователи ---
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                phone TEXT,
                last_message_ts INTEGER DEFAULT 0
            )
        """)

        # --- Связка "сообщение в канале поддержки" → "user_id" ---
        await db.execute("""
            CREATE TABLE IF NOT EXISTS support_map (
                support_msg_id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at INTEGER NOT NULL
            )
        """)

        await db.commit()


# ---------- Пользователи ----------

async def upsert_user(user_id: int, username: str | None,
                      full_name: str, phone: str | None = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, username, full_name, phone)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                full_name = excluded.full_name,
                phone = COALESCE(excluded.phone, users.phone)
        """, (user_id, username, full_name, phone))
        await db.commit()


async def get_last_ts(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT last_message_ts FROM users WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def set_last_ts(user_id: int, ts: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET last_message_ts = ? WHERE user_id = ?",
            (ts, user_id)
        )
        await db.commit()


async def get_all_user_ids() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cur:
            rows = await cur.fetchall()
            return [r[0] for r in rows]


async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id, username, full_name, phone FROM users WHERE user_id = ?",
            (user_id,)
        ) as cur:
            return await cur.fetchone()


# ---------- Поддержка ----------

async def save_support_map(support_msg_id: int, user_id: int):
    """Сохраняет связь: сообщение в канале поддержки → ID пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO support_map (support_msg_id, user_id, created_at) "
            "VALUES (?, ?, ?)",
            (support_msg_id, user_id, int(time.time())),
        )
        await db.commit()


async def get_support_user(support_msg_id: int) -> int | None:
    """По ID сообщения в канале поддержки возвращает user_id или None."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id FROM support_map WHERE support_msg_id = ?",
            (support_msg_id,),
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None