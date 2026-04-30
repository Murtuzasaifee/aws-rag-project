"""
tests/unit/test_chunking.py

Unit tests for the text chunking service.
"""

from ragapp.services.chunking import Chunk, RecursiveChunker, chunk_text

class TestChunkText:
    def test_empty_text_returns_no_chunks(self):
        assert chunk_text("", "doc-1") == []

    def test_short_text_returns_single_chunk(self):
        text = "Hello world."
        chunks = chunk_text(text, "doc-1", chunk_size=100, chunk_overlap=10)

        assert len(chunks) == 1
        assert chunks[0].content == text
        assert chunks[0].document_id == "doc-1"

    def test_long_text_produces_multiple_chunks(self):
        text = "This is a sentence. " * 40
        chunks = chunk_text(text, "doc-1", chunk_size=20, chunk_overlap=5)

        assert len(chunks) > 1

    def test_chunks_contain_correct_document_id(self):
        text = "Hello world. " * 10
        chunks = chunk_text(text, "document-42", chunk_size=20, chunk_overlap=5)

        assert all(chunk.document_id == "document-42" for chunk in chunks)

    def test_chunk_overlap_produces_overlapping_content(self):
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        chunks = chunk_text(text, "doc-1", chunk_size=12, chunk_overlap=5)

        assert len(chunks) > 1
        overlap_tokens = set(chunks[0].content.split()).intersection(chunks[1].content.split())
        assert overlap_tokens

    def test_chunk_ids_are_unique(self):
        text = "Sentence one. Sentence two. Sentence three. Sentence four."
        chunks = chunk_text(text, "doc-1", chunk_size=10, chunk_overlap=3)

        assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)

    def test_chunk_metadata_includes_character_offsets_and_source(self):
        text = "Paragraph one.\n\nParagraph two."
        chunks = chunk_text(
            text,
            "doc-1",
            chunk_size=20,
            chunk_overlap=5,
            source_metadata={"source": "unit-test"},
        )

        assert all(chunk.character_offsets is not None for chunk in chunks)
        assert all(chunk.source_metadata.get("source") == "unit-test" for chunk in chunks)

    def test_recursive_chunker_respects_structured_blocks(self):
        text = "```python\nprint(\'line\')\n" * 10 + "```\n\n- bullet one\n- bullet two\n"
        chunks = RecursiveChunker(chunk_size=30, chunk_overlap=5).chunk(text, "doc-1")

        assert chunks
        assert all(chunk.token_count <= 30 for chunk in chunks)
        assert any("```python" in chunk.content or "bullet" in chunk.content for chunk in chunks)

    def test_recursive_chunker_handles_code_table_and_list_blocks(self):
        text = (
            "Paragraph before block.\n\n"
            "```python\nprint(\"hello\")\nfor i in range(3):\n    print(i)\n```\n\n"
            "- list item one\n"
            "- list item two\n\n"
            "| Col1 | Col2 |\n"
            "| ---- | ---- |\n"
            "| a | b |\n"
            "| c | d |\n"
        )

        chunks = chunk_text(text, "doc-structured", strategy="recursive", chunk_size=40, chunk_overlap=10)

        assert chunks
        assert all(chunk.token_count <= 40 for chunk in chunks)
        assert any("```python" in chunk.content for chunk in chunks)
        assert any("- list item" in chunk.content for chunk in chunks)
        assert any("| Col1 | Col2 |" in chunk.content or "| a | b |" in chunk.content for chunk in chunks)
        assert any(chunk.source_metadata == {} for chunk in chunks)
