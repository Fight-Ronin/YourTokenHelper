# Interface Design V1

Date: 2026-06-14

## Purpose

This document defines the V1 interface direction for YourTokenHelper before the desktop shell is implemented.

It should guide PR 3: Desktop Shell With Mock Data.

The goal is to make the mock UI feel like the real product direction, not a throwaway scaffold.

## Scope

This document covers:

- Visual theme.
- Color system.
- Layout principles.
- Navigation.
- Daily view.
- Weekly view.
- Sources view.
- API Costs view.
- Settings view.
- Core components.
- Empty, error, and trust states.
- PR 3 implementation handoff.

This document does not cover:

- Real parser integration.
- SQLite schema.
- Secure key storage.
- Live OpenAI API sync.
- Packaging.
- Monthly reporting.

## Design Assumptions

- V1 is a desktop utility for one personal user.
- Daily and rolling 7-day usage are the primary views.
- Local coding-tool usage is the default path.
- OpenAI API costs are a secondary optional source.
- Remaining allowance and reset timing may be official, manual, derived, or unavailable.
- The UI must make data quality visible without turning the app into an alert dashboard.
- The app stores and displays aggregates only, not prompt or response content.
- PR 3 can use mock data, but the mock data should include partial, missing, and stale states.

## Product Posture

YourTokenHelper should feel like a calm local usage control panel.

It should not feel like:

- A marketing landing page.
- A large SaaS analytics dashboard.
- A billing reconciliation tool.
- A realtime observability platform.
- A playful AI toy.

It should feel like:

- A desktop utility the user can open daily.
- A trustworthy source-health viewer.
- A compact dashboard for personal coding-tool usage.
- A place where uncertainty is handled plainly.

The primary user question is:

> How much did I use, how much do I appear to have left, and can I trust these numbers?

## Visual Theme

Theme name: Graphite + Ice + Teal.

Design intent:

- Graphite for readable, serious text.
- Ice for quiet desktop surfaces.
- Teal for local health, usage emphasis, and primary actions.
- Blue as a secondary accent for optional API-related surfaces.
- Amber and red only for actual warning and error states.

The theme should be minimal, spacious, and utilitarian. It should use enough contrast to make dense numbers readable, but avoid heavy shadows, decorative gradients, and loud color blocks.

## Color System

### Core Palette

| Token | Hex | Use |
| --- | --- | --- |
| `color.bg` | `#F6F8FA` | App background. |
| `color.surface` | `#FFFFFF` | Main panels, metric tiles, table rows. |
| `color.surface.subtle` | `#F9FAFB` | Sidebar, grouped settings areas, muted panels. |
| `color.surface.hover` | `#F3F4F6` | Row and button hover states. |
| `color.text.primary` | `#15171A` | Main text and primary numbers. |
| `color.text.secondary` | `#4B5563` | Labels and secondary values. |
| `color.text.muted` | `#6B7280` | Timestamps, helper labels, table metadata. |
| `color.text.disabled` | `#9CA3AF` | Disabled controls and unavailable values. |
| `color.border` | `#E5E7EB` | Default borders. |
| `color.border.strong` | `#D1D5DB` | Active rows, focused panels, table separators. |
| `color.accent.primary` | `#0F766E` | Primary action, current usage emphasis, healthy sync. |
| `color.accent.primary.hover` | `#0D9488` | Primary action hover. |
| `color.accent.secondary` | `#2563EB` | Optional API source and secondary action emphasis. |
| `color.chart.grid` | `#EEF2F7` | Chart grid lines. |

### Status Palette

| Token | Hex | Use |
| --- | --- | --- |
| `color.status.ready` | `#16A34A` | Connected, synced, official, ready. |
| `color.status.warning` | `#D97706` | Manual, derived, partial, stale, needs setup. |
| `color.status.error` | `#DC2626` | Permission denied, invalid key, failed sync. |
| `color.status.neutral` | `#9CA3AF` | Not found, unavailable, disabled. |

### Source Colors

Source colors should be used for charts and small source markers, not large page backgrounds.

| Source | Hex | Notes |
| --- | --- | --- |
| Codex | `#0F766E` | Primary local source accent. |
| Claude Code | `#C2410C` | Warm but restrained. |
| Cursor | `#111827` | Neutral graphite. |
| Gemini CLI | `#2563EB` | Secondary blue. |
| GitHub Copilot | `#16A34A` | Green source marker. |
| OpenAI API Cost | `#7C3AED` | Purple only for API cost, used sparingly. |
| Manual allowance | `#D97706` | Estimate or fallback marker. |
| Unknown/unavailable | `#9CA3AF` | Missing or not configured. |

### Color Rules

- Do not use large decorative gradients.
- Do not make the UI a single-hue teal or blue theme.
- Teal should identify primary actions and important healthy usage states.
- Amber should mean "pay attention, but recoverable."
- Red should mean "blocked or failed."
- Purple should stay limited to optional API cost surfaces.
- Missing values must not use green or look successful.

## Typography

Use the platform system font stack:

```css
font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
  "Segoe UI", sans-serif;
```

If Inter is not bundled, system UI is acceptable.

Use tabular numbers for metrics:

```css
font-variant-numeric: tabular-nums;
```

Recommended sizes:

| Role | Size | Weight |
| --- | ---: | ---: |
| Page title | 20px | 650 |
| Section title | 14px | 600 |
| Metric label | 12px | 500 |
| Primary metric value | 32px | 650 |
| Secondary metric value | 20px | 650 |
| Body text | 14px | 400 |
| Table text | 13px | 400 |
| Badge text | 11px | 600 |

Typography rules:

- Do not scale font size with viewport width.
- Use zero letter spacing.
- Keep compact panels visually compact. Do not use hero-scale type inside dashboard surfaces.
- Metric labels should be short and stable.
- Use sentence case for UI labels unless a provider name requires casing.

## Spacing, Radius, And Elevation

Spacing scale:

| Token | Value |
| --- | ---: |
| `space.1` | 4px |
| `space.2` | 8px |
| `space.3` | 12px |
| `space.4` | 16px |
| `space.5` | 20px |
| `space.6` | 24px |
| `space.8` | 32px |

Radius:

| Token | Value | Use |
| --- | ---: | --- |
| `radius.sm` | 4px | Badges, inputs, compact controls. |
| `radius.md` | 6px | Buttons, table row hover, source chips. |
| `radius.lg` | 8px | Metric tiles and repeated cards. |

Elevation:

- Prefer borders over shadows.
- Use at most one subtle shadow for floating menus or modals.
- Do not nest cards inside cards.
- Page sections should be unframed layouts or full-width bands; cards are for metric tiles, repeated source rows, and modal surfaces.

## App Shell

The desktop app should use a stable two-column shell:

- Left sidebar navigation.
- Main content area.

Recommended desktop dimensions:

- Sidebar width: 176px.
- Top header height: 56px.
- Content padding: 24px.
- Minimum practical app width: 960px.
- Comfortable width: 1120px to 1280px.

Mobile responsiveness is lower priority for a desktop app, but the layout should still avoid overlapping if the window is narrow.

## Navigation

Primary navigation:

1. Daily.
2. Weekly.
3. Sources.
4. API Costs.
5. Settings.

Rules:

- Daily is the default connected-state screen.
- First launch uses the same shell but shows setup content in the main area.
- API Costs is secondary and should not block Daily or Weekly.
- Monthly is not a V1 navigation item.
- Navigation labels should use icons plus text when space allows.
- Active navigation uses a teal left marker or subtle filled row, not a large color block.

## Header

Each page header should include:

- Page title.
- Time range label.
- Timezone.
- Last successful sync.
- Manual sync action.
- Data quality badge.

Example header content:

```text
Daily                  Local time: Asia/Shanghai   Synced 4 min ago   [Sync]
```

The header should be useful, not decorative. Avoid explanatory paragraphs in the header.

## Daily View

Daily is the primary product screen.

It should answer:

- What did I use today?
- How much appears remaining?
- When does it reset?
- Which tools or models drove usage?
- Which numbers are partial, manual, derived, or unavailable?

### Daily Layout

Recommended structure:

```text
Header

Metric strip
  [Usage consumed] [Remaining] [Reset] [Cost estimate] [Requests] [Cached share]

Main grid
  Left:  Source usage chart
         Token split
         Top drivers table

  Right: Trust panel
         Source health
         Allowance status
         Cost coverage
```

### Daily Metric Strip

Metric priority:

1. Usage consumed.
2. Remaining usage.
3. Next reset.
4. Cost estimate.
5. Requests.
6. Cached input share.

Usage consumed should be the largest tile.

Remaining usage should never imply precision when the data is manual, derived, or unavailable.

Cost estimate should be visually secondary. It should not compete with usage consumed or remaining allowance.

### Daily Charts

Recommended charts:

- Stacked source usage bar for today's total.
- Token split horizontal bars for input, output, cached input, and reasoning output.
- Top drivers table for source, model, workspace/project/API key.

Avoid:

- Pie charts for primary source usage.
- Dense multi-axis charts.
- Prompt/session drilldown as a V1 default.

### Daily Trust Panel

The trust panel should be visible without scrolling on common desktop sizes.

It should show:

- Last successful sync.
- Sources with failed or partial sync.
- Allowance confidence: official, manual, derived, unavailable.
- Cost coverage: complete, partial, unavailable.
- Stale data indicator.

It should be quiet when healthy and specific when something is wrong.

## Weekly View

Weekly is the rolling last 7 days view.

It should answer:

- How much did I use in the last 7 days?
- Which day was highest?
- Which source or model drove the week?
- Is allowance or cost data complete for the week?

### Weekly Layout

Recommended structure:

```text
Header

Metric strip
  [7-day usage] [Avg daily] [Remaining] [Reset] [7-day cost] [Requests]

Main grid
  Full width: 7-day trend chart

  Left:  Top sources and models
         Top workspaces/projects/API keys

  Right: Coverage and trust panel
```

### Weekly Trend

Use a simple 7-bar chart with source stacking if the result stays readable.

Rules:

- Highlight the highest day subtly.
- Label only the necessary dates.
- Show empty days as zero usage only when the source data is fresh and complete.
- If source data is missing, show the day as incomplete instead of silently treating it as zero.

## Sources View

Sources is the product's trust center.

It should help the user understand which data sources are connected, missing, partial, or blocked.

### Sources Layout

Use a compact table-like list, not a decorative card wall.

Recommended columns:

- Source.
- Status.
- Usage.
- Cost.
- Allowance.
- Last sync.
- Action.

Example row states:

| Source | Status | Usage | Cost | Allowance | Action |
| --- | --- | --- | --- | --- | --- |
| Codex | Ready | Local exact | Estimate unavailable | Manual estimate | Rescan |
| Claude Code | Ready | Local exact | Estimate unavailable | Manual estimate | Rescan |
| Cursor | Not found | Unavailable | Unavailable | Manual available | Configure |
| Gemini CLI | Needs setup | Telemetry required | Unavailable | Manual available | Configure |
| GitHub Copilot | Partial | Official report only | Partial | Unavailable | Connect report |
| OpenAI API Cost | Permission denied | Admin API required | Unavailable | Not account allowance | Replace key |

### Source Status Labels

Allowed source status labels:

- `Ready`
- `Syncing`
- `Not found`
- `Needs setup`
- `Permission denied`
- `Last sync failed`
- `No usage found`
- `Manual only`
- `Disabled`

Avoid vague labels like:

- `Broken`
- `Unknown error`
- `Inactive`
- `Unsupported` without a recovery action.

## API Costs View

API Costs is secondary.

It should show OpenAI organization/API-key usage and cost when Admin API access is available.

It must not imply that API organization usage is the same thing as personal coding-tool subscription allowance.

Recommended top metrics:

- Rolling 7-day API cost.
- Today's API cost.
- API usage tokens.
- Requests.
- Permission status.

Recommended breakdowns:

- By API key.
- By project.
- By model when available or inferable.
- Cost coverage by day.

State rules:

- If the key lacks `api.usage.read`, show a permission state.
- If costs are unavailable, do not show `$0.00`.
- If only usage is available, show usage normally and mark cost as unavailable.
- If allowance is unavailable, do not infer remaining personal subscription usage from API cost.

## Settings View

Settings should be plain and grouped by task.

Recommended groups:

- Local sources.
- API cost source.
- Manual allowance.
- Timezone.
- Data retention.
- Export aggregate data.
- Clear local aggregate cache.

Rules:

- Dangerous actions should require confirmation.
- Clearing local aggregate cache should not imply source credentials are removed.
- Replacing the API key should be separate from removing it.
- Timezone should be explicit because Daily and Weekly depend on it.

## First Launch

First launch should be a setup surface, not a landing page.

Primary action:

- Detect local sources.

Secondary actions:

- Explore sample data.
- Connect API cost source.

The page should include source setup status immediately after detection.

Avoid:

- Marketing hero copy.
- Large illustrations.
- Feature tour language.
- Any flow that requires an API key before local sources can be used.

## Core Components

### Metric Tile

Used for top-level Daily and Weekly numbers.

Required fields:

- Label.
- Value.
- Unit.
- Delta or coverage label, if relevant.
- Confidence badge, if relevant.

States:

- Normal.
- Partial.
- Manual estimate.
- Derived estimate.
- Unavailable.
- Stale.

Rules:

- Unavailable values should render as `Unavailable`, not `0`.
- Manual and derived values should show the confidence label near the number.
- Cost estimates should include coverage when partial.

### Status Badge

Used for source health, confidence, and coverage.

Recommended badge variants:

- Ready.
- Official.
- Local exact.
- Local estimated.
- Manual.
- Derived.
- Partial.
- Unavailable.
- Permission denied.
- Stale.

Badges should use subtle backgrounds and strong text. They should not look like primary buttons.

### Source Row

Used in Sources and trust panels.

Required fields:

- Source name.
- Source marker color.
- Status.
- Last sync.
- Data confidence.
- Primary action.

Rules:

- Keep row height stable.
- Do not hide failed states behind hover.
- The action should be concrete: `Rescan`, `Configure`, `Replace key`, `Retry`, or `View`.

### Trust Panel

Used in Daily and Weekly.

Required sections:

- Source freshness.
- Allowance status.
- Cost coverage.
- Sync issues.

Rules:

- Show healthy state compactly.
- Show issues as a short list.
- Keep wording operational.
- Do not use alarm language unless data is blocked.

### Chart

Recommended chart types:

- Bar chart.
- Stacked bar chart.
- Small horizontal breakdown bar.
- Compact trend sparkline only for secondary detail.

Chart rules:

- Use source colors consistently.
- Avoid chart legends that require excessive scanning.
- Put values in tables when exact comparison matters.
- Missing data should be visibly different from zero.

### Table

Use tables for top drivers and source lists.

Recommended columns for top drivers:

- Driver.
- Source.
- Model.
- Tokens.
- Share.
- Confidence.

Rules:

- Keep dense but readable.
- Right-align numeric values.
- Use tabular numbers.
- Allow source/model names to truncate with tooltips.

## Data Confidence Language

Confidence labels should be consistent across the product.

| Label | Meaning |
| --- | --- |
| `Official` | Fetched from an official API or official usage report. |
| `Local exact` | Parsed from local source data with explicit token fields. |
| `Local estimated` | Derived from local data but not exact provider usage. |
| `Manual` | Entered by the user. |
| `Derived` | Calculated from user-entered allowance plus synced usage. |
| `Partial` | Some data is available, but coverage is incomplete. |
| `Unavailable` | The product does not have this data. |

Rules:

- Do not mix confidence with source status.
- `Ready` means the source can be used.
- `Official` or `Local exact` means the value's confidence.
- A ready source can still have unavailable allowance.

## Empty And Error States

### No Sources Connected

Show:

- Detect local sources action.
- Explore sample data action.
- Optional API cost connect action.

Do not block on API setup.

### No Usage Found

Use when a source is connected but returns no usage for the selected range.

Offer:

- Retry sync.
- Change time range where applicable.
- View source setup.

Do not show this as an error.

### Source Not Found

Use when a local source directory or report was not found.

Offer:

- Rescan.
- Configure manually if supported.

### Permission Error

Use when a local path cannot be read or an API key lacks required access.

Offer:

- Rescan.
- Replace key.
- View source setup.

### Missing Allowance

Use when consumed usage exists but remaining allowance is unavailable.

Render:

- Usage consumed normally.
- Remaining as `Unavailable`.
- Reset as `Unavailable`.
- Optional action to configure manual allowance.

### Manual Or Derived Allowance

Render:

- Remaining value.
- Reset time.
- `Manual estimate` or `Derived estimate` badge near the value.

Do not visually equate this with official allowance.

### Partial Cost

Render:

- Usage normally.
- Cost estimate with `Partial` badge.
- Missing cost note in trust panel.

Do not silently show `$0.00`.

### Stale Data

Render:

- Last successful sync timestamp.
- Stale badge near page header or trust panel.
- Manual sync action.

## Interaction Rules

- Buttons should use icons where the action is familiar, plus text when the action is not obvious.
- Primary action should be teal.
- Secondary actions should be white or subtle gray with border.
- Destructive actions should be red only at the point of confirmation.
- Use segmented controls for Daily/Weekly local filters if needed.
- Use tabs only within pages if the page needs clear subviews.
- Use menus for source-specific actions.
- Use tooltips for icon-only buttons and truncated source/model names.

## Copy Rules

Use short operational language.

Prefer:

- `Synced 4 min ago`
- `Manual estimate`
- `Cost unavailable`
- `Permission denied`
- `No usage found`
- `Configure allowance`

Avoid:

- `We could not unlock the power of your analytics`
- `Everything is broken`
- `Zero cost` when costs are missing.
- `Refresh job`, `bucket`, `ingestion`, or other implementation terms in user-facing copy.

## Accessibility And Quality Bar

The PR 3 mock UI should meet these checks:

- Text does not overlap at 960px width.
- Numbers remain readable with tabular figures.
- Status is not conveyed by color alone.
- Buttons have visible focus states.
- Metric tiles have stable dimensions.
- Source rows do not change height on hover.
- Chart colors have enough contrast against the background.
- Empty and error states have concrete next actions.

## PR 3 Mock Data Requirements

Mock data should include:

- Codex ready with local exact usage.
- Claude Code ready with local exact usage.
- Cursor not found or manual-only.
- Gemini CLI needs setup.
- GitHub Copilot partial or official-report state.
- OpenAI API Cost permission-denied or optional connected state.
- Today usage total.
- Rolling 7-day usage total.
- Token split: input, output, cached input, reasoning output.
- At least one partial cost state.
- At least one missing allowance state.
- At least one manual or derived allowance state.
- At least one stale sync state.

The mock should prove the UI can represent uncertainty, not only a perfect happy path.

## PR 3 Acceptance Criteria

The desktop shell design is acceptable when:

- Daily is the default connected-state screen.
- Daily and Weekly render from mock aggregate data.
- Usage consumed, remaining usage, and reset timing are visible above the fold.
- Cost is visible as a secondary metric when available.
- Sources and Settings are reachable from primary navigation.
- API Costs is reachable but clearly secondary.
- Missing allowance is visible near remaining/reset metrics.
- Partial cost is visible near cost metrics.
- Source health is visible without deep navigation.
- First launch is a setup view, not a marketing page.
- Monthly is not present as a first-class route.

## Open Design Questions

- Should the first PR 3 mock support dark mode, or should dark mode wait until after the light theme is stable?
- Should source colors be user-customizable later, or fixed for consistency?
- Should API Costs be a primary sidebar item or nested under Sources until connected?
- Should the app include a compact tray/menu-bar view after V1?
- Should weekly default to rolling 7 days only, or should calendar week become a later toggle?

