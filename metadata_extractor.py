# metadata_extractor.py

import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
from config import MAX_RETRIES

class MetadataExtractor:
    def __init__(self, client, semaphore):
        self.client = client
        self.semaphore = semaphore

    @retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=1, max=10))
    async def extract(self, text):
        loop = asyncio.get_event_loop()

        async with self.semaphore:
            return await loop.run_in_executor(
                None, self.client.extract, text
            )