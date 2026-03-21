"""Scoring engine — matches review findings against defect/distractor manifests.

This is the measurement instrument for both experiments. Its accuracy directly
determines whether conclusions are valid.

Matching algorithm (5 steps):
1. File match — finding must reference the correct file
2. Line proximity — within 10 lines of a manifest defect
3. Category match — exact or related category
4. Tie-breaking — exact > fuzzy, closest line, manifest order
5. LLM-judge fallback — optional Haiku call for ambiguous matches
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .schemas import (
    DefectEntry,
    DefectManifest,
    DistractorEntry,
    DistractorManifest,
    FileScore,
    FindingClassification,
    MatchMethod,
    ReviewFinding,
    ScoredFinding,
)

# Categories considered related for fuzzy matching
RELATED_CATEGORIES: dict[str, set[str]] = {
    "security": {"error_handling"},
    "error_handling": {"security", "logic"},
    "logic": {"error_handling"},
    "performance": {"architecture"},
    "architecture": {"performance"},
    "integration": {"logic", "architecture"},
}

LINE_PROXIMITY_THRESHOLD = 10


@dataclass
class _CandidateMatch:
    """Internal: a potential match between a finding and a manifest defect."""

    defect: DefectEntry
    line_distance: int
    category_match: str  # "exact", "related", or "keyword"
    keyword_matched: bool


class Scorer:
    """Matches review findings against manifests and classifies them."""

    def __init__(
        self,
        defect_manifest: DefectManifest,
        distractor_manifest: DistractorManifest | None = None,
        llm_judge: object | None = None,  # ExperimentClient, optional
        use_llm_judge: bool = False,
    ):
        self.defects = defect_manifest
        self.distractors = distractor_manifest
        self.llm_judge = llm_judge
        self.use_llm_judge = use_llm_judge and llm_judge is not None

    def score_findings(
        self,
        findings: list[ReviewFinding],
        file_id: str,
        arm: str,
        run_id: str,
    ) -> tuple[list[ScoredFinding], FileScore]:
        """Score all findings for a single file against the manifests.

        Returns scored findings and an aggregated FileScore.
        """
        file_name = file_id if "." in file_id else f"{file_id}.py"
        file_defects = self.defects.defects_for_file(file_name)
        file_distractors = (
            self.distractors.distractors_for_file(file_name)
            if self.distractors
            else []
        )

        # Track which defects have been claimed (each can match at most once)
        claimed_defect_ids: set[str] = set()
        scored: list[ScoredFinding] = []

        # Score each finding
        for finding in findings:
            sf = self._score_single_finding(
                finding, file_defects, file_distractors, claimed_defect_ids
            )
            if sf.matched_defect_id:
                claimed_defect_ids.add(sf.matched_defect_id)
            scored.append(sf)

        # Compute file-level aggregates
        tp_ids = [sf.matched_defect_id for sf in scored if sf.classification == FindingClassification.TRUE_POSITIVE]
        all_defect_ids = [d.defect_id for d in file_defects]
        fn_ids = [d_id for d_id in all_defect_ids if d_id not in set(tp_ids)]

        tp_count = len(tp_ids)
        fn_count = len(fn_ids)
        fp_dist = sum(1 for sf in scored if sf.classification == FindingClassification.FALSE_POSITIVE_DISTRACTOR)
        fp_novel = sum(1 for sf in scored if sf.classification == FindingClassification.FALSE_POSITIVE_NOVEL)
        valid_unexpected = sum(1 for sf in scored if sf.classification == FindingClassification.VALID_UNEXPECTED)

        total_findings = tp_count + fp_dist + fp_novel + valid_unexpected
        precision = tp_count / total_findings if total_findings > 0 else 0.0
        recall = tp_count / len(all_defect_ids) if all_defect_ids else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        file_score = FileScore(
            file=file_name,
            arm=arm,
            run_id=run_id,
            true_positives=tp_ids,
            false_negatives=fn_ids,
            fp_distractor=fp_dist,
            fp_novel=fp_novel,
            valid_unexpected=valid_unexpected,
            recall=recall,
            precision=precision,
            f1=f1,
        )

        return scored, file_score

    def _score_single_finding(
        self,
        finding: ReviewFinding,
        file_defects: list[DefectEntry],
        file_distractors: list[DistractorEntry],
        claimed: set[str],
    ) -> ScoredFinding:
        """Classify a single finding using the 5-step algorithm.

        Defect matching is attempted first (Steps 2-4). Only if no defect match
        is found do we check distractors. This prevents a nearby distractor from
        shadowing a legitimate defect match.
        """

        # Step 2 + 3: Find candidate defect matches (line proximity + category)
        candidates: list[_CandidateMatch] = []
        for defect in file_defects:
            if defect.defect_id in claimed:
                continue

            line_dist = self._line_distance(
                finding.line_start, finding.line_end,
                defect.line_start, defect.line_end,
            )
            if line_dist > LINE_PROXIMITY_THRESHOLD:
                continue

            # Check category match
            cat_match = self._category_match(finding.category, defect.category)

            # Check keyword match
            keyword_hit = self._keyword_match(finding.finding, defect.keywords)

            # Accept if: exact category match, or keyword match, or both.
            # Related category alone is not sufficient — too many false matches.
            if cat_match == "exact" or keyword_hit:
                candidates.append(_CandidateMatch(
                    defect=defect,
                    line_distance=line_dist,
                    category_match=cat_match,
                    keyword_matched=keyword_hit,
                ))

        # Step 4: Tie-breaking — pick best candidate
        if candidates:
            best = self._pick_best_candidate(candidates)

            # Determine match method
            if best.category_match == "exact":
                method = MatchMethod.EXACT
            else:
                method = MatchMethod.FUZZY

            return ScoredFinding(
                finding=finding,
                classification=FindingClassification.TRUE_POSITIVE,
                matched_defect_id=best.defect.defect_id,
                match_method=method,
            )

        # Step 5: LLM-judge fallback for line-proximate but category-mismatched
        if self.use_llm_judge:
            for defect in file_defects:
                if defect.defect_id in claimed:
                    continue
                line_dist = self._line_distance(
                    finding.line_start, finding.line_end,
                    defect.line_start, defect.line_end,
                )
                if line_dist <= LINE_PROXIMITY_THRESHOLD:
                    if self.llm_judge.judge_match(defect.description, finding.finding):
                        return ScoredFinding(
                            finding=finding,
                            classification=FindingClassification.TRUE_POSITIVE,
                            matched_defect_id=defect.defect_id,
                            match_method=MatchMethod.LLM_JUDGE,
                        )

        # Check against distractors (only if no defect matched)
        for dist in file_distractors:
            if self._lines_overlap(finding.line_start, finding.line_end, dist.line_start, dist.line_end):
                return ScoredFinding(
                    finding=finding,
                    classification=FindingClassification.FALSE_POSITIVE_DISTRACTOR,
                    matched_distractor_id=dist.distractor_id,
                    match_method=MatchMethod.EXACT,
                )

        # No match — novel false positive (or valid unexpected)
        return ScoredFinding(
            finding=finding,
            classification=FindingClassification.FALSE_POSITIVE_NOVEL,
            match_method=MatchMethod.NONE,
        )

    @staticmethod
    def _line_distance(f_start: int, f_end: int, d_start: int, d_end: int) -> int:
        """Compute minimum distance between two line ranges."""
        if f_start <= d_end and f_end >= d_start:
            return 0  # overlap
        return min(abs(f_start - d_end), abs(f_end - d_start))

    @staticmethod
    def _lines_overlap(f_start: int, f_end: int, d_start: int, d_end: int) -> bool:
        """Check if two line ranges overlap or are within 3 lines."""
        return Scorer._line_distance(f_start, f_end, d_start, d_end) <= 3

    @staticmethod
    def _category_match(finding_cat: str, defect_cat: str) -> str:
        """Return 'exact', 'related', or 'none'."""
        finding_cat = finding_cat.lower().strip()
        defect_cat = defect_cat.lower().strip()
        if finding_cat == defect_cat:
            return "exact"
        related = RELATED_CATEGORIES.get(defect_cat, set())
        if finding_cat in related:
            return "related"
        return "none"

    @staticmethod
    def _keyword_match(finding_text: str, keywords: list[str]) -> bool:
        """Check if any manifest keywords appear in the finding text."""
        lower_text = finding_text.lower()
        return any(kw.lower() in lower_text for kw in keywords)

    @staticmethod
    def _pick_best_candidate(candidates: list[_CandidateMatch]) -> _CandidateMatch:
        """Pick the best candidate match using tie-breaking rules."""
        def sort_key(c: _CandidateMatch) -> tuple:
            # Lower is better for all:
            # 1. Exact category > keyword-only > related > none
            cat_rank = {"exact": 0, "related": 2, "none": 3}.get(c.category_match, 3)
            if c.keyword_matched and cat_rank > 0:
                cat_rank = 1
            # 2. Closer line distance
            return (cat_rank, c.line_distance)

        candidates.sort(key=sort_key)
        return candidates[0]
