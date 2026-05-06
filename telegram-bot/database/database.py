import motor.motor_asyncio
from config import MONGO_URI

_client = None


def _get_cols():
    global _client
    if _client is None:
        if not MONGO_URI:
            raise RuntimeError("MONGO_URI is not set.")
        _client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
    db = _client["PostSearchBot"]
    return db["files"], db["users"], db["groups"], db["settings"]


async def ensure_indexes():
    files_col, users_col, groups_col, _ = _get_cols()
    await files_col.create_index([("file_name", "text"), ("caption", "text")])
    await files_col.create_index("file_id", unique=True)
    await users_col.create_index("user_id", unique=True)
    await groups_col.create_index("group_id", unique=True)


async def save_file(file: dict):
    files_col, _, _, _ = _get_cols()
    try:
        await files_col.update_one(
            {"file_id": file["file_id"]},
            {"$set": file},
            upsert=True,
        )
        return True
    except Exception:
        return False


async def search_files(query: str, offset: int = 0, limit: int = 10):
    files_col, _, _, _ = _get_cols()
    cursor = files_col.find(
        {"$text": {"$search": query}},
        {"score": {"$meta": "textScore"}},
    ).sort([("score", {"$meta": "textScore"})]).skip(offset).limit(limit)
    return await cursor.to_list(length=limit)


async def count_files(query: str = "") -> int:
    files_col, _, _, _ = _get_cols()
    if query:
        return await files_col.count_documents({"$text": {"$search": query}})
    return await files_col.count_documents({})


async def delete_file(file_id: str) -> bool:
    files_col, _, _, _ = _get_cols()
    result = await files_col.delete_one({"file_id": file_id})
    return result.deleted_count > 0


async def get_all_files(limit: int = 0):
    files_col, _, _, _ = _get_cols()
    cursor = files_col.find({})
    if limit:
        cursor = cursor.limit(limit)
    return await cursor.to_list(length=None)


async def add_user(user_id: int, username: str = "", full_name: str = ""):
    _, users_col, _, _ = _get_cols()
    await users_col.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id, "username": username, "full_name": full_name}},
        upsert=True,
    )


async def get_all_users():
    _, users_col, _, _ = _get_cols()
    return await users_col.find({}).to_list(length=None)


async def total_users() -> int:
    _, users_col, _, _ = _get_cols()
    return await users_col.count_documents({})


async def add_group(group_id: int, title: str = ""):
    _, _, groups_col, _ = _get_cols()
    await groups_col.update_one(
        {"group_id": group_id},
        {"$set": {"group_id": group_id, "title": title}},
        upsert=True,
    )


async def total_groups() -> int:
    _, _, groups_col, _ = _get_cols()
    return await groups_col.count_documents({})
