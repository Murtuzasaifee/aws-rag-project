# main.py

import asyncio
from comprehend_client import ComprehendClient
from metadata_extractor import MetadataExtractor
from metadata_enricher import MetadataEnricher
from embedder import BedrockEmbedder
from chunk_processor import ChunkProcessor
from batch_processor import process_batches
from config import MAX_CONCURRENT_REQUESTS

async def main():
    chunks = [
        {
            "id": "1",
            "text": "Satya Nadella announced AI innovations at Microsoft Build 2024 in Seattle."
        },
        {
            "id": "2",
            "text": "Google introduced new transformer models in 2023."
        }
    ]

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    comprehend = ComprehendClient()
    extractor = MetadataExtractor(comprehend, semaphore)
    enricher = MetadataEnricher()
    embedder = BedrockEmbedder()

    processor = ChunkProcessor(embedder, extractor, enricher)

    results = await process_batches(chunks, processor)

    for r in results:
        print("\n--- FINAL PAYLOAD ---")
        print(r)

if __name__ == "__main__":
    asyncio.run(main())