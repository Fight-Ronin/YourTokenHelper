# Backend

Formal backend implementation will live here.

Expected V1 responsibilities:

- source adapters for Codex, Claude Code, Cursor, Gemini CLI, GitHub Copilot, and secondary API cost provider data;
- privacy-preserving normalization into daily and rolling 7-day usage buckets;
- local storage and refresh scheduling for the desktop app.

Do not put one-off probe scripts here. Start in `experiments/probes/`, then graduate stable code into this boundary.

## Current Boundary

- `core/`: stable usage-event and aggregate contracts shared by parser, storage, and UI layers.
- `fixtures/`: synthetic contract payloads and SQLite seed helpers.
- `sources/`: source adapter contracts, explicit source discovery/registry setup, command-shaped manual refresh/result-summary payloads, aggregate-only local JSONL adapters, API cost provider status contracts, and redacted OpenAI Admin usage/cost/key monitor payload helpers.
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
The `backend.sources.openai_admin_command_cli` module uses the same
stdin/stdout shape for the PR6 OpenAI Admin fixture/payload sync boundary. It
accepts aggregate Admin usage/cost payloads, writes hashed API-key/project
aggregates to SQLite, and returns sync metadata plus `storage_summary` without
echoing raw OpenAI IDs, fixture paths, or database paths.
The `backend.sources.openai_admin_key_monitor_command_cli` module accepts a
payload shaped like the Admin API Keys list/retrieve response and returns only
redacted monitor metadata: status, counts, timestamps, and hashed key refs. It
does not accept plaintext API keys, database paths, key names, redacted key
values, owner records, or live network options in the JSON request.
The `backend.sources.openai_admin_key_probe_command_cli` module is the narrow
live diagnostic boundary for that monitor. It reads the Admin key only from the
`OPENAI_ADMIN_KEY` environment variable, accepts only `checked_at` on stdin, and
returns the same redacted monitor metadata. Missing env configuration,
personal-key permission denials, and endpoint failures are explicit structured
states; raw API keys, response bodies, local paths, and database paths are not
accepted or returned.
The `backend.sources.api_provider_billing_sync_command_cli` module is the live
billing sync boundary for verified API cost providers. Its JSON request accepts
only `provider_id`, `end_day_utc`, and optional `started_at`; the OpenAI Admin
key is read only from `OPENAI_ADMIN_KEY`, and the SQLite path is read only from
the internal `YTH_REFRESH_DATABASE_PATH`. It currently enables the verified
OpenAI Admin usage/cost adapter, maps 401/403/429 endpoint errors to explicit
provider and endpoint diagnostic states, writes only hashed aggregate
usage/cost rows, and keeps raw API keys, response bodies, local paths, and raw
provider payloads out of stdout.
