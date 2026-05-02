# batch_processor.py

import asyncio
from config import BATCH_SIZE

async def process_batches(chunks, processor):
    results = []

    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i+BATCH_SIZE]

        tasks = [processor.process(c) for c in batch]

        batch_results = await asyncio.gather(
            *tasks, return_exceptions=True
        )

        for r in batch_results:
            if isinstance(r, Exception):
                print("Error:", r)
                continue
            results.append(r)

    return results