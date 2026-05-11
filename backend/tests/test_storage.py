"""Tests for storage service pure helpers (Phase 2)."""
import pytest

from app.services.storage import MAX_FILE_SIZE_BYTES, _ALLOWED_MIME_TYPES


class TestStorageConstants:
    def test_max_file_size_is_20mb(self):
        assert MAX_FILE_SIZE_BYTES == 20 * 1024 * 1024

    def test_pdf_allowed(self):
        assert "application/pdf" in _ALLOWED_MIME_TYPES

    def test_jpeg_allowed(self):
        assert "image/jpeg" in _ALLOWED_MIME_TYPES

    def test_png_allowed(self):
        assert "image/png" in _ALLOWED_MIME_TYPES

    def test_plain_text_allowed(self):
        assert "text/plain" in _ALLOWED_MIME_TYPES

    def test_exe_not_allowed(self):
        assert "application/x-msdownload" not in _ALLOWED_MIME_TYPES

    def test_zip_not_allowed(self):
        assert "application/zip" not in _ALLOWED_MIME_TYPES

    def test_html_not_allowed(self):
        assert "text/html" not in _ALLOWED_MIME_TYPES

    def test_minimum_allowed_types(self):
        # At least PDF + 2 image formats must be supported
        assert len(_ALLOWED_MIME_TYPES) >= 3
