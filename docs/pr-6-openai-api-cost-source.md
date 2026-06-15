# PR 6: OpenAI API Cost Source

Status: payload ingestion, local-readback, secure credential storage, and
explicit OpenAI live billing sync are implemented.

## Scope For This Slice

- Parse OpenAI Admin Usage/Costs payloads from a sanitized fixture shape.
- Expose a backend-only `sync_openai_admin_usage_cost` stdin/stdout command
  boundary for deterministic payload sync tests.
- Parse OpenAI Admin API Keys list/retrieve payloads into a redacted monitor
  result for credential diagnostics.
- Expose a backend-only `monitor_openai_admin_api_key` stdin/stdout command
  boundary for deterministic key-monitor payload tests.
- Expose a backend-only `probe_openai_admin_api_key` stdin/stdout command
  boundary for live Admin-key capability diagnostics from environment only.
- Expose `sync_api_provider_billing` as the explicit live provider sync command;
  it currently enables only the verified OpenAI Admin usage/cost adapter.
- Store provider credentials as protected desktop app-data blobs and inject the
  decrypted OpenAI key only into the backend process environment.
- Convert `organization.usage.completions` buckets into `openai_api_cost` aggregate usage events.
- Preserve OpenAI `num_model_requests` as request/event count.
- Store `organization.costs` buckets in `cost_buckets` without creating fake 0-token usage events.
- Surface a `cost_summary` aggregate from local SQLite storage for the desktop API Costs page.
- Keep available usage when costs are permission-denied or unavailable; do not show fake zero cost.
- Hash OpenAI `api_key_id` and `project_id` before storage.
- Keep `allowance_windows` empty unless a reliable allowance source is captured later.

## Command Boundary

`backend.sources.openai_admin_commands` defines the internal
`sync_openai_admin_usage_cost` command contract. The request accepts only:

- `end_day_utc`
- `started_at`
- `payload`

`database_path`, fixture paths, local paths, auto-discovery flags, API keys, and
live network options are not accepted in the JSON request. The process wrapper
`backend.sources.openai_admin_command_cli` can open the aggregate SQLite
database through the internal `YTH_REFRESH_DATABASE_PATH` environment variable,
matching the PR5 refresh command boundary. Structured errors name only the
field and error class; they must not echo local paths or raw OpenAI IDs.
Both `usage` and `costs` endpoint envelopes are required inside `payload`.
Empty endpoint results must be explicit `data: []`; permission-denied or
unavailable endpoint results must be explicit `error` objects. An absent
endpoint is invalid and must not replace existing aggregate rows.

The response contains `sync_result` metadata plus `storage_summary`. It does
not return the raw Admin response, prompts, requests, transcripts, API keys,
raw `api_key_id`, or raw `project_id`.

`backend.storage.summary_payload` exposes `cost_summary` from local aggregate
SQLite storage. This is a read path only: it summarizes stored USD cost buckets
by provider for the rolling 7-day window and does not include raw Admin
responses, raw project IDs, raw API key IDs, prompts, request payloads, local
paths, or API keys.

`backend.sources.api_provider_billing_sync_commands` defines the live billing
sync contract for verified provider adapters. The request accepts only:

- `provider_id`
- `end_day_utc`
- `started_at`

The command reads OpenAI key material only from `OPENAI_ADMIN_KEY`; it does not
accept key material, provider payloads, database paths, local paths, or live
network options in JSON. The response contains sync metadata, a refreshed
aggregate `storage_summary`, and redacted provider status metadata. Endpoint
401, 403, and 429 states map to `invalid_key`, `permission_denied`, and
`rate_limited` respectively without returning response bodies.

`backend.sources.openai_admin_key_monitor_commands` defines the internal
`monitor_openai_admin_api_key` command contract. The request accepts only:

- `checked_at`
- `payload`

`api_key`, `database_path`, live network options, fixture paths, and local paths
are not accepted in the JSON request. The payload must include an explicit
`admin_api_keys` endpoint envelope with list `data`, a single retrieved Admin
API key object, or `error`. The response contains `monitor_result` metadata
only: status, counts, timestamps, and hashed key references. It does not return
Admin API key names, redacted key values, owners, raw key IDs, API keys, or
endpoint error details.

`backend.sources.openai_admin_key_probe_commands` defines the narrow live
diagnostic contract for checking whether an env-configured key can access the
Admin API Keys list endpoint. The request accepts only:

- `checked_at`

The command reads key material only from `OPENAI_ADMIN_KEY`; it intentionally
does not fall back to `OPENAI_API_KEY`, so a personal key is not used
implicitly. A personal or insufficiently scoped key may be placed in
`OPENAI_ADMIN_KEY` for a negative-path test, which should return
`invalid_key` or `permission_denied` rather than fake readiness. The response
contains the same `monitor_result` shape as the payload monitor. HTTP failures
are converted to status-only endpoint envelopes; raw API keys, endpoint
response bodies, local paths, database paths, and Admin key names are not
accepted or returned.

## Official Shape Used

- Usage endpoint: `GET /organization/usage/completions`
- Costs endpoint: `GET /organization/costs`
- Admin API Keys list endpoint: `GET /organization/admin_api_keys`
- Admin API Keys retrieve endpoint: `GET /organization/admin_api_keys/{key_id}`
- Usage fields used: `input_tokens`, `output_tokens`, `input_cached_tokens`, `num_model_requests`, `model`, `api_key_id`, and `project_id`.
- Cost fields used: `amount.value`, `amount.currency`, `api_key_id`, and `project_id`.
- Admin API key fields consumed for diagnostics: `id`, `created_at`, and `last_used_at`.

Official docs:

- https://developers.openai.com/api/reference/resources/admin/subresources/organization/subresources/usage
- https://developers.openai.com/api/reference/resources/admin/subresources/organization/subresources/admin_api_keys/methods/list
- https://developers.openai.com/api/reference/resources/admin/subresources/organization/subresources/admin_api_keys/methods/retrieve

## Non-Goals

- No automatic background sync.
- No verified live billing adapters for Claude, Gemini, or DeepSeek yet.
- No plaintext API key monitor request fields in this slice.
- No allowance, remaining usage, or reset inference.
- No raw API responses, prompts, request payloads, or stable raw OpenAI IDs in UI payloads.
- No team account management or billing mutation actions.

## Verification

Run:

```powershell
conda run -n tokenviz python -m pytest backend\tests
```

Expected coverage:

- Fixture payload maps to `openai_api_cost` usage totals.
- Cost records are queryable without inflating usage event counts.
- Local storage summaries expose stored cost aggregates when cost buckets exist
  and explicit empty cost summaries when no cost buckets exist.
- `api_key_id` and `project_id` are hashed before storage.
- Permission denied produces a recoverable source state.
- The stdin/stdout command writes a file-backed SQLite aggregate without
  echoing raw IDs or database paths.
- The Admin API key monitor maps ready, invalid-key, permission-denied,
  rate-limited, and generic-error endpoint states without echoing raw key
  metadata.
- The env-only Admin API key probe maps missing env configuration and
  personal-key permission denial without echoing key material or response
  bodies.
- Live OpenAI provider billing sync accepts only provider id and date on stdin,
  writes aggregate usage/cost rows when access is available, and maps personal
  or insufficiently scoped keys to explicit credential/provider states.
