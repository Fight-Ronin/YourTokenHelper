# PR 1b: Local Source Discovery Spike

## Goal

Validate whether Codex, Claude Code, Cursor, Gemini CLI, and GitHub Copilot expose enough data for a personal daily/weekly usage viewer.

This spike should answer:

1. Which local source directories exist on the current machine?
2. Which candidate files look usage-bearing?
3. Which sources expose token, model, timestamp, session, or workspace fields?
4. Which sources are ready for parser work, need more investigation, or should start as manual/export-only?

## Source Priority

Primary local sources:

- Codex.
- Claude Code.
- Cursor.

Secondary source:

- OpenAI API cost via official Admin Usage/Costs APIs when available. This should live in a secondary source/page and should not block the personal local usage path.

## Privacy Rules

- Do not store prompts.
- Do not store assistant responses.
- Do not store tool output.
- Do not store code snippets.
- Do not store full transcripts.
- Store only schema keys, aggregate counts, and redacted path/status metadata.

Full local paths should be kept out of committed docs. The ignored `.probe-output/` directory may contain machine-local discovery reports.

## Commands

Fixture smoke test:

```powershell
python experiments/probes/local_source_discovery.py --fixture-root experiments/fixtures/local_sources --output .probe-output/local-source-fixture-report.redacted.json
```

Local discovery:

```powershell
python experiments/probes/local_source_discovery.py --output .probe-output/local-source-report.redacted.json
```

Include full local paths only in ignored output:

```powershell
python experiments/probes/local_source_discovery.py --include-paths --output .probe-output/local-source-report.with-paths.local.json
```

## Status Values

- `not-found`: no likely local data was found.
- `needs-parser`: candidate data exists and should be inspected with a parser spike.
- `manual-only`: source exists but no usage-bearing fields were found.
- `permission-denied`: candidate source exists but could not be read.
- `ready`: enough usage-bearing fields were found to start fixture-driven parser tests.

## Acceptance Criteria

- Fixture mode runs without network access.
- Local discovery can run without printing sensitive content.
- The report includes one section each for Codex, Claude Code, Cursor, Gemini CLI, GitHub Copilot, and OpenAI API cost.
- Candidate local sources include only schema keys and counts.
- Cursor is explicitly marked based on observed local data, not assumed.

Current findings are recorded in [PR 1b Local Source Discovery Findings](pr-1b-local-source-discovery-findings.md).
