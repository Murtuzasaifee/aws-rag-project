# config.py

AWS_REGION = "ap-south-1"

MAX_RETRIES = 3
BATCH_SIZE = 8
MAX_CONCURRENT_REQUESTS = 15

MAX_TEXT_LENGTH = 4500  # safety for Comprehend

DOMAIN_TERMS = ["RAG", "LLM", "Transformer", "Vector Database"]