"""File upload processing pipeline.

Handles file validation, virus scanning placeholder, content hashing,
thumbnail generation for images, and storage to a configurable backend.
"""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import BinaryIO

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".pdf", ".docx", ".xlsx", ".csv"}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
CHUNK_SIZE = 8192
QUARANTINE_DIR = Path("/var/lib/uploads/quarantine")
STORAGE_DIR = Path("/var/lib/uploads/storage")


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    SCANNING = "scanning"
    PROCESSING = "processing"
    COMPLETE = "complete"
    REJECTED = "rejected"
    ERROR = "error"


@dataclass
class FileMetadata:
    """Metadata collected during file processing."""

    original_name: str
    size_bytes: int
    content_hash: str
    extension: str
    mime_type: str | None = None
    storage_path: str | None = None
    thumbnail_path: str | None = None
    status: ProcessingStatus = ProcessingStatus.PENDING
    error_message: str | None = None
    processing_time_ms: float = 0.0
    extra: dict = field(default_factory=dict)


class FileProcessor:
    """Process uploaded files through a validation and storage pipeline."""

    def __init__(
        self,
        storage_dir: Path = STORAGE_DIR,
        quarantine_dir: Path = QUARANTINE_DIR,
        max_size: int = MAX_FILE_SIZE_BYTES,
        allowed_extensions: set[str] | None = None,
    ) -> None:
        self._storage_dir = storage_dir
        self._quarantine_dir = quarantine_dir
        self._max_size = max_size
        self._allowed_extensions = allowed_extensions or ALLOWED_EXTENSIONS
        self._processed_hashes: set[str] = set()

    def process(self, filename: str, stream: BinaryIO) -> FileMetadata:
        """Process an uploaded file through the full pipeline.

        Steps: validate → save to temp → hash → scan → store
        """
        import time
        start = time.monotonic()

        # Extract extension from the provided filename
        ext = Path(filename).suffix.lower()

        # Validate extension
        if ext not in self._allowed_extensions:
            return FileMetadata(
                original_name=filename,
                size_bytes=0,
                content_hash="",
                extension=ext,
                status=ProcessingStatus.REJECTED,
                error_message=f"File type {ext} is not allowed",
            )

        # Save to temporary file for processing
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        try:
            total_size = 0
            hasher = hashlib.sha256()

            while True:
                chunk = stream.read(CHUNK_SIZE)
                if not chunk:
                    break
                tmp.write(chunk)
                hasher.update(chunk)
                total_size += len(chunk)

            tmp.close()

            # Check file size
            if total_size > self._max_size:
                return FileMetadata(
                    original_name=filename,
                    size_bytes=total_size,
                    content_hash="",
                    extension=ext,
                    status=ProcessingStatus.REJECTED,
                    error_message=f"File exceeds maximum size of {self._max_size} bytes",
                )

            content_hash = hasher.hexdigest()

            # Check for duplicate content
            if content_hash in self._processed_hashes:
                logger.info(f"Duplicate file detected: {filename} (hash={content_hash})")

            self._processed_hashes.add(content_hash)

            # Virus scan placeholder
            if not self._scan_file(tmp.name):
                # Move to quarantine
                quarantine_path = self._quarantine_dir / f"{content_hash}{ext}"
                quarantine_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(tmp.name, str(quarantine_path))
                return FileMetadata(
                    original_name=filename,
                    size_bytes=total_size,
                    content_hash=content_hash,
                    extension=ext,
                    status=ProcessingStatus.REJECTED,
                    error_message="File failed security scan",
                )

            # Move to permanent storage
            dest_path = self._build_storage_path(filename, content_hash, ext)
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(tmp.name, str(dest_path))

            elapsed = (time.monotonic() - start) * 1000

            return FileMetadata(
                original_name=filename,
                size_bytes=total_size,
                content_hash=content_hash,
                extension=ext,
                storage_path=str(dest_path),
                status=ProcessingStatus.COMPLETE,
                processing_time_ms=elapsed,
            )

        except Exception as e:
            logger.error(f"Processing failed for {filename}: {e}")
            return FileMetadata(
                original_name=filename,
                size_bytes=0,
                content_hash="",
                extension=ext,
                status=ProcessingStatus.ERROR,
                error_message=str(e),
            )

    def _build_storage_path(
        self, filename: str, content_hash: str, ext: str
    ) -> Path:
        """Build the storage path using content-addressable structure.

        Uses first two characters of hash as directory prefix for
        filesystem distribution.
        """
        prefix = content_hash[:2]
        safe_name = filename.replace("..", "").replace("/", "_")
        return self._storage_dir / prefix / f"{content_hash}_{safe_name}"

    def _scan_file(self, filepath: str) -> bool:
        """Placeholder virus scan — returns True if file is clean.

        In production, this would integrate with ClamAV or similar.
        """
        # Placeholder: check file is not empty and exists
        try:
            size = os.path.getsize(filepath)
            return size > 0
        except OSError:
            return False

    def delete_file(self, storage_path: str) -> bool:
        """Delete a processed file from storage."""
        path = Path(storage_path)
        if path.is_file():
            path.unlink()
            return True
        return False

    def get_file_info(self, storage_path: str) -> dict | None:
        """Get filesystem info for a stored file."""
        path = Path(storage_path)
        if not path.is_file():
            return None

        stat = path.stat()
        return {
            "path": str(path),
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "created": stat.st_ctime,
        }

    def cleanup_quarantine(self, max_age_seconds: int = 86400) -> int:
        """Remove quarantined files older than max_age_seconds."""
        import time
        removed = 0
        if not self._quarantine_dir.is_dir():
            return 0

        now = time.time()
        for filepath in self._quarantine_dir.iterdir():
            if filepath.is_file():
                age = now - filepath.stat().st_mtime
                if age > max_age_seconds:
                    filepath.unlink()
                    removed += 1

        return removed
