## Output Format

**Return a `ReviewOutput` JSON block followed by a human-readable summary.**

Your output MUST include a fenced JSON block:

```json
{
  "findings": [
    {
      "file": "relative/path/to/file.ts",
      "line_start": 42,
      "line_end": 48,
      "severity": "critical | major | minor | nitpick",
      "category": "security | correctness | performance | maintainability | testing | documentation | architecture | style",
      "finding": "Clear description of the issue",
      "suggested_fix": "Optional — specific fix or alternative"
    }
  ]
}
```

**Severity values — use these EXACT strings (do not paraphrase):**
- `"critical"` — blocks merge; correctness, security, data integrity.
- `"major"` — significant maintainability or correctness concern.
- `"minor"` — small but real issue.
- `"nitpick"` — optional style/naming improvement.

**Field names — use these EXACT keys (do not rename):**
- `"finding"` — the issue description. NOT "title", NOT "detail", NOT "description", NOT "issue".
- `"suggested_fix"` — optional fix. NOT "recommendation", NOT "suggestion", NOT "fix".
- `"line_start"` and `"line_end"` — line range. NOT "line", NOT "lines", NOT "start_line".
- `"file"` — relative path. NOT "path", NOT "filename".

After the JSON block, provide a human-readable narrative explaining your review findings. Reference findings by their index if helpful.

## Coverage Declaration (mandatory)

Every review must end with a coverage declaration:

```
## Coverage
- **Reviewed:** [list areas examined, e.g., "security, error handling, architecture, documentation, naming"]
- **Not reviewed:** [list areas outside this review's scope or expertise]
- **Confidence:** HIGH on findings 1-N; MEDIUM on finding M; LOW/speculative on finding K
- **Gaps:** [anything you couldn't assess and why]
```

This declaration is structural, not optional. A review without a coverage declaration is incomplete.
