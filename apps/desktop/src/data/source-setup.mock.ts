import type { RefreshSourcesManualDraft } from "../commands/refreshSourcesManualArgs.js";
import type { ApiCostSourceKind, SourceKind } from "../types.js";

export type LocalSetupSourceKind = Exclude<SourceKind, ApiCostSourceKind>;
export type ExplicitRootSourceKind = "codex" | "claude_code";
export type ExplicitRootSelectionDraft = Pick<
  RefreshSourcesManualDraft,
  "codexJsonlRoot" | "claudeCodeJsonlRoot"
>;
export type ExplicitRootSetupAction =
  | {
      type: "select_root";
      sourceKind: ExplicitRootSourceKind;
      root: string;
    }
  | {
      type: "clear_root";
      sourceKind: ExplicitRootSourceKind;
    };

export type ExplicitRootMockRow = {
  sourceKind: LocalSetupSourceKind;
  state: "Selected (mock)" | "Not selected" | "Manual" | "Setup required" | "Report path";
  displayValue:
    | "Selected, path hidden"
    | "No root selected"
    | "Manual status"
    | "Telemetry/export setup"
    | "Official report";
  detail: "Hidden root selected" | "Explicit root required" | "Status only" | "Official report";
  nextStep:
    | "Needs explicit root"
    | "Choose explicit root"
    | "Manual status only"
    | "Configure telemetry or export"
    | "Use official report"
    | "Ready for gated refresh";
  pathPolicy: "no_path_stored" | "no_local_parser" | "official_report_only";
  rootReadiness: "label_only" | "missing_explicit_root" | "selected_explicit_root" | "not_required";
  picker?: "codex" | "claude_code";
  pickerAction?: "Change" | "Choose";
};

export const pathPolicyLabels: Record<ExplicitRootMockRow["pathPolicy"], string> = {
  no_path_stored: "Path hidden",
  no_local_parser: "No local parser",
  official_report_only: "Official report"
};

export const explicitRootSourceLabels: Record<ExplicitRootSourceKind, string> = {
  codex: "Codex",
  claude_code: "Claude Code"
};

export type ManualRefreshUiState = {
  commandName: "refresh_sources_manual";
  statusLabel: "Blocked";
  canRun: false;
  blockedReason: "explicit_roots_and_tauri_wiring";
  disabledAriaLabel: string;
  disabledTitle: string;
};

export type ManualRefreshRunState =
  | { phase: "idle" }
  | { phase: "running" }
  | { phase: "succeeded"; message: string }
  | { phase: "failed"; message: string };

export type ManualRefreshReadiness = {
  canRun: boolean;
  hasTauriWiring: boolean;
  missingExplicitRoots: readonly ("codex" | "claude_code")[];
  blockedReason: ManualRefreshUiState["blockedReason"] | null;
};

export type ManualRefreshReadinessOptions = {
  hasTauriWiring?: boolean;
};

export type HiddenRootManualRefreshDraft = RefreshSourcesManualDraft & ExplicitRootSelectionDraft;

export type HiddenRootManualRefreshState =
  | {
      canInvoke: true;
      rows: readonly ExplicitRootMockRow[];
      readiness: ManualRefreshReadiness;
      draft: RefreshSourcesManualDraft;
    }
  | {
      canInvoke: false;
      rows: readonly ExplicitRootMockRow[];
      readiness: ManualRefreshReadiness;
      draft: null;
    };

export const manualRefreshMockState: ManualRefreshUiState = {
  commandName: "refresh_sources_manual",
  statusLabel: "Blocked",
  canRun: false,
  blockedReason: "explicit_roots_and_tauri_wiring",
  disabledAriaLabel: "Manual refresh is disabled until explicit roots and Tauri wiring are ready",
  disabledTitle: "Manual refresh is not wired in mock mode"
};

export const explicitRootMockRows: readonly ExplicitRootMockRow[] = [
  {
    sourceKind: "codex",
    state: "Selected (mock)",
    displayValue: "Selected, path hidden",
    detail: "Explicit root required",
    nextStep: "Needs explicit root",
    pathPolicy: "no_path_stored",
    rootReadiness: "label_only",
    picker: "codex",
    pickerAction: "Change"
  },
  {
    sourceKind: "claude_code",
    state: "Not selected",
    displayValue: "No root selected",
    detail: "Explicit root required",
    nextStep: "Choose explicit root",
    pathPolicy: "no_path_stored",
    rootReadiness: "missing_explicit_root",
    picker: "claude_code",
    pickerAction: "Choose"
  },
  {
    sourceKind: "cursor",
    state: "Manual",
    displayValue: "Manual status",
    detail: "Status only",
    nextStep: "Manual status only",
    pathPolicy: "no_local_parser",
    rootReadiness: "not_required"
  },
  {
    sourceKind: "gemini_cli",
    state: "Setup required",
    displayValue: "Telemetry/export setup",
    detail: "Status only",
    nextStep: "Configure telemetry or export",
    pathPolicy: "no_local_parser",
    rootReadiness: "not_required"
  },
  {
    sourceKind: "github_copilot",
    state: "Report path",
    displayValue: "Official report",
    detail: "Official report",
    nextStep: "Use official report",
    pathPolicy: "official_report_only",
    rootReadiness: "not_required"
  }
];

export function getManualRefreshReadiness(
  rows: readonly ExplicitRootMockRow[] = explicitRootMockRows,
  options: ManualRefreshReadinessOptions = {}
): ManualRefreshReadiness {
  const hasTauriWiring = options.hasTauriWiring ?? false;
  const missingExplicitRoots = rows
    .filter(
      (row): row is ExplicitRootMockRow & { sourceKind: ExplicitRootSourceKind } =>
        (row.sourceKind === "codex" || row.sourceKind === "claude_code") &&
        row.rootReadiness !== "selected_explicit_root"
    )
    .map((row) => row.sourceKind);
  const canRun = hasTauriWiring && missingExplicitRoots.length === 0;

  return {
    canRun,
    hasTauriWiring,
    missingExplicitRoots,
    blockedReason: canRun ? null : manualRefreshMockState.blockedReason
  };
}

export function manualRefreshRootsLabel(readiness: ManualRefreshReadiness) {
  if (readiness.missingExplicitRoots.length === 0) {
    return "Ready";
  }
  const missingLabels = readiness.missingExplicitRoots.map((source) => explicitRootSourceLabels[source]).join(", ");
  return `Missing ${missingLabels}`;
}

export function manualRefreshNeedsLabel(readiness: ManualRefreshReadiness) {
  if (readiness.missingExplicitRoots.length === 0) {
    return "None";
  }
  return readiness.missingExplicitRoots.map((source) => explicitRootSourceLabels[source]).join(", ");
}

export function manualRefreshBridgeLabel(readiness: ManualRefreshReadiness) {
  return readiness.hasTauriWiring ? "wired" : "not wired";
}

export function manualRefreshStatusLabel(canInvoke: boolean, runState: ManualRefreshRunState) {
  if (runState.phase === "running") {
    return "Running";
  }
  if (runState.phase === "succeeded") {
    return "Succeeded";
  }
  if (runState.phase === "failed") {
    return "Failed";
  }
  return canInvoke ? "Ready" : manualRefreshMockState.statusLabel;
}

export function manualRefreshSuccessMessage(totalTokens: number) {
  return `Updated ${new Intl.NumberFormat("en-US").format(totalTokens)} aggregate tokens`;
}

export function buildExplicitRootSetupRows(
  draft: ExplicitRootSelectionDraft,
  rows: readonly ExplicitRootMockRow[] = explicitRootMockRows
): readonly ExplicitRootMockRow[] {
  return rows.map((row) => {
    if (row.sourceKind !== "codex" && row.sourceKind !== "claude_code") {
      return row;
    }

    const hasExplicitRoot = Boolean(rootValueForSource(row.sourceKind, draft)?.trim());
    return {
      ...row,
      state: hasExplicitRoot ? "Selected (mock)" : "Not selected",
      displayValue: hasExplicitRoot ? "Selected, path hidden" : "No root selected",
      detail: hasExplicitRoot ? "Hidden root selected" : "Explicit root required",
      nextStep: hasExplicitRoot ? "Ready for gated refresh" : "Choose explicit root",
      rootReadiness: hasExplicitRoot ? "selected_explicit_root" : "missing_explicit_root",
      pickerAction: hasExplicitRoot ? "Change" : "Choose"
    };
  });
}

export function applyExplicitRootSetupAction(
  draft: ExplicitRootSelectionDraft,
  action: ExplicitRootSetupAction
): ExplicitRootSelectionDraft {
  const next: ExplicitRootSelectionDraft = { ...draft };
  const field = rootFieldForSource(action.sourceKind);

  if (action.type === "clear_root") {
    delete next[field];
    return next;
  }

  const normalizedRoot = action.root.trim();
  if (normalizedRoot) {
    next[field] = normalizedRoot;
  } else {
    delete next[field];
  }
  return next;
}

export function buildManualRefreshDraftFromHiddenRoots(
  draft: HiddenRootManualRefreshDraft,
  options: ManualRefreshReadinessOptions = {}
): HiddenRootManualRefreshState {
  const rows = buildExplicitRootSetupRows(draft);
  const readiness = getManualRefreshReadiness(rows, options);
  if (!readiness.canRun) {
    return {
      canInvoke: false,
      rows,
      readiness,
      draft: null
    };
  }

  return {
    canInvoke: true,
    rows,
    readiness,
    draft: {
      endDayUtc: draft.endDayUtc.trim(),
      codexJsonlRoot: draft.codexJsonlRoot?.trim(),
      claudeCodeJsonlRoot: draft.claudeCodeJsonlRoot?.trim(),
      startedAt: draft.startedAt?.trim()
    }
  };
}

function rootValueForSource(sourceKind: ExplicitRootSourceKind, draft: ExplicitRootSelectionDraft) {
  return sourceKind === "codex" ? draft.codexJsonlRoot : draft.claudeCodeJsonlRoot;
}

function rootFieldForSource(sourceKind: ExplicitRootSourceKind): keyof ExplicitRootSelectionDraft {
  return sourceKind === "codex" ? "codexJsonlRoot" : "claudeCodeJsonlRoot";
}
