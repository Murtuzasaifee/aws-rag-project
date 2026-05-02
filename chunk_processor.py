# chunk_processor.py

import asyncio
from config import MAX_TEXT_LENGTH

class ChunkProcessor:
    def __init__(self, embedder, extractor, enricher):
        self.embedder = embedder
        self.extractor = extractor
        self.enricher = enricher

    def _clean_text(self, text):
        return text[:MAX_TEXT_LENGTH]

    async def process(self, chunk):
        text = self._clean_text(chunk["text"])

        embed_task = asyncio.create_task(
            self.embedder.embed(text)
        )

        metadata_task = asyncio.create_task(
            self.extractor.extract(text)
        )

        embedding, raw_meta = await asyncio.gather(
            embed_task, metadata_task
        )

        enriched = self.enricher.enrich(text, raw_meta)

        return {
            "id": chunk["id"],
            "text": text,
            "embedding": embedding,      # TEXT ONLY
            "metadata": enriched         # STORED SEPARATELY
        }