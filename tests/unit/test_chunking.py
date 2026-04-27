"""
tests/unit/test_chunking.py

Unit tests for the text chunking service.
"""

import pytest

from ragapp.services.chunking import chunk_text, Chunk


class TestChunkText:
    def test_empty_text_returns_no_chunks(self):
        """Empty or whitespace-only text should return an empty list."""
        # TODO: call chunk_text with empty string, assert result == []
        pass

    def test_short_text_returns_single_chunk(self):
        """Text shorter than chunk_size should produce exactly one chunk."""
        # TODO: call chunk_text with short text, assert len(result) == 1
        pass

    def test_long_text_produces_multiple_chunks(self):
        """Text longer than chunk_size should produce multiple overlapping chunks."""
        # TODO: call chunk_text with long text, assert len(result) > 1
        pass

    def test_chunks_contain_correct_document_id(self):
        """Each chunk should reference the parent document_id."""
        # TODO: assert all chunks have the correct document_id
        pass

    def test_chunk_overlap_produces_overlapping_content(self):
        """Adjacent chunks should share overlapping text."""
        # TODO: verify overlap between consecutive chunks
        pass

    def test_chunk_ids_are_unique(self):
        """Each chunk should have a globally unique chunk_id."""
        # TODO: collect all chunk_ids and assert no duplicates
        pass
