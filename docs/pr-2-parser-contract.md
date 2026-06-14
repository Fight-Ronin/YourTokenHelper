# PR 2 Parser Contract And Fixtures

Date: 2026-06-14

## Goal

Create a deterministic normalized usage-event contract before building the desktop UI or persistent storage.

This PR should prove that Codex, Claude Code, Cursor, Gemini CLI, GitHub Copilot, and later API costs can share one aggregate shape while preserving source confidence and missing-data states.

## Assumptions

- V1 is for a single personal user.
- Daily and rolling 7-day views are the primary product views.
- Monthly remains lower priority.
- Cursor and Gemini CLI stay first-class sources, but if no local data is detected on the developer machine, parser work can use interface/fixtures only.
- GitHub Copilot personal local token access is not assumed; official usage metrics/report support and manual fallback are the first path.
- API-key dollar cost is a secondary source and should not block local usage parsing.
- The parser must not output prompt text, response text, tool output, code snippets, or full transcripts.

## Normalized Usage Event

Required fields:

- `source_kind`: `codex`, `claude_code`, `cursor`, `gemini_cli`, `github_copilot`, or secondary `openai_api_cost`.
- `source_id`: stable local source identifier.
- `started_at`: UTC ISO-8601 timestamp.
- `total_tokens`.
- `confidence`: `official`, `local_exact`, `local_estimated`, `manual`, or `unavailable`.

Optional fields:

- `model`.
- `input_tokens`.
- `output_tokens`.
- `cached_input_tokens`.
- `reasoning_output_tokens`.
- `session_id`.
- `workspace_id`.
- `project_id`.
- `api_key_id`.
- `cost_usd`.
- `usage_credits`.
- `raw_source_ref`.

`raw_source_ref` must be a redacted pointer, hash, or opaque local reference. It must not include raw prompt/response content.

## Aggregates

The parser summary should provide:

- Overall totals.
- Totals by source.
- Totals by UTC day.
- Rolling 7-day totals, anchored to the latest event date in fixture mode.

Token dimensions:

- `input_tokens`.
- `output_tokens`.
- `cached_input_tokens`.
- `reasoning_output_tokens`.
- `total_tokens`.

Cached tokens are a parallel dimension and should not be added to `total_tokens` when the source already provides an explicit total.

Backend summaries exposed to the desktop mock UI should use plain JSON-ready dictionaries with:

- `event_count`.
- `totals`.
- `by_source`.
- `by_day`.
- `rolling_7d`.

This keeps PR3 mock data aligned to the backend contract without connecting the desktop shell to experimental parser files.

The PR3 mock UI can start from `backend/fixtures/mock_v1_summary.json`. That fixture is synthetic aggregate data generated from backend core contracts; it is not parsed from real local logs.

## Allowance Windows

Allowance and remaining-usage data must be represented separately from token events because some sources do not expose an exact allowance.

Required fields:

- `source_kind`.
- `source_id`.
- `status`: `api_backed`, `manual`, `derived`, or `unavailable`.
- `unit`: `tokens`, `credits`, `usd`, `requests`, or `unknown`.

Optional fields:

- `window_start`.
- `window_end`.
- `reset_at`.
- `limit_amount`.
- `used_amount`.
- `remaining_amount`.
- `note`.

When `status` is `unavailable`, `remaining_amount`, `limit_amount`, and `reset_at` must be empty. This prevents the app from silently implying exact remaining usage when the source has no allowance data.

## Current Fixture Coverage

| Source | Fixture status | Real local status from PR 1b | PR 2 handling |
| --- | --- | --- | --- |
| Codex | Has synthetic usage fixture | `ready` | Parse fixture into `local_exact` events. |
| Claude Code | Has synthetic usage fixture | `ready` | Parse fixture into `local_exact` events. |
| Cursor | Has synthetic interface fixture | `not-found` on this machine | Keep parser interface and fixture coverage; skip real parser readiness until data is observed. |
| Gemini CLI | Has synthetic telemetry fixture | `not-found` on this machine | Parse telemetry/export token fields only; never persist prompt/response text. |
| GitHub Copilot | Has synthetic official-report fixture | `needs-parser` local state on this machine | Keep official metrics/report interface and personal manual fallback. |
| OpenAI API cost | Has separate API spike fixture | `secondary-source` | Keep for later API-cost parser; not part of local fixture parser yet. |

## Verification

Run:

```powershell
python -m pytest backend/tests
python -m py_compile backend/fixtures/mock_summary.py
python -m py_compile experiments/probes/usage_event_parser.py
python experiments/probes/usage_event_parser.py --fixture-root experiments/fixtures/local_sources --output .probe-output/usage-events-fixture-summary.redacted.json
```

Expected fixture totals:

| Source | Events | Total tokens |
| --- | ---: | ---: |
| Codex | 2 | 2540 |
| Claude Code | 2 | 5030 |
| Cursor | 1 | 3780 |
| Gemini CLI | 1 | 2250 |
| GitHub Copilot | 1 | 3440 |
| All sources | 7 | 17040 |

The output under `.probe-output/` is ignored by git.

## Non-Goals

- No desktop UI.
- No real local log ingestion.
- No database schema.
- No live OpenAI API call.
- No account WebView login.
- No internal endpoint scraping.
- No Monthly view.

## Next Step After PR 2

If fixture parsing stays stable, PR 3 can build a desktop mock UI against this normalized summary shape.

Real local parser integration should wait until PR 5, after source setup, trust states, and storage are designed.
