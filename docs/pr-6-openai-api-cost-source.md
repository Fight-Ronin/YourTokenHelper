# PR 6: OpenAI API Cost Source

Status: first backend slice in progress.

## Scope For This Slice

- Parse OpenAI Admin Usage/Costs payloads from a sanitized fixture shape.
- Expose a backend-only `sync_openai_admin_usage_cost` stdin/stdout command
  boundary for deterministic payload sync tests.
- Convert `organization.usage.completions` buckets into `openai_api_cost` aggregate usage events.
- Preserve OpenAI `num_model_requests` as request/event count.
- Store `organization.costs` buckets in `cost_buckets` without creating fake 0-token usage events.
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

The response contains `sync_result` metadata plus `storage_summary`. It does
not return the raw Admin response, prompts, requests, transcripts, API keys,
raw `api_key_id`, or raw `project_id`.

## Official Shape Used

- Usage endpoint: `GET /organization/usage/completions`
- Costs endpoint: `GET /organization/costs`
- Usage fields used: `input_tokens`, `output_tokens`, `input_cached_tokens`, `num_model_requests`, `model`, `api_key_id`, and `project_id`.
- Cost fields used: `amount.value`, `amount.currency`, `api_key_id`, and `project_id`.

Official docs:

- https://developers.openai.com/api/reference/resources/admin/subresources/organization/subresources/usage

## Non-Goals

- No live network sync in this slice.
- No API key collection or OS secure storage in this slice.
- No background sync.
- No Tauri command registration in this slice.
- No allowance, remaining usage, or reset inference.
- No raw API responses, prompts, request payloads, or stable raw OpenAI IDs in UI payloads.

## Verification

Run:

```powershell
conda run -n tokenviz python -m pytest backend\tests
```

Expected coverage:

- Fixture payload maps to `openai_api_cost` usage totals.
- Cost records are queryable without inflating usage event counts.
- `api_key_id` and `project_id` are hashed before storage.
- Permission denied produces a recoverable source state.
- The stdin/stdout command writes a file-backed SQLite aggregate without
  echoing raw IDs or database paths.
