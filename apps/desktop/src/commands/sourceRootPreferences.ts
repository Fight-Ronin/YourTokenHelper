import type { ExplicitRootSelectionDraft } from "../data/source-setup.mock.js";

export const LOAD_SAVED_SOURCE_ROOTS_COMMAND = "load_saved_source_roots" as const;
export const SAVE_SOURCE_ROOTS_COMMAND = "save_source_roots" as const;
export const CLEAR_SAVED_SOURCE_ROOTS_COMMAND = "clear_saved_source_roots" as const;
export const DEFAULT_AUTO_REFRESH_INTERVAL_MINUTES = 15;

export type SavedSourceRootsPayload = {
  codex_jsonl_root?: string;
  claude_code_jsonl_root?: string;
  gemini_cli_jsonl_root?: string;
  auto_refresh_enabled: boolean;
  auto_refresh_interval_minutes: number;
};

export type SourceRootPreferences = {
  rootDraft: ExplicitRootSelectionDraft;
  hasSavedRoots: boolean;
  autoRefreshEnabled: boolean;
  autoRefreshIntervalMinutes: number;
};

export type SourceRootPersistenceState =
  | { phase: "idle" }
  | { phase: "loading" }
  | { phase: "loaded" }
  | { phase: "saving" }
  | { phase: "saved" }
  | { phase: "dirty" }
  | { phase: "failed"; message: string };

export function defaultSourceRootPreferences(): SourceRootPreferences {
  return {
    rootDraft: {},
    hasSavedRoots: false,
    autoRefreshEnabled: false,
    autoRefreshIntervalMinutes: DEFAULT_AUTO_REFRESH_INTERVAL_MINUTES
  };
}

export function sourceRootPreferencesFromSaved(
  saved: Partial<SavedSourceRootsPayload>
): SourceRootPreferences {
  const rootDraft: ExplicitRootSelectionDraft = {};
  assignRootDraftValue(rootDraft, "codexJsonlRoot", saved.codex_jsonl_root);
  assignRootDraftValue(rootDraft, "claudeCodeJsonlRoot", saved.claude_code_jsonl_root);
  assignRootDraftValue(rootDraft, "geminiCliJsonlRoot", saved.gemini_cli_jsonl_root);
  const hasAnyRoot = hasAnySourceRoot(rootDraft);

  return {
    rootDraft,
    hasSavedRoots: hasAnyRoot,
    autoRefreshEnabled: Boolean(saved.auto_refresh_enabled) && hasAnyRoot,
    autoRefreshIntervalMinutes: normalizeAutoRefreshIntervalMinutes(
      saved.auto_refresh_interval_minutes
    )
  };
}

export function savedSourceRootsPayloadFromPreferences(
  preferences: SourceRootPreferences
): SavedSourceRootsPayload {
  return {
    codex_jsonl_root: normalizeRoot(preferences.rootDraft.codexJsonlRoot),
    claude_code_jsonl_root: normalizeRoot(preferences.rootDraft.claudeCodeJsonlRoot),
    gemini_cli_jsonl_root: normalizeRoot(preferences.rootDraft.geminiCliJsonlRoot),
    auto_refresh_enabled:
      preferences.autoRefreshEnabled &&
      hasAnySourceRoot(preferences.rootDraft),
    auto_refresh_interval_minutes: normalizeAutoRefreshIntervalMinutes(
      preferences.autoRefreshIntervalMinutes
    )
  };
}

export function sourceRootStorageLabel(
  preferences: SourceRootPreferences,
  state: SourceRootPersistenceState
) {
  if (state.phase === "loading") {
    return "Loading";
  }
  if (state.phase === "saving") {
    return "Saving";
  }
  if (state.phase === "dirty") {
    return "Unsaved changes";
  }
  if (state.phase === "failed") {
    return "Save unavailable";
  }
  return preferences.hasSavedRoots ? "Saved locally" : "This session";
}

export function autoRefreshStatusLabel(
  preferences: SourceRootPreferences,
  rootsAreSaved: boolean
) {
  if (!rootsAreSaved) {
    return "Needs saved roots";
  }
  return preferences.autoRefreshEnabled ? "On" : "Off";
}

export function shouldRunAutoRefresh({
  preferences,
  canInvoke,
  isRunning,
  rootsAreSaved
}: {
  preferences: SourceRootPreferences;
  canInvoke: boolean;
  isRunning: boolean;
  rootsAreSaved: boolean;
}) {
  return preferences.autoRefreshEnabled && rootsAreSaved && canInvoke && !isRunning;
}

export function canRunHeaderRefresh({
  canInvoke,
  isRunning,
  rootsAreSaved
}: {
  canInvoke: boolean;
  isRunning: boolean;
  rootsAreSaved: boolean;
}) {
  return canInvoke && rootsAreSaved && !isRunning;
}

export function headerRefreshButtonLabel(isRunning: boolean) {
  return isRunning ? "Refreshing" : "Refresh";
}

export function headerRefreshButtonTitle({
  canInvoke,
  isRunning,
  rootsAreSaved
}: {
  canInvoke: boolean;
  isRunning: boolean;
  rootsAreSaved: boolean;
}) {
  if (isRunning) {
    return "Refreshing local aggregate";
  }
  if (!canInvoke) {
    return "Save at least one source root in Sources first";
  }
  if (!rootsAreSaved) {
    return "Save roots before using header refresh";
  }
  return "Refresh local aggregate";
}

export function normalizeAutoRefreshIntervalMinutes(value: unknown) {
  const minutes = typeof value === "number" && Number.isFinite(value)
    ? Math.trunc(value)
    : DEFAULT_AUTO_REFRESH_INTERVAL_MINUTES;
  if (minutes < 5) {
    return DEFAULT_AUTO_REFRESH_INTERVAL_MINUTES;
  }
  if (minutes > 1440) {
    return 1440;
  }
  return minutes;
}

function normalizeRoot(value: string | undefined) {
  const normalized = value?.trim();
  return normalized || undefined;
}

function assignRootDraftValue(
  draft: ExplicitRootSelectionDraft,
  field: keyof ExplicitRootSelectionDraft,
  value: string | undefined
) {
  const root = normalizeRoot(value);
  if (root) {
    draft[field] = root;
  }
}

function hasAnySourceRoot(draft: ExplicitRootSelectionDraft) {
  return Boolean(
    normalizeRoot(draft.codexJsonlRoot) ||
      normalizeRoot(draft.claudeCodeJsonlRoot) ||
      normalizeRoot(draft.geminiCliJsonlRoot)
  );
}
