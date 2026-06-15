import type { RefreshSourcesManualDraft } from "../commands/refreshSourcesManualArgs.js";
import type { ApiCostSourceKind, SourceKind } from "../types.js";

export type LocalSetupSourceKind = Exclude<SourceKind, ApiCostSourceKind>;
export type ExplicitRootSourceKind = LocalSetupSourceKind;
export type ExplicitRootSelectionDraft = Pick<
  RefreshSourcesManualDraft,
  | "codexJsonlRoot"
  | "claudeCodeJsonlRoot"
  | "cursorJsonlRoot"
  | "geminiCliJsonlRoot"
  | "githubCopilotJsonlRoot"
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
  sourceKind: ExplicitRootSourceKind;
  state: "Selected (mock)" | "Not selected";
  displayValue:
    | "Selected, path hidden"
    | "No root selected";
  detail:
    | "Hidden root selected"
    | "Explicit root required"
    | "Usage export root"
    | "Telemetry/export root"
    | "Official report root";
  nextStep:
    | "Choose explicit root"
    | "Choose usage export"
    | "Choose telemetry export"
    | "Choose official report"
    | "Ready for refresh";
  pathPolicy: "no_path_stored" | "official_report_import";
  rootReadiness: "missing_explicit_root" | "selected_explicit_root";
  picker: ExplicitRootSourceKind;
  pickerAction?: "Change" | "Choose";
};

export const pathPolicyLabels: Record<ExplicitRootMockRow["pathPolicy"], string> = {
  no_path_stored: "Path hidden",
  official_report_import: "Official report import"
};

export const explicitRootSourceLabels: Record<ExplicitRootSourceKind, string> = {
  codex: "Codex",
  claude_code: "Claude Code",
  cursor: "Cursor",
  gemini_cli: "Gemini CLI",
  github_copilot: "GitHub Copilot"
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
  configuredExplicitRoots: readonly ExplicitRootSourceKind[];
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
  disabledAriaLabel: "Manual refresh is disabled until at least one explicit root and Tauri wiring are ready",
  disabledTitle: "Add at least one hidden source root"
};

export const explicitRootMockRows: readonly ExplicitRootMockRow[] = [
  {
    sourceKind: "codex",
    state: "Not selected",
    displayValue: "No root selected",
    detail: "Explicit root required",
    nextStep: "Choose explicit root",
    pathPolicy: "no_path_stored",
    rootReadiness: "missing_explicit_root",
    picker: "codex",
    pickerAction: "Choose"
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
    state: "Not selected",
    displayValue: "No root selected",
    detail: "Usage export root",
    nextStep: "Choose usage export",
    pathPolicy: "no_path_stored",
    rootReadiness: "missing_explicit_root",
    picker: "cursor",
    pickerAction: "Choose"
  },
  {
    sourceKind: "gemini_cli",
    state: "Not selected",
    displayValue: "No root selected",
    detail: "Telemetry/export root",
    nextStep: "Choose telemetry export",
    pathPolicy: "no_path_stored",
    rootReadiness: "missing_explicit_root",
    picker: "gemini_cli",
    pickerAction: "Choose"
  },
  {
    sourceKind: "github_copilot",
    state: "Not selected",
    displayValue: "No root selected",
    detail: "Official report root",
    nextStep: "Choose official report",
    pathPolicy: "official_report_import",
    rootReadiness: "missing_explicit_root",
    picker: "github_copilot",
    pickerAction: "Choose"
  }
];

export function getManualRefreshReadiness(
  rows: readonly ExplicitRootMockRow[] = explicitRootMockRows,
  options: ManualRefreshReadinessOptions = {}
): ManualRefreshReadiness {
  const hasTauriWiring = options.hasTauriWiring ?? false;
  const configuredExplicitRoots = rows
    .filter((row) => row.rootReadiness === "selected_explicit_root")
    .map((row) => row.sourceKind);
  const canRun = hasTauriWiring && configuredExplicitRoots.length > 0;

  return {
    canRun,
    hasTauriWiring,
    configuredExplicitRoots,
    blockedReason: canRun ? null : manualRefreshMockState.blockedReason
  };
}

export function manualRefreshRootsLabel(readiness: ManualRefreshReadiness) {
  if (readiness.configuredExplicitRoots.length === 0) {
    return "No roots selected";
  }
  const configuredLabels = readiness.configuredExplicitRoots.map((source) => explicitRootSourceLabels[source]).join(", ");
  return `Ready: ${configuredLabels}`;
}

export function manualRefreshNeedsLabel(readiness: ManualRefreshReadiness) {
  if (readiness.configuredExplicitRoots.length > 0) {
    return "None";
  }
  return "At least one import root";
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
    const hasExplicitRoot = Boolean(rootValueForSource(row.sourceKind, draft)?.trim());
    return {
      ...row,
      state: hasExplicitRoot ? "Selected (mock)" : "Not selected",
      displayValue: hasExplicitRoot ? "Selected, path hidden" : "No root selected",
      detail: hasExplicitRoot ? "Hidden root selected" : row.detail,
      nextStep: hasExplicitRoot ? "Ready for refresh" : row.nextStep,
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
      cursorJsonlRoot: draft.cursorJsonlRoot?.trim(),
      geminiCliJsonlRoot: draft.geminiCliJsonlRoot?.trim(),
      githubCopilotJsonlRoot: draft.githubCopilotJsonlRoot?.trim(),
      startedAt: draft.startedAt?.trim()
    }
  };
}

function rootValueForSource(sourceKind: ExplicitRootSourceKind, draft: ExplicitRootSelectionDraft) {
  return draft[rootFieldForSource(sourceKind)];
}

function rootFieldForSource(sourceKind: ExplicitRootSourceKind): keyof ExplicitRootSelectionDraft {
  if (sourceKind === "codex") {
    return "codexJsonlRoot";
  }
  if (sourceKind === "claude_code") {
    return "claudeCodeJsonlRoot";
  }
  if (sourceKind === "cursor") {
    return "cursorJsonlRoot";
  }
  if (sourceKind === "gemini_cli") {
    return "geminiCliJsonlRoot";
  }
  return "githubCopilotJsonlRoot";
}
