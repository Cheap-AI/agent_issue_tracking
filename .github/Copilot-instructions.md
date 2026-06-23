## Summary
This repository creates and manages agents that analyze economic and stock‑market trends in (near) real‑time. Langraph may be used for orchestration; treat it as a known integration and validate compatibility before adding large Langraph-specific scaffolding.

## Guideline
Only implement exactly what was requested. Create the requested file(s) and at most minimal, obvious supporting artifacts (unit tests, a one-paragraph README note, type hints, or minimal dependency metadata). Do not scaffold dashboards, CI, large frameworks, or unrelated top-level services without explicit approval.

## Dev notes
Supported Python >= 3.8; run tests in PowerShell with ` $env:PYTHONPATH="src"; python -m pytest -q ` (tests live under `tests/`).

## Langraph note
If adding Langraph integration, prefer small adapter modules (keep core code framework-agnostic), include unit tests for the adapter, and confirm Python/runtime compatibility before adding the dependency.

If unsure, ask one concise clarifying question.

## Examples
- "Add feature X" → add X, one unit test, and a one-paragraph README example.
- "Create monitoring and CI" → ask clarifying questions (hosting, budget, frequency) before implementing.