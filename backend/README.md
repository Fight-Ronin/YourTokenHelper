# Backend

Formal backend implementation will live here.

Expected V1 responsibilities:

- source adapters for Codex, Claude Code, Cursor, Gemini CLI, GitHub Copilot, and secondary OpenAI API cost data;
- privacy-preserving normalization into daily and rolling 7-day usage buckets;
- local storage and refresh scheduling for the desktop app.

Do not put one-off probe scripts here. Start in `experiments/probes/`, then graduate stable code into this boundary.

## Current Boundary

- `core/`: stable usage-event and aggregate contracts shared by parser, storage, and UI layers.
- `tests/`: deterministic backend tests that use synthetic data only.

The desktop app should consume summaries shaped by `core/`; it should not read experimental parser files directly.
