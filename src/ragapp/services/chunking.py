"""
src/ragapp/services/chunking.py

Text chunking strategies for document processing.
"""

import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

try:
    import tiktoken
except ImportError:  # pragma: no cover
    tiktoken = None

DEFAULT_CHUNK_SIZE_TOKENS = 512
DEFAULT_CHUNK_OVERLAP_TOKENS = 50
DEFAULT_EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2"
_PARAGRAPH_BOUNDARIES = ["\n\n", ". ", "? ", "! ", "\n"]


@dataclass
class Chunk:
    chunk_id: str
    content: str
    document_id: str
    chunk_index: int = 0
    page_number: int | None = None
    character_offsets: tuple[int, int] | None = None
    source_metadata: dict[str, Any] | None = None
    token_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "page_number": self.page_number,
            "character_offsets": self.character_offsets,
            "source_metadata": self.source_metadata,
            "token_count": self.token_count,
            "metadata": self.metadata,
        }


class Tokenizer:
    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL_ID):
        self.model_name = model_name
        self._encoding = self._load_encoding(model_name)

    def _load_encoding(self, model_name: str):
        if not tiktoken:
            return None
        try:
            if "titan-embed" in model_name:
                return tiktoken.get_encoding("cl100k_base")
            return tiktoken.encoding_for_model(model_name)
        except Exception:
            return tiktoken.get_encoding("cl100k_base")

    def encode(self, text: str) -> list[int]:
        if self._encoding:
            return self._encoding.encode(text)
        return text.split()

    def count_tokens(self, text: str) -> int:
        return len(self.encode(text))


class ChunkingStrategy(ABC):
    @abstractmethod
    def chunk(
        self,
        text: str,
        document_id: str,
        page_number: int | None = None,
        source_metadata: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        raise NotImplementedError


class FixedWindowChunker(ChunkingStrategy):
    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE_TOKENS,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP_TOKENS,
        tokenizer: Tokenizer | None = None,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.tokenizer = tokenizer or Tokenizer()

    def chunk(
        self,
        text: str,
        document_id: str,
        page_number: int | None = None,
        source_metadata: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        if not text or not text.strip():
            return []

        text = text.strip()
        chunks: list[Chunk] = []
        start_char = 0
        chunk_index = 0
        text_length = len(text)

        while start_char < text_length:
            end_char = self._find_chunk_end(text, start_char)
            if end_char <= start_char:
                end_char = min(text_length, start_char + 1)

            chunk_text = text[start_char:end_char].strip()
            token_count = self.tokenizer.count_tokens(chunk_text)

            if token_count > self.chunk_size:
                end_char = self._find_token_limited_end(text, start_char)
                chunk_text = text[start_char:end_char].strip()
                token_count = self.tokenizer.count_tokens(chunk_text)

            if chunk_text:
                chunks.append(
                    Chunk(
                        chunk_id=f"{document_id}_chunk_{chunk_index}_{uuid.uuid4().hex[:8]}",
                        content=chunk_text,
                        document_id=document_id,
                        page_number=page_number,
                        chunk_index=chunk_index,
                        character_offsets=(start_char, end_char),
                        source_metadata=source_metadata or {},
                        token_count=token_count,
                    )
                )
                chunk_index += 1

            if end_char >= text_length:
                break

            next_start = self._find_overlap_start(text, start_char, end_char)
            if next_start <= start_char:
                next_start = end_char
            start_char = next_start

        return chunks

    def _find_chunk_end(self, text: str, start_char: int) -> int:
        estimated_end = min(len(text), start_char + self.chunk_size * 8)
        for boundary in _PARAGRAPH_BOUNDARIES:
            boundary_pos = text.rfind(boundary, start_char, estimated_end)
            if boundary_pos > start_char + self.chunk_size // 4:
                return boundary_pos + len(boundary)
        return self._find_token_limited_end(text, start_char, estimated_end)

    def _find_token_limited_end(self, text: str, start_char: int, max_end_char: int | None = None) -> int:
        if max_end_char is None:
            max_end_char = len(text)

        lo = start_char + 1
        hi = min(len(text), max_end_char)
        best = lo

        while lo <= hi:
            mid = (lo + hi) // 2
            if self.tokenizer.count_tokens(text[start_char:mid]) <= self.chunk_size:
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1

        return best

    def _find_overlap_start(self, text: str, start_char: int, end_char: int) -> int:
        if self.chunk_overlap <= 0 or end_char <= start_char:
            return end_char

        lo = start_char
        hi = end_char
        best = end_char

        while lo <= hi:
            mid = (lo + hi) // 2
            if self.tokenizer.count_tokens(text[mid:end_char]) <= self.chunk_overlap:
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1

        return best


@dataclass
class DocumentBlock:
    content: str
    block_type: str
    start_char: int
    end_char: int


class RecursiveChunker(ChunkingStrategy):
    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE_TOKENS,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP_TOKENS,
        tokenizer: Tokenizer | None = None,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.tokenizer = tokenizer or Tokenizer()
        self.fallback_chunker = FixedWindowChunker(chunk_size, chunk_overlap, self.tokenizer)

    def chunk(
        self,
        text: str,
        document_id: str,
        page_number: int | None = None,
        source_metadata: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        if not text or not text.strip():
            return []

        text = text.strip()
        blocks = self._split_into_blocks(text)
        chunks: list[Chunk] = []
        chunk_index = 0

        for block in blocks:
            block_chunks = self._chunk_block(block, document_id, page_number, source_metadata)
            for chunk in block_chunks:
                chunk.chunk_index = chunk_index
                chunks.append(chunk)
                chunk_index += 1

        return chunks

    def _chunk_block(
        self,
        block: DocumentBlock,
        document_id: str,
        page_number: int | None,
        source_metadata: dict[str, Any] | None,
    ) -> list[Chunk]:
        if self.tokenizer.count_tokens(block.content) <= self.chunk_size:
            return [
                Chunk(
                    chunk_id=f"{document_id}_chunk_{uuid.uuid4().hex[:8]}",
                    content=block.content.strip(),
                    document_id=document_id,
                    page_number=page_number,
                    chunk_index=0,
                    character_offsets=(block.start_char, block.end_char),
                    source_metadata=source_metadata or {},
                    token_count=self.tokenizer.count_tokens(block.content),
                )
            ]

        sub_blocks = self._split_by_block_type(block)
        if not sub_blocks:
            return self.fallback_chunker.chunk(
                block.content,
                document_id,
                page_number=page_number,
                source_metadata=source_metadata,
            )

        chunks: list[Chunk] = []
        for sub_block in sub_blocks:
            chunks.extend(self._chunk_block(sub_block, document_id, page_number, source_metadata))

        return chunks

    def _split_into_blocks(self, text: str) -> list[DocumentBlock]:
        lines = text.splitlines(keepends=True)
        blocks: list[DocumentBlock] = []
        current_lines: list[str] = []
        current_type: str | None = None
        position = 0

        for line in lines:
            line_type = self._detect_line_type(line)
            if current_type is None:
                current_type = line_type

            if line_type != current_type and current_lines:
                block_text = "".join(current_lines)
                blocks.append(
                    DocumentBlock(
                        content=block_text,
                        block_type=current_type,
                        start_char=position - len(block_text),
                        end_char=position,
                    )
                )
                current_lines = []
                current_type = line_type

            current_lines.append(line)
            position += len(line)

        if current_lines:
            block_text = "".join(current_lines)
            blocks.append(
                DocumentBlock(
                    content=block_text,
                    block_type=current_type or "paragraph",
                    start_char=position - len(block_text),
                    end_char=position,
                )
            )

        return blocks

    def _detect_line_type(self, line: str) -> str:
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            return "code"
        if re.match(r"^\s*([-*+]|(\d+\.))\s+", line):
            return "list"
        if "|" in line and re.search(r"\|.*\|", line):
            return "table"
        if stripped == "":
            return "paragraph"
        return "paragraph"

    def _split_by_block_type(self, block: DocumentBlock) -> list[DocumentBlock]:
        if block.block_type == "code":
            return self._split_code_block(block)
        if block.block_type == "table":
            return self._split_table_block(block)
        if block.block_type == "list":
            return self._split_list_block(block)
        return self._split_paragraph(block)

    def _split_code_block(self, block: DocumentBlock) -> list[DocumentBlock]:
        lines = block.content.splitlines(keepends=True)
        blocks: list[DocumentBlock] = []
        start = block.start_char
        current: list[str] = []
        current_start = start

        for line in lines:
            if line.lstrip().startswith("```") or line.lstrip().startswith("~~~"):
                if current:
                    text = "".join(current)
                    blocks.append(DocumentBlock(text, block.block_type, current_start, current_start + len(text)))
                    current = []
                current_start = start + len(line)
            current.append(line)
            start += len(line)

        if current:
            text = "".join(current)
            blocks.append(DocumentBlock(text, block.block_type, current_start, current_start + len(text)))

        return blocks

    def _split_table_block(self, block: DocumentBlock) -> list[DocumentBlock]:
        lines = block.content.splitlines(keepends=True)
        blocks: list[DocumentBlock] = []
        start = block.start_char
        current: list[str] = []
        current_start = start

        for line in lines:
            if line.strip() == "":
                if current:
                    text = "".join(current)
                    blocks.append(DocumentBlock(text, block.block_type, current_start, current_start + len(text)))
                    current = []
                current_start = start + len(line)
            else:
                current.append(line)
            start += len(line)

        if current:
            text = "".join(current)
            blocks.append(DocumentBlock(text, block.block_type, current_start, current_start + len(text)))

        return blocks

    def _split_list_block(self, block: DocumentBlock) -> list[DocumentBlock]:
        lines = block.content.splitlines(keepends=True)
        blocks: list[DocumentBlock] = []
        start = block.start_char
        current: list[str] = []
        current_start = start

        for line in lines:
            if re.match(r"^\s*([-*+]|(\d+\.))\s+", line):
                if current and not re.match(r"^\s*([-*+]|(\d+\.))\s+", current[-1]):
                    text = "".join(current)
                    blocks.append(DocumentBlock(text, block.block_type, current_start, current_start + len(text)))
                    current = []
                    current_start = start
            current.append(line)
            start += len(line)

        if current:
            text = "".join(current)
            blocks.append(DocumentBlock(text, block.block_type, current_start, current_start + len(text)))

        return blocks

    def _split_paragraph(self, block: DocumentBlock) -> list[DocumentBlock]:
        sentences = re.split(r"(?<=[.!?])\s+", block.content)
        chunks: list[DocumentBlock] = []
        offset = block.start_char

        for sentence in sentences:
            if not sentence:
                continue
            end = offset + len(sentence)
            chunks.append(DocumentBlock(sentence, "paragraph", offset, end))
            offset = end + 1

        return chunks


class ChunkingService:
    STRATEGIES = {
        "fixed_window": FixedWindowChunker,
        "recursive": RecursiveChunker,
    }

    def __init__(
        self,
        strategy: str = "fixed_window",
        chunk_size: int = DEFAULT_CHUNK_SIZE_TOKENS,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP_TOKENS,
        tokenizer: Tokenizer | None = None,
    ):
        if strategy not in self.STRATEGIES:
            raise ValueError(f"Unknown chunking strategy: {strategy}")
        self.strategy_name = strategy
        self.strategy = self.STRATEGIES[strategy](chunk_size, chunk_overlap, tokenizer)

    def chunk(
        self,
        text: str,
        document_id: str,
        page_number: int | None = None,
        source_metadata: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        return self.strategy.chunk(text, document_id, page_number, source_metadata)


def chunk_text(
    text: str,
    document_id: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE_TOKENS,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP_TOKENS,
    page_number: int | None = None,
    source_metadata: dict[str, Any] | None = None,
    strategy: str = "fixed_window",
    tokenizer: Tokenizer | None = None,
) -> list[Chunk]:
    """
    Wrap the chunking service around the desired strategy.
    """
    service = ChunkingService(strategy=strategy, chunk_size=chunk_size, chunk_overlap=chunk_overlap, tokenizer=tokenizer)
    return service.chunk(text, document_id, page_number, source_metadata)
