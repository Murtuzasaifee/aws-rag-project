"""
src/ragapp/services/chunking.py

Text chunking strategies for document processing.
"""

import uuid
from dataclasses import dataclass


@dataclass
class Chunk:
    chunk_id: str
    content: str
    document_id: str
    page_number: int | None = None
    chunk_index: int = 0
    metadata: dict | None = None


def chunk_text(
    text: str,
    document_id: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    page_number: int | None = None,
) -> list[Chunk]:
    """
    Split text into overlapping chunks using character-based splitting
    with paragraph-boundary awareness.
    """
    if not text.strip():
        return []

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(text):
        end = start + chunk_size

        # Try to break at a paragraph or sentence boundary
        if end < len(text):
            # Look for paragraph break
            newline_pos = text.rfind("\n\n", start, end)
            if newline_pos > start + chunk_size // 2:
                end = newline_pos + 2
            else:
                # Look for sentence break
                for sep in (". ", "? ", "! ", "\n"):
                    sep_pos = text.rfind(sep, start, end)
                    if sep_pos > start + chunk_size // 2:
                        end = sep_pos + len(sep)
                        break

        chunk_text_content = text[start:end].strip()
        if chunk_text_content:
            chunks.append(
                Chunk(
                    chunk_id=f"{document_id}_chunk_{chunk_index}_{uuid.uuid4().hex[:8]}",
                    content=chunk_text_content,
                    document_id=document_id,
                    page_number=page_number,
                    chunk_index=chunk_index,
                )
            )
            chunk_index += 1

        start = end - chunk_overlap
        if start >= len(text):
            break

    return chunks
