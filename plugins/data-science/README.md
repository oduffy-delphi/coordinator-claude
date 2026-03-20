# data-science

Data science domain plugin. Enable for ML, statistical analysis, and data engineering projects.

## Components

**Agents:**
- `camelia-data-scientist` (Opus) — ML/AI specialist, statistical analysis, data modeling, LLM expertise. Complements Patrik's engineering focus with quantitative depth.

**Routing:** Registers Camelia for data science signals with Patrik (coordinator) as backstop.

## Enabling

Add to your project's `.claude/coordinator.local.md`:

```yaml
---
project_type: data-science
---
```

Or explicitly list reviewers:

```yaml
---
active_reviewers:
  - patrik
  - camelia
---
```

## When Camelia Activates

Camelia handles reviews involving:
- ML model architecture and training pipelines
- Statistical analysis and hypothesis testing
- Data preprocessing and feature engineering
- LLM prompt engineering and fine-tuning
- Jupyter notebooks and data exploration
