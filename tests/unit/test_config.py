"""
tests/unit/test_config.py

Unit tests for application configuration.
"""

import pytest

from ragapp.core.config import Settings


class TestSettings:
    def test_default_values(self):
        """Settings should load with sensible defaults."""
        # TODO: instantiate Settings(), verify app_name, environment, port
        pass

    def test_environment_override(self):
        """Settings should accept environment variable overrides."""
        # TODO: use monkeypatch to set ENV vars, verify Settings picks them up
        pass

    def test_chunk_settings(self):
        """Chunk size and overlap should have defaults."""
        # TODO: verify chunk_size=1000, chunk_overlap=200
        pass
