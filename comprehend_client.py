# comprehend_client.py

import boto3
from botocore.config import Config
from config import AWS_REGION

class ComprehendClient:
    def __init__(self):
        self.client = boto3.client(
            "comprehend",
            region_name=AWS_REGION,
            config=Config(retries={"max_attempts": 5, "mode": "adaptive"})
        )

    def extract(self, text):
        entities = self.client.detect_entities(Text=text, LanguageCode="en")
        key_phrases = self.client.detect_key_phrases(Text=text, LanguageCode="en")

        return {
            "entities": entities.get("Entities", []),
            "key_phrases": key_phrases.get("KeyPhrases", [])
        }