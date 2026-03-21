"""JSON-per-call persistence with crash-resume support.

Each API call saves immediately to:
    results/runs/{experiment_id}/{arm}/{file_stem}/run_{n}.json

The runner checks exists() before each call to skip completed work.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..schemas import APICallRecord, ReviewOutput
from .config import RESULTS_DIR


class ResultStore:
    """Manages per-call result persistence on disk."""

    def __init__(self, experiment_id: str, base_dir: Path | None = None) -> None:
        self.experiment_id = experiment_id
        self.base_dir = (base_dir or RESULTS_DIR) / "runs" / experiment_id

    def _result_path(self, arm: str, file_stem: str, run_index: int) -> Path:
        return self.base_dir / arm / file_stem / f"run_{run_index}.json"

    def exists(self, arm: str, file_stem: str, run_index: int) -> bool:
        """Check whether a result already exists (for crash-resume)."""
        return self._result_path(arm, file_stem, run_index).is_file()

    def save(
        self,
        arm: str,
        file_stem: str,
        run_index: int,
        review: ReviewOutput,
        call_record: APICallRecord,
    ) -> Path:
        """Persist a single API call result to disk.

        Returns the path written to.
        """
        path = self._result_path(arm, file_stem, run_index)
        path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "review": review.model_dump(mode="json"),
            "call_record": call_record.model_dump(mode="json"),
        }
        path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        return path

    def load(self, arm: str, file_stem: str, run_index: int) -> dict:
        """Load a previously saved result."""
        path = self._result_path(arm, file_stem, run_index)
        return json.loads(path.read_text(encoding="utf-8"))

    def completed_runs(self, arm: str, file_stem: str) -> list[int]:
        """Return sorted list of completed run indices for a given arm/file."""
        arm_dir = self.base_dir / arm / file_stem
        if not arm_dir.is_dir():
            return []
        indices = []
        for p in arm_dir.glob("run_*.json"):
            try:
                idx = int(p.stem.split("_", 1)[1])
                indices.append(idx)
            except (ValueError, IndexError):
                continue
        return sorted(indices)

    def count_total(self) -> int:
        """Count all completed results across all arms/files."""
        if not self.base_dir.is_dir():
            return 0
        return sum(1 for _ in self.base_dir.rglob("run_*.json"))
