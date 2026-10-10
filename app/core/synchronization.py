import asyncio
from functools import wraps


sync_lock = asyncio.Lock()


def serialized_sync(function):
    @wraps(function)
    async def wrapped(*args, **kwargs):
        async with sync_lock:
            return await function(*args, **kwargs)
    return wrapped
