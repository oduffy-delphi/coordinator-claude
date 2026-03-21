"""Tests for corpus loading and validation."""

from pathlib import Path

from review_experiments.corpus import Corpus

FIXTURES = Path(__file__).parent / "fixtures" / "corpus"


def test_load_corpus():
    corpus = Corpus(FIXTURES)
    assert len(corpus.file_ids()) == 2
    assert "file_001" in corpus.file_ids()
    assert "file_002" in corpus.file_ids()


def test_read_file():
    corpus = Corpus(FIXTURES)
    content = corpus.read_file("file_001")
    assert "authenticate" in content
    assert "def authenticate" in content


def test_defect_manifest():
    corpus = Corpus(FIXTURES)
    manifest = corpus.defect_manifest
    assert manifest.experiment == "test"
    assert len(manifest.defects) == 5
    file_001_defects = manifest.defects_for_file("file_001.py")
    assert len(file_001_defects) == 3


def test_distractor_manifest():
    corpus = Corpus(FIXTURES)
    distractors = corpus.distractor_manifest
    assert distractors is not None
    assert len(distractors.distractors) == 1


def test_manifest_sha256():
    corpus = Corpus(FIXTURES)
    sha = corpus.manifest_sha256()
    assert len(sha) == 64  # SHA256 hex digest length


def test_validate_clean():
    corpus = Corpus(FIXTURES)
    errors = corpus.validate()
    assert errors == [], f"Validation errors: {errors}"


def test_validate_missing_path():
    corpus = Corpus(Path("/nonexistent/path"))
    errors = corpus.validate()
    assert len(errors) > 0
    assert "does not exist" in errors[0]
