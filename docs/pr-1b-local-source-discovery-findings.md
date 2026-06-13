# PR 1b Local Source Discovery Findings

Last updated: 2026-06-14

## What Ran

Fixture smoke test:

```powershell
python experiments/probes/local_source_discovery.py --fixture-root experiments/fixtures/local_sources --output .probe-output/local-source-fixture-report.redacted.json
```

Local discovery:

```powershell
python experiments/probes/local_source_discovery.py --output .probe-output/local-source-report.redacted.json
```

Both reports are written under `.probe-output/`, which is ignored by git.

## Current Result

| Source | Status | Observed candidate files | Interpretation |
| --- | --- | ---: | --- |
| Codex | `ready` | 113 | Local data contains usage-like token fields and model fields. Start parser fixture work. |
| Claude Code | `ready` | 243 | Local data contains `message.usage` token fields and model fields. Start parser fixture work. |
| Cursor | `not-found` | 0 | Cursor was not detected on this machine. Keep Cursor as a first-class planned source, but do not assume parser readiness yet. |
| Gemini CLI | `not-found` | 0 | Gemini CLI was not detected on this machine. Keep fixture/interface support and require explicit telemetry/export setup later. |
| GitHub Copilot | `needs-parser` | 1 | A local Copilot candidate file exists, but token-bearing fields were not observed. Prefer official usage metrics/report support or manual fallback. |
| OpenAI API cost | `secondary-source` | 0 | Keep API/Admin usage and costs on a secondary page/source. It should not block local personal usage. |

## Observed Field Families

Codex:

- `payload.info.last_token_usage.*`
- `payload.info.total_token_usage.*`
- `payload.model`

Claude Code:

- `message.usage.input_tokens`
- `message.usage.output_tokens`
- `message.usage.cache_read_input_tokens`
- `message.usage.cache_creation_input_tokens`
- `message.usage.cache_creation.*`
- `message.usage.iterations.*`
- `message.model`
- `sessionId`

Cursor:

- No local data was found on this machine.

Gemini CLI:

- No local data was found on this machine.
- Official local telemetry can contain token fields, but it can also contain prompt/response text when configured, so parsing must be whitelist-only.

GitHub Copilot:

- One local candidate file was found.
- No token-bearing fields were observed locally on this machine.
- Official usage metrics/report support is the safer first parser path; personal local usage should remain manual or unavailable until validated.

## Product Decision

V1 should proceed as:

1. Local personal usage first: Codex and Claude Code parser contract.
2. Cursor and Gemini CLI remain first-class, but start with discovery/manual/export support until local data confirms parser shape.
3. GitHub Copilot remains first-class, but starts with official metrics/report fixture support and personal manual fallback.
4. OpenAI Admin/API usage and costs move to a secondary API Cost page/source.
5. No WebView login or internal endpoint scraping.

## Next Implementation Step

Build the normalized parser contract with fixtures for Codex, Claude Code, Cursor, Gemini CLI, and GitHub Copilot.

Cursor should get:

- detection state,
- not-found state,
- manual allowance window support,
- fixture/interface coverage,
- and a follow-up parser spike when local Cursor data is available.

Gemini CLI should get:

- detection state,
- not-found state,
- telemetry/export fixture coverage,
- and a follow-up parser spike when local telemetry is available.

GitHub Copilot should get:

- detection state,
- official metrics/report fixture coverage,
- manual fallback for personal users,
- and a follow-up parser spike only if local token fields are observed.
