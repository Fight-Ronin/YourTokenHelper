# Backend

Formal backend implementation will live here.

Expected V1 responsibilities:

- source adapters for Codex, Claude Code, Cursor, Gemini CLI, GitHub Copilot, and secondary OpenAI API cost data;
- privacy-preserving normalization into daily and rolling 7-day usage buckets;
- local storage and refresh scheduling for the desktop app.

Do not put one-off probe scripts here. Start in `experiments/probes/`, then graduate stable code into this boundary.

## Current Boundary

- `core/`: stable usage-event and aggregate contracts shared by parser, storage, and UI layers.
- `fixtures/`: synthetic contract payloads and SQLite seed helpers.
- `sources/`: source adapter contracts, fixture adapters, explicit source discovery/registry setup, command-shaped manual refresh/result-summary payloads, and aggregate-only Codex/Claude JSONL adapters for storage sync tests.
- `storage/`: SQLite aggregate storage and summary payload assembly for Daily and rolling 7-day Weekly views.
- `tests/`: deterministic backend tests that use synthetic data only.

The desktop app should consume summaries shaped by `core/`; it should not read experimental parser files directly.

The `backend.sources.refresh_command_cli` module exposes the future manual
refresh stdin/stdout boundary. It reads JSON command args from stdin and writes
the same aggregate-only success/error union produced by
`build_primary_refresh_command_response_json`; it does not infer default source
paths or echo supplied roots. For process-style desktop wiring it can open a
file-backed SQLite database through the internal `YTH_REFRESH_DATABASE_PATH`
environment variable; that path is not accepted in the JSON request payload and
database-open failures are returned without echoing the path.
The `backend.storage.summary_command_cli` module uses the same internal
environment variable to read an existing SQLite aggregate summary without
creating an empty database. Missing persisted storage returns a structured
unavailable error instead of fake zero usage.
