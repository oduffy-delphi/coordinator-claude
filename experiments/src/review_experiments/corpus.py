"""Corpus loading, validation, and integrity checking."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .schemas import DefectManifest, DistractorManifest


class CorpusError(Exception):
    """Raised when corpus validation fails."""


class Corpus:
    """Loads and validates an experiment corpus (code files + manifests)."""

    def __init__(self, corpus_path: str | Path):
        self.path = Path(corpus_path)
        self.files_dir = self.path / "files"
        self.manifests_dir = self.path / "manifests"
        self._defect_manifest: DefectManifest | None = None
        self._distractor_manifest: DistractorManifest | None = None

    @property
    def defect_manifest(self) -> DefectManifest:
        if self._defect_manifest is None:
            self._defect_manifest = self._load_defect_manifest()
        return self._defect_manifest

    @property
    def distractor_manifest(self) -> DistractorManifest | None:
        if self._distractor_manifest is None:
            dist_path = self.manifests_dir / "distractors.json"
            if dist_path.exists():
                self._distractor_manifest = self._load_distractor_manifest()
        return self._distractor_manifest

    def file_ids(self) -> list[str]:
        """Return sorted list of corpus file IDs (stem names)."""
        return sorted(f.stem for f in self.files_dir.iterdir() if f.is_file())

    def read_file(self, file_id: str) -> str:
        """Read a corpus file by its ID (stem name)."""
        for f in self.files_dir.iterdir():
            if f.stem == file_id:
                return f.read_text(encoding="utf-8")
        raise CorpusError(f"File not found: {file_id}")

    def file_name(self, file_id: str) -> str:
        """Get the full filename (with extension) for a file ID."""
        for f in self.files_dir.iterdir():
            if f.stem == file_id:
                return f.name
        raise CorpusError(f"File not found: {file_id}")

    def manifest_sha256(self) -> str:
        """Compute SHA256 of the defect manifest for corpus versioning."""
        defect_path = self.manifests_dir / "defects.json"
        content = defect_path.read_bytes()
        return hashlib.sha256(content).hexdigest()

    def validate(self) -> list[str]:
        """Validate corpus integrity. Returns list of error messages (empty = valid)."""
        errors: list[str] = []

        if not self.path.exists():
            errors.append(f"Corpus path does not exist: {self.path}")
            return errors

        if not self.files_dir.exists():
            errors.append(f"Files directory missing: {self.files_dir}")

        defect_path = self.manifests_dir / "defects.json"
        if not defect_path.exists():
            errors.append(f"Defect manifest missing: {defect_path}")
            return errors

        # Load and validate manifest
        try:
            manifest = self.defect_manifest
        except Exception as e:
            errors.append(f"Failed to parse defect manifest: {e}")
            return errors

        # Check all referenced files exist
        file_ids = set(self.file_ids())
        referenced_files = {d.file for d in manifest.defects}
        for ref_file in sorted(referenced_files):
            # Strip extension for comparison
            stem = Path(ref_file).stem
            if stem not in file_ids:
                errors.append(f"Manifest references missing file: {ref_file}")

        # Check defect IDs are unique
        defect_ids = [d.defect_id for d in manifest.defects]
        if len(defect_ids) != len(set(defect_ids)):
            errors.append("Duplicate defect IDs in manifest")

        # Check distractor manifest if present
        if self.distractor_manifest:
            dist_ids = [d.distractor_id for d in self.distractor_manifest.distractors]
            if len(dist_ids) != len(set(dist_ids)):
                errors.append("Duplicate distractor IDs in manifest")

        return errors

    def _load_defect_manifest(self) -> DefectManifest:
        path = self.manifests_dir / "defects.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return DefectManifest(**data)

    def _load_distractor_manifest(self) -> DistractorManifest:
        path = self.manifests_dir / "distractors.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return DistractorManifest(**data)
