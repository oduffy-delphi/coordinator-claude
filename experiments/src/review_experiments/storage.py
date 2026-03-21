"""SQLite storage layer for experiment results.

All writes use atomic transactions — a crash loses at most one API call.
The checkpoint table enables resume after interruption.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .schemas import (
    APICallRecord,
    FileScore,
    FindingClassification,
    MatchMethod,
    ScoredFinding,
    WorkItem,
    WorkItemStatus,
)

SCHEMA_VERSION = 1

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    experiment TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL DEFAULT 'in_progress',
    config_json TEXT,
    corpus_manifest_sha256 TEXT
);

CREATE TABLE IF NOT EXISTS api_calls (
    call_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    experiment TEXT NOT NULL,
    arm TEXT NOT NULL,
    file_id TEXT NOT NULL,
    step TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cost_usd REAL NOT NULL,
    duration_seconds REAL NOT NULL,
    system_prompt_hash TEXT NOT NULL,
    raw_response TEXT,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id TEXT PRIMARY KEY,
    call_id TEXT NOT NULL REFERENCES api_calls(call_id),
    findings_json TEXT NOT NULL,
    parse_status TEXT NOT NULL DEFAULT 'ok'
);

CREATE TABLE IF NOT EXISTS scores (
    score_id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id TEXT NOT NULL REFERENCES reviews(review_id),
    finding_idx INTEGER NOT NULL,
    classification TEXT NOT NULL,
    matched_defect_id TEXT,
    matched_distractor_id TEXT,
    match_method TEXT NOT NULL,
    match_score REAL  -- numerical similarity that drove the assignment; enables post-hoc threshold sensitivity analysis
);

CREATE TABLE IF NOT EXISTS file_scores (
    file_score_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    experiment TEXT NOT NULL,
    arm TEXT NOT NULL,
    file_id TEXT NOT NULL,
    tp_count INTEGER NOT NULL DEFAULT 0,
    fn_count INTEGER NOT NULL DEFAULT 0,
    fp_count INTEGER NOT NULL DEFAULT 0,
    valid_unexpected_count INTEGER NOT NULL DEFAULT 0,
    recall REAL NOT NULL DEFAULT 0.0,
    precision REAL NOT NULL DEFAULT 0.0,
    f1 REAL NOT NULL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS correction_audits (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    arm TEXT NOT NULL,
    file_id TEXT NOT NULL,
    step TEXT NOT NULL,
    defect_id TEXT NOT NULL,
    fix_attempted INTEGER NOT NULL,
    fix_succeeded INTEGER NOT NULL,
    regression_introduced INTEGER NOT NULL,
    fix_quality TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS checkpoints (
    experiment TEXT NOT NULL,
    run_id TEXT NOT NULL,
    file_id TEXT NOT NULL,
    arm TEXT NOT NULL,
    step TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'completed',
    completed_at TEXT NOT NULL,
    PRIMARY KEY (experiment, run_id, file_id, arm, step)
);

CREATE INDEX IF NOT EXISTS idx_api_calls_run ON api_calls(run_id);
CREATE INDEX IF NOT EXISTS idx_reviews_call ON reviews(call_id);
CREATE INDEX IF NOT EXISTS idx_scores_review ON scores(review_id);
CREATE INDEX IF NOT EXISTS idx_file_scores_run ON file_scores(run_id, experiment, arm);
CREATE INDEX IF NOT EXISTS idx_checkpoints_run ON checkpoints(run_id);
"""


class ExperimentDB:
    """SQLite database for experiment results with checkpoint/resume support."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self) -> None:
        cursor = self._conn.cursor()
        cursor.executescript(SCHEMA_SQL)
        # Check/set schema version
        row = cursor.execute("SELECT version FROM schema_version").fetchone()
        if row is None:
            cursor.execute("INSERT INTO schema_version VALUES (?)", (SCHEMA_VERSION,))
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> ExperimentDB:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    # -------------------------------------------------------------------
    # Runs
    # -------------------------------------------------------------------

    def create_run(
        self,
        run_id: str,
        experiment: str,
        config: dict | None = None,
        corpus_sha256: str | None = None,
    ) -> None:
        self._conn.execute(
            "INSERT INTO runs (run_id, experiment, started_at, status, config_json, corpus_manifest_sha256) "
            "VALUES (?, ?, ?, 'in_progress', ?, ?)",
            (run_id, experiment, _now_iso(), json.dumps(config) if config else None, corpus_sha256),
        )
        self._conn.commit()

    def complete_run(self, run_id: str) -> None:
        self._conn.execute(
            "UPDATE runs SET status = 'completed', completed_at = ? WHERE run_id = ?",
            (_now_iso(), run_id),
        )
        self._conn.commit()

    # -------------------------------------------------------------------
    # Checkpoints
    # -------------------------------------------------------------------

    def is_completed(self, item: WorkItem) -> bool:
        row = self._conn.execute(
            "SELECT status FROM checkpoints "
            "WHERE experiment=? AND run_id=? AND file_id=? AND arm=? AND step=?",
            (item.experiment, item.run_id, item.file_id, item.arm, item.step),
        ).fetchone()
        return row is not None

    def get_checkpoint_status(self, item: WorkItem) -> WorkItemStatus | None:
        row = self._conn.execute(
            "SELECT status FROM checkpoints "
            "WHERE experiment=? AND run_id=? AND file_id=? AND arm=? AND step=?",
            (item.experiment, item.run_id, item.file_id, item.arm, item.step),
        ).fetchone()
        return WorkItemStatus(row[0]) if row else None

    # -------------------------------------------------------------------
    # Atomic record + checkpoint (single transaction)
    # -------------------------------------------------------------------

    def record_review(
        self,
        item: WorkItem,
        api_record: APICallRecord,
        review_id: str,
        findings_json: str,
        parse_status: str,
        scored_findings: list[ScoredFinding],
        file_score: FileScore,
        checkpoint_status: WorkItemStatus = WorkItemStatus.COMPLETED,
        raw_response: str | None = None,
    ) -> None:
        """Atomically record an API call, review, scores, file score, and checkpoint."""
        cursor = self._conn.cursor()
        try:
            cursor.execute("BEGIN")

            # API call
            cursor.execute(
                "INSERT INTO api_calls "
                "(call_id, run_id, experiment, arm, file_id, step, model, "
                "input_tokens, output_tokens, cost_usd, duration_seconds, "
                "system_prompt_hash, raw_response, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    api_record.call_id,
                    api_record.run_id,
                    api_record.experiment,
                    api_record.arm,
                    api_record.file_id,
                    api_record.step,
                    api_record.model,
                    api_record.input_tokens,
                    api_record.output_tokens,
                    api_record.cost_usd,
                    api_record.duration_seconds,
                    api_record.system_prompt_hash,
                    raw_response,
                    api_record.timestamp.isoformat(),
                ),
            )

            # Review
            cursor.execute(
                "INSERT INTO reviews (review_id, call_id, findings_json, parse_status) "
                "VALUES (?, ?, ?, ?)",
                (review_id, api_record.call_id, findings_json, parse_status),
            )

            # Scores
            for idx, sf in enumerate(scored_findings):
                cursor.execute(
                    "INSERT INTO scores "
                    "(review_id, finding_idx, classification, matched_defect_id, "
                    "matched_distractor_id, match_method) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        review_id,
                        idx,
                        sf.classification.value,
                        sf.matched_defect_id,
                        sf.matched_distractor_id,
                        sf.match_method.value,
                    ),
                )

            # File score
            cursor.execute(
                "INSERT INTO file_scores "
                "(run_id, experiment, arm, file_id, tp_count, fn_count, fp_count, "
                "valid_unexpected_count, recall, precision, f1) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    item.run_id,
                    item.experiment,
                    item.arm,
                    item.file_id,
                    len(file_score.true_positives),
                    len(file_score.false_negatives),
                    file_score.fp_distractor + file_score.fp_novel,
                    file_score.valid_unexpected,
                    file_score.recall,
                    file_score.precision,
                    file_score.f1,
                ),
            )

            # Checkpoint
            cursor.execute(
                "INSERT OR REPLACE INTO checkpoints "
                "(experiment, run_id, file_id, arm, step, status, completed_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    item.experiment,
                    item.run_id,
                    item.file_id,
                    item.arm,
                    item.step,
                    checkpoint_status.value,
                    _now_iso(),
                ),
            )

            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def record_api_call_only(
        self,
        item: WorkItem,
        api_record: APICallRecord,
        checkpoint_status: WorkItemStatus = WorkItemStatus.COMPLETED,
        raw_response: str | None = None,
    ) -> None:
        """Record an API call and checkpoint without review scoring (e.g., executor steps)."""
        cursor = self._conn.cursor()
        try:
            cursor.execute("BEGIN")

            cursor.execute(
                "INSERT INTO api_calls "
                "(call_id, run_id, experiment, arm, file_id, step, model, "
                "input_tokens, output_tokens, cost_usd, duration_seconds, "
                "system_prompt_hash, raw_response, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    api_record.call_id,
                    api_record.run_id,
                    api_record.experiment,
                    api_record.arm,
                    api_record.file_id,
                    api_record.step,
                    api_record.model,
                    api_record.input_tokens,
                    api_record.output_tokens,
                    api_record.cost_usd,
                    api_record.duration_seconds,
                    api_record.system_prompt_hash,
                    raw_response,
                    api_record.timestamp.isoformat(),
                ),
            )

            cursor.execute(
                "INSERT OR REPLACE INTO checkpoints "
                "(experiment, run_id, file_id, arm, step, status, completed_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    item.experiment,
                    item.run_id,
                    item.file_id,
                    item.arm,
                    item.step,
                    checkpoint_status.value,
                    _now_iso(),
                ),
            )

            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    # -------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------

    def get_run_progress(self, run_id: str) -> dict:
        """Return completion stats for a run."""
        total = self._conn.execute(
            "SELECT COUNT(*) FROM checkpoints WHERE run_id = ?", (run_id,)
        ).fetchone()[0]
        completed = self._conn.execute(
            "SELECT COUNT(*) FROM checkpoints WHERE run_id = ? AND status = 'completed'",
            (run_id,),
        ).fetchone()[0]
        failed = self._conn.execute(
            "SELECT COUNT(*) FROM checkpoints WHERE run_id = ? AND status = 'parse_failed'",
            (run_id,),
        ).fetchone()[0]
        return {"total": total, "completed": completed, "parse_failed": failed}

    def get_cost_summary(self, run_id: str | None = None) -> dict:
        """Return token usage and cost summary."""
        where = "WHERE run_id = ?" if run_id else ""
        params = (run_id,) if run_id else ()
        row = self._conn.execute(
            f"SELECT SUM(input_tokens), SUM(output_tokens), SUM(cost_usd), COUNT(*) "
            f"FROM api_calls {where}",
            params,
        ).fetchone()
        return {
            "input_tokens": row[0] or 0,
            "output_tokens": row[1] or 0,
            "total_cost_usd": row[2] or 0.0,
            "api_calls": row[3] or 0,
        }

    def get_step_output(
        self, run_id: str, file_id: str, arm: str, step: str
    ) -> str | None:
        """Retrieve raw_response from a completed step (for pipeline resume)."""
        row = self._conn.execute(
            "SELECT raw_response FROM api_calls "
            "WHERE run_id=? AND file_id=? AND arm=? AND step=?",
            (run_id, file_id, arm, step),
        ).fetchone()
        return row[0] if row else None

    def get_file_scores(
        self, experiment: str, run_id: str | None = None
    ) -> list[dict]:
        """Return file scores, optionally filtered by run."""
        query = "SELECT * FROM file_scores WHERE experiment = ?"
        params: list = [experiment]
        if run_id:
            query += " AND run_id = ?"
            params.append(run_id)
        cursor = self._conn.execute(query, params)
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
