"""Data processing pipeline — test corpus file with seeded defects."""

from typing import Any


def process_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Process and validate a list of records."""
    results = []
    for record in records:
        # DEFECT: No error handling — KeyError if 'id' missing
        record_id = record["id"]
        value = record.get("value", 0)

        # DEFECT: Integer division truncation
        normalized = value / 100 * 100
        results.append({"id": record_id, "normalized": normalized})

    return results


def merge_datasets(primary: list[dict], secondary: list[dict]) -> list[dict]:
    """Merge two datasets by ID."""
    # DEFECT: O(n*m) nested loop — should use dict lookup
    merged = []
    for p in primary:
        for s in secondary:
            if p["id"] == s["id"]:
                merged.append({**p, **s})
                break
        else:
            merged.append(p)
    return merged
