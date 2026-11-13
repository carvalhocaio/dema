import asyncio
from collections.abc import AsyncGenerator, AsyncIterator


async def merge[T](*sources: AsyncIterator[T]) -> AsyncGenerator[T]:
    """Yields items from every source as they arrive, in arrival order."""
    queue: asyncio.Queue[T] = asyncio.Queue()

    async def pump(source: AsyncIterator[T]) -> None:
        async for item in source:
            await queue.put(item)

    tasks = [asyncio.create_task(pump(source)) for source in sources]
    try:
        while True:
            yield await queue.get()
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
