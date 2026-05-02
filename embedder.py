# embedder.py

import boto3
import json
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
from config import AWS_REGION, MAX_RETRIES

class BedrockEmbedder:
    def __init__(self):
        self.client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
        self.model_id = "amazon.titan-embed-text-v1"

    @retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=1, max=10))
    def _embed_sync(self, text):
        body = json.dumps({"inputText": text})

        response = self.client.invoke_model(
            body=body,
            modelId=self.model_id,
            accept="application/json",
            contentType="application/json"
        )

        result = json.loads(response["body"].read())
        return result["embedding"]

    async def embed(self, text):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._embed_sync, text)