# Programming Agent Source Candidates

Date: 2026-06-14

## Decision

V1 should support exactly these primary coding-agent sources:

1. Codex.
2. Claude Code.
3. Cursor.
4. Gemini CLI.
5. GitHub Copilot.

OpenAI API-key dollar cost remains a secondary API Costs source.

Other programming agents are out of scope for V1 and the near-term roadmap. This keeps the app small enough to be useful for one personal user instead of becoming a broad observability platform.

## Added Sources

| Source | Why it stays | Initial support shape |
| --- | --- | --- |
| Gemini CLI | It is a terminal coding agent with official OpenTelemetry support and local file-based telemetry. | Discovery for `.gemini` and parser support for telemetry/export token fields only. |
| GitHub Copilot | It is widely used and has official usage metrics APIs, but personal local token access is uncertain. | Official metrics/report fixture support, local detection state, and manual fallback for personal users. |

## Explicitly Out Of Scope

| Candidate | Reason |
| --- | --- |
| Cline | Useful, but expanding to another open-source multi-surface agent would make V1 too broad. |
| OpenCode | Useful, but provider/subscription attribution adds another layer of complexity. |
| Aider | Mature CLI tool, but not part of the user's chosen source set. |
| Devin Desktop / Windsurf | Important, but local/export usage access is unclear and cloud/account-centric. |
| Continue | Current positioning is more PR checks than personal local usage viewing. |
| Roo Code / ZooCode | Roo Code has shutdown/ecosystem churn. |
| Replit Agent | Cloud/account-centric and outside the local-first path. |
| Sourcegraph Amp | Deferred because local/export usage access is not validated. |
| Google Jules | Cloud agent; not aligned with the local desktop viewer. |
| JetBrains AI / Zed agent surfaces | IDE surfaces only; revisit only if they become part of the user's actual workflow. |

## Fit Criteria For Adding A Source

A source is worth adding when it satisfies at least two of:

- The user actually uses it.
- It has local usage-bearing files or an official export/API.
- It exposes daily or rolling 7-day data.
- It can identify model/tool/session without storing prompt content.
- It can represent remaining usage, refresh timing, or at least consumed usage.

## Guardrail

Future agent support should enter through the same normalized `UsageEvent` contract. Do not add source-specific UI until the source can produce daily and rolling 7-day aggregate usage with clear confidence labels.

For V1, "future agent support" means Gemini CLI and GitHub Copilot only.

## Sources Checked

- Claude Code costs and `/usage`: https://code.claude.com/docs/en/costs
- Cursor pricing and Admin Dashboard usage note: https://cursor.com/pricing
- Gemini CLI repository: https://github.com/google-gemini/gemini-cli
- Gemini CLI telemetry: https://geminicli.com/docs/cli/telemetry/
- GitHub Copilot usage metrics APIs: https://docs.github.com/en/rest/copilot/copilot-usage-metrics
- Roo Code shutdown notice: https://docs.roocode.com/
- Continue current positioning: https://www.continue.dev/
