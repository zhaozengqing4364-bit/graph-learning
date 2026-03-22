"""Settings repository - app_settings table CRUD."""

import aiosqlite


async def get_setting(db: aiosqlite.Connection, key: str) -> str | None:
    cursor = await db.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
    row = await cursor.fetchone()
    return row[0] if row else None


async def set_setting(db: aiosqlite.Connection, key: str, value: str):
    await db.execute(
        "INSERT OR REPLACE INTO app_settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        (key, value),
    )
    await db.commit()


async def get_all_settings(db: aiosqlite.Connection) -> dict[str, str]:
    cursor = await db.execute("SELECT key, value FROM app_settings")
    return {row[0]: row[1] for row in await cursor.fetchall()}


async def update_settings(db: aiosqlite.Connection, settings: dict[str, str]):
    for key, value in settings.items():
        await set_setting(db, key, value)
