import { useEffect, useState, type ReactNode } from "react";
import {
  BarChart3,
  CalendarDays,
  CheckCircle2,
  CircleDollarSign,
  Clock3,
  RefreshCw,
  Save,
  Settings,
  TableProperties,
  X
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { loadStartupStorageSummary } from "./commands/loadStorageSummaryClient.js";
import {
  defaultApiProviderCredentialStatuses,
  apiProviderCredentialStatusFromPayload,
  loadApiProviderCredentials,
  removeApiProviderCredential as removeApiProviderCredentialCommand,
  saveApiProviderCredential as saveApiProviderCredentialCommand
} from "./commands/apiProviderCredentials.js";
import {
  syncApiProviderBilling,
  type ApiProviderEndpointStatusesPayload
} from "./commands/apiProviderBillingSync.js";
import {
  defaultManualAllowanceEndDayUtc,
  invokeSaveManualAllowance,
  isManualAllowanceSuccessPayload
} from "./commands/manualAllowance.js";
import { invokeRefreshSourcesManual } from "./commands/refreshSourcesManualClient.js";
import { isRefreshCommandErrorPayload, manualRefreshEndDayUtc } from "./commands/sourceRefreshSummary.js";
import {
  clearSourceRootPreferences,
  loadSourceRootPreferences,
  saveSourceRootPreferences
} from "./commands/sourceRootPreferencesClient.js";
import {
  autoRefreshStatusLabel,
  canRunHeaderRefresh,
  defaultSourceRootPreferences,
  headerRefreshButtonLabel,
  headerRefreshButtonTitle,
  shouldRunAutoRefresh,
  sourceRootStorageLabel,
  type SourceRootPersistenceState,
  type SourceRootPreferences
} from "./commands/sourceRootPreferences.js";
import {
  buildDashboardSummaryFromRefresh,
  dashboardQualityLabel,
  emptyDashboardSummaryPayload,
  emptyTokenTotals,
  latestSummaryDay,
  refreshRecencyLabel,
  sourceUsageRows,
  sourceTotalsForDay,
  startupStorageStatusLabel,
  type DashboardDataMode,
  type SourceUsageProgress,
  type StartupStorageReadState
} from "./data/dashboard-summary.js";
import {
  apiCostProviderIds,
  apiCostProviderStatusFor,
  apiCostProviderStatusLabel,
  type ApiCostProviderStatus
} from "./data/api-cost-providers.js";
import {
  applyExplicitRootSetupAction,
  buildManualRefreshDraftFromHiddenRoots,
  manualRefreshBridgeLabel,
  manualRefreshMockState,
  manualRefreshNeedsLabel,
  manualRefreshRootsLabel,
  manualRefreshStatusLabel,
  manualRefreshSuccessMessage,
  pathPolicyLabels
} from "./data/source-setup.mock.js";
import type {
  ExplicitRootMockRow,
  ExplicitRootSelectionDraft,
  ExplicitRootSourceKind,
  ManualRefreshReadiness,
  ManualRefreshRunState
} from "./data/source-setup.mock.js";
import type {
  ApiCostSourceKind,
  AllowanceWindow,
  MockSummaryPayload,
  RefreshResult,
  RefreshState,
  RefreshStorageSummaryPayload,
  SourceKind,
  SourceRefreshSummaryPayload,
  TokenTotals
} from "./types";

type ViewId = "daily" | "weekly" | "sources" | "api_costs" | "settings";
type ManualAllowanceFormState = {
  sourceKind: SourceKind;
  unit: AllowanceWindow["unit"];
  limitAmount: string;
  remainingAmount: string;
  resetAt: string;
};
type ManualAllowanceSaveState =
  | { phase: "idle" }
  | { phase: "saving" }
  | { phase: "succeeded"; message: string }
  | { phase: "failed"; message: string };
type ApiProviderCredentialFormState = {
  providerId: ApiCostSourceKind;
  apiKey: string;
};
type ApiProviderCredentialRunState =
  | { phase: "idle" }
  | { phase: "loading" }
  | { phase: "loaded" }
  | { phase: "saving" }
  | { phase: "saved"; message: string }
  | { phase: "syncing" }
  | { phase: "synced"; message: string }
  | { phase: "removing" }
  | { phase: "removed"; message: string }
  | { phase: "failed"; message: string };
type ApiProviderEndpointDiagnostics = Partial<Record<ApiCostSourceKind, ApiProviderEndpointStatusesPayload>>;

const sourceLabels: Record<SourceKind, string> = {
  codex: "Codex",
  claude_code: "Claude Code",
  cursor: "Cursor",
  gemini_cli: "Gemini CLI",
  github_copilot: "GitHub Copilot",
  openai_api_cost: "OpenAI API Cost",
  claude_api_cost: "Claude API Cost",
  gemini_api_cost: "Gemini API Cost",
  deepseek_api_cost: "DeepSeek API Cost"
};

const sourceColors: Record<SourceKind, string> = {
  codex: "#0F766E",
  claude_code: "#C2410C",
  cursor: "#111827",
  gemini_cli: "#2563EB",
  github_copilot: "#16A34A",
  openai_api_cost: "#7C3AED",
  claude_api_cost: "#8B5CF6",
  gemini_api_cost: "#4F46E5",
  deepseek_api_cost: "#0891B2"
};

type ApiCostProvider = {
  sourceKind: ApiCostSourceKind;
  detail: string;
};

const apiCostProviderDetails: Record<ApiCostSourceKind, string> = {
  openai_api_cost: "Stored Admin usage/cost imports are supported; live sync needs an OpenAI Admin API key",
  claude_api_cost: "Official billing adapter still needs verification before sync is enabled",
  gemini_api_cost: "Official billing adapter still needs verification before sync is enabled",
  deepseek_api_cost: "Official billing adapter still needs verification before sync is enabled"
};

const apiCostProviders: readonly ApiCostProvider[] = apiCostProviderIds.map((sourceKind) => ({
  sourceKind,
  detail: apiCostProviderDetails[sourceKind]
}));

const navItems: Array<{ id: ViewId; label: string; icon: LucideIcon; secondary?: boolean }> = [
  { id: "daily", label: "Daily", icon: CalendarDays },
  { id: "weekly", label: "Weekly", icon: BarChart3 },
  { id: "sources", label: "Sources", icon: TableProperties },
  { id: "api_costs", label: "API Costs", icon: CircleDollarSign, secondary: true },
  { id: "settings", label: "Settings", icon: Settings }
];
const manualAllowanceSourceKinds: readonly SourceKind[] = [
  "codex",
  "claude_code",
  "gemini_cli"
];
const manualAllowanceUnits: readonly AllowanceWindow["unit"][] = ["tokens", "credits", "usd", "requests"];
const defaultManualAllowanceFormState: ManualAllowanceFormState = {
  sourceKind: "codex",
  unit: "tokens",
  limitAmount: "",
  remainingAmount: "",
  resetAt: ""
};
const defaultApiProviderCredentialFormState: ApiProviderCredentialFormState = {
  providerId: "openai_api_cost",
  apiKey: ""
};

export function App() {
  const [activeView, setActiveView] = useState<ViewId>("daily");
  const [dashboardPayload, setDashboardPayload] = useState<MockSummaryPayload>(() => emptyDashboardSummaryPayload());
  const [dashboardDataMode, setDashboardDataMode] = useState<DashboardDataMode>("empty");
  const [lastRefreshResults, setLastRefreshResults] = useState<readonly RefreshResult[] | null>(null);
  const [startupStorageReadState, setStartupStorageReadState] = useState<StartupStorageReadState>({ phase: "idle" });
  const [sourceRootPreferences, setSourceRootPreferences] = useState<SourceRootPreferences>(
    defaultSourceRootPreferences
  );
  const [sourceRootPersistenceState, setSourceRootPersistenceState] =
    useState<SourceRootPersistenceState>({ phase: "idle" });
  const [manualRefreshRunState, setManualRefreshRunState] = useState<ManualRefreshRunState>({ phase: "idle" });
  const [manualAllowanceFormState, setManualAllowanceFormState] =
    useState<ManualAllowanceFormState>(defaultManualAllowanceFormState);
  const [manualAllowanceSaveState, setManualAllowanceSaveState] =
    useState<ManualAllowanceSaveState>({ phase: "idle" });
  const [apiProviderCredentialStatuses, setApiProviderCredentialStatuses] =
    useState<ApiCostProviderStatus[]>(defaultApiProviderCredentialStatuses);
  const [apiProviderCredentialFormState, setApiProviderCredentialFormState] =
    useState<ApiProviderCredentialFormState>(defaultApiProviderCredentialFormState);
  const [apiProviderCredentialRunState, setApiProviderCredentialRunState] =
    useState<ApiProviderCredentialRunState>({ phase: "idle" });
  const [apiProviderEndpointDiagnostics, setApiProviderEndpointDiagnostics] =
    useState<ApiProviderEndpointDiagnostics>({});
  const view = navItems.find((item) => item.id === activeView) ?? navItems[0];
  const manualRefreshBoundary = buildManualRefreshDraftFromHiddenRoots(
    {
      endDayUtc: manualRefreshEndDayUtc(),
      ...sourceRootPreferences.rootDraft
    },
    { hasTauriWiring: true }
  );
  const rootsAreSavedForAutoRefresh =
    sourceRootPreferences.hasSavedRoots &&
    (sourceRootPersistenceState.phase === "loaded" || sourceRootPersistenceState.phase === "saved");
  const headerRefreshState = {
    canInvoke: manualRefreshBoundary.canInvoke,
    isRunning: manualRefreshRunState.phase === "running",
    rootsAreSaved: rootsAreSavedForAutoRefresh
  };
  const headerCanRefresh = canRunHeaderRefresh(headerRefreshState);
  const headerRefreshTitle = headerRefreshButtonTitle(headerRefreshState);

  useEffect(() => {
    let isCancelled = false;

    async function loadPersistedSummary() {
      setStartupStorageReadState({ phase: "loading" });
      const outcome = await loadStartupStorageSummary({ end_day_utc: manualRefreshEndDayUtc() });
      if (isCancelled) {
        return;
      }
      if (outcome.ok) {
        setDashboardPayload(buildDashboardSummaryFromRefresh(outcome.payload));
        setDashboardDataMode("local_refresh");
        setStartupStorageReadState({ phase: "loaded" });
        return;
      }
      setStartupStorageReadState({ phase: "unavailable", message: outcome.message });
    }

    void loadPersistedSummary();

    return () => {
      isCancelled = true;
    };
  }, []);

  useEffect(() => {
    let isCancelled = false;

    async function loadPersistedRoots() {
      setSourceRootPersistenceState({ phase: "loading" });
      const outcome = await loadSourceRootPreferences();
      if (isCancelled) {
        return;
      }
      if (outcome.ok) {
        setSourceRootPreferences(outcome.preferences);
        setSourceRootPersistenceState(outcome.preferences.hasSavedRoots ? { phase: "loaded" } : { phase: "idle" });
        return;
      }
      setSourceRootPersistenceState({ phase: "failed", message: outcome.message });
    }

    void loadPersistedRoots();

    return () => {
      isCancelled = true;
    };
  }, []);

  useEffect(() => {
    let isCancelled = false;

    async function loadCredentialStatuses() {
      setApiProviderCredentialRunState({ phase: "loading" });
      const outcome = await loadApiProviderCredentials();
      if (isCancelled) {
        return;
      }
      if (outcome.ok) {
        setApiProviderCredentialStatuses(outcome.statuses);
        setApiProviderCredentialRunState({ phase: "loaded" });
        return;
      }
      setApiProviderCredentialStatuses(defaultApiProviderCredentialStatuses());
      setApiProviderCredentialRunState({ phase: "failed", message: outcome.error.error.message });
    }

    void loadCredentialStatuses();

    return () => {
      isCancelled = true;
    };
  }, []);

  function handleRefreshSummary(refreshSummary: SourceRefreshSummaryPayload) {
    const payload = buildDashboardSummaryFromRefresh(refreshSummary.storage_summary);
    setDashboardPayload(payload);
    setDashboardDataMode("local_refresh");
    setLastRefreshResults(refreshSummary.refresh_results);
    setStartupStorageReadState({ phase: "loaded" });
    return payload;
  }

  function updateExplicitRoot(sourceKind: ExplicitRootSourceKind, root: string) {
    setSourceRootPreferences((preferences) => ({
      ...preferences,
      rootDraft: applyExplicitRootSetupAction(preferences.rootDraft, {
        type: "select_root",
        sourceKind,
        root
      }),
      autoRefreshEnabled: false
    }));
    setSourceRootPersistenceState((state) =>
      state.phase === "loaded" || state.phase === "saved" || state.phase === "dirty"
        ? { phase: "dirty" }
        : state
    );
    setManualRefreshRunState({ phase: "idle" });
  }

  function clearExplicitRoot(sourceKind: ExplicitRootSourceKind) {
    setSourceRootPreferences((preferences) => ({
      ...preferences,
      rootDraft: applyExplicitRootSetupAction(preferences.rootDraft, {
        type: "clear_root",
        sourceKind
      }),
      autoRefreshEnabled: false
    }));
    setSourceRootPersistenceState((state) =>
      state.phase === "loaded" || state.phase === "saved" || state.phase === "dirty"
        ? { phase: "dirty" }
        : state
    );
    setManualRefreshRunState({ phase: "idle" });
  }

  async function saveExplicitRoots() {
    if (!manualRefreshBoundary.canInvoke) {
      return;
    }

    const preferences: SourceRootPreferences = {
      ...sourceRootPreferences,
      hasSavedRoots: true,
      autoRefreshEnabled:
        sourceRootPreferences.autoRefreshEnabled && manualRefreshBoundary.canInvoke
    };
    setSourceRootPersistenceState({ phase: "saving" });
    const outcome = await saveSourceRootPreferences(preferences);
    if (!outcome.ok) {
      setSourceRootPersistenceState({ phase: "failed", message: outcome.message });
      return;
    }
    setSourceRootPreferences(outcome.preferences);
    setSourceRootPersistenceState({ phase: "saved" });
  }

  async function forgetExplicitRoots() {
    setSourceRootPersistenceState({ phase: "saving" });
    const outcome = await clearSourceRootPreferences();
    if (!outcome.ok) {
      setSourceRootPersistenceState({ phase: "failed", message: outcome.message });
      return;
    }
    setSourceRootPreferences(outcome.preferences);
    setSourceRootPersistenceState({ phase: "idle" });
    setManualRefreshRunState({ phase: "idle" });
  }

  async function setAutoRefreshEnabled(enabled: boolean) {
    if (enabled && (!manualRefreshBoundary.canInvoke || !rootsAreSavedForAutoRefresh)) {
      return;
    }

    const preferences: SourceRootPreferences = {
      ...sourceRootPreferences,
      autoRefreshEnabled: enabled
    };
    if (!sourceRootPreferences.hasSavedRoots) {
      setSourceRootPreferences(preferences);
      return;
    }

    setSourceRootPersistenceState({ phase: "saving" });
    const outcome = await saveSourceRootPreferences(preferences);
    if (!outcome.ok) {
      setSourceRootPersistenceState({ phase: "failed", message: outcome.message });
      return;
    }
    setSourceRootPreferences(outcome.preferences);
    setSourceRootPersistenceState({ phase: "saved" });
  }

  async function runRefreshWithDraft(draft: NonNullable<typeof manualRefreshBoundary.draft>) {
    setManualRefreshRunState({ phase: "running" });
    const outcome = await invokeRefreshSourcesManual(draft);
    if (!outcome.ok) {
      setManualRefreshRunState({ phase: "failed", message: outcome.error.error.message });
      return;
    }
    if (isRefreshCommandErrorPayload(outcome.result)) {
      setManualRefreshRunState({ phase: "failed", message: outcome.result.error.message });
      return;
    }

    const payload = handleRefreshSummary(outcome.result);
    setManualRefreshRunState({
      phase: "succeeded",
      message: manualRefreshSuccessMessage(payload.summary.totals.total_tokens)
    });
  }

  async function handleManualRefresh() {
    if (!manualRefreshBoundary.canInvoke) {
      return;
    }
    await runRefreshWithDraft(manualRefreshBoundary.draft);
  }

  async function handleHeaderRefresh() {
    if (!headerCanRefresh || !manualRefreshBoundary.canInvoke) {
      return;
    }
    await runRefreshWithDraft(manualRefreshBoundary.draft);
  }

  function updateManualAllowanceDraft(patch: Partial<ManualAllowanceFormState>) {
    setManualAllowanceFormState((state) => ({ ...state, ...patch }));
    setManualAllowanceSaveState((state) =>
      state.phase === "succeeded" || state.phase === "failed" ? { phase: "idle" } : state
    );
  }

  function updateApiProviderCredentialDraft(patch: Partial<ApiProviderCredentialFormState>) {
    setApiProviderCredentialFormState((state) => ({ ...state, ...patch }));
    setApiProviderCredentialRunState((state) =>
      state.phase === "saved" || state.phase === "removed" || state.phase === "failed" ? { phase: "idle" } : state
    );
  }

  async function saveApiProviderCredential() {
    const providerId = apiProviderCredentialFormState.providerId;
    setApiProviderCredentialRunState({ phase: "saving" });
    const outcome = await saveApiProviderCredentialCommand(apiProviderCredentialFormState);
    if (!outcome.ok) {
      setApiProviderCredentialRunState({ phase: "failed", message: outcome.error.error.message });
      return;
    }
    setApiProviderCredentialStatuses(outcome.statuses);
    clearApiProviderEndpointDiagnostics(providerId);
    setApiProviderCredentialFormState((state) => ({ ...state, apiKey: "" }));
    setApiProviderCredentialRunState({
      phase: "saved",
      message: `Saved ${sourceLabels[providerId]} credential`
    });
  }

  async function removeApiProviderCredential() {
    const providerId = apiProviderCredentialFormState.providerId;
    setApiProviderCredentialRunState({ phase: "removing" });
    const outcome = await removeApiProviderCredentialCommand(providerId);
    if (!outcome.ok) {
      setApiProviderCredentialRunState({ phase: "failed", message: outcome.error.error.message });
      return;
    }
    setApiProviderCredentialStatuses(outcome.statuses);
    clearApiProviderEndpointDiagnostics(providerId);
    setApiProviderCredentialFormState((state) => ({ ...state, apiKey: "" }));
    setApiProviderCredentialRunState({
      phase: "removed",
      message: `Removed ${sourceLabels[providerId]} credential`
    });
  }

  async function syncApiProviderBillingNow() {
    const providerId = apiProviderCredentialFormState.providerId;
    setApiProviderCredentialRunState({ phase: "syncing" });
    const outcome = await syncApiProviderBilling({
      providerId,
      endDayUtc: manualRefreshEndDayUtc()
    });
    if (!outcome.ok) {
      setApiProviderCredentialRunState({ phase: "failed", message: outcome.error.error.message });
      return;
    }

    setDashboardPayload(buildDashboardSummaryFromRefresh(outcome.result.storage_summary));
    setDashboardDataMode("local_refresh");
    setStartupStorageReadState({ phase: "loaded" });
    const providerStatus = outcome.result.provider_status;
    const normalizedProviderStatus = providerStatus
      ? apiProviderCredentialStatusFromPayload(providerStatus)
      : undefined;
    if (normalizedProviderStatus) {
      setApiProviderCredentialStatuses((statuses) =>
        replaceApiProviderCredentialStatus(statuses, normalizedProviderStatus)
      );
    }
    if (outcome.result.endpoint_statuses) {
      setApiProviderEndpointDiagnostics((statuses) => ({
        ...statuses,
        [providerId]: outcome.result.endpoint_statuses
      }));
    }
    setApiProviderCredentialRunState({
      phase:
        normalizedProviderStatus === undefined || normalizedProviderStatus.status === "ready"
          ? "synced"
          : "failed",
      message: apiProviderBillingSyncMessage(
        outcome.result.sync_result.events_seen,
        normalizedProviderStatus
      )
    });
  }

  function clearApiProviderEndpointDiagnostics(providerId: ApiCostSourceKind) {
    setApiProviderEndpointDiagnostics((statuses) => {
      const next = { ...statuses };
      delete next[providerId];
      return next;
    });
  }

  async function saveManualAllowance() {
    setManualAllowanceSaveState({ phase: "saving" });
    const outcome = await invokeSaveManualAllowance({
      endDayUtc: defaultManualAllowanceEndDayUtc(),
      sourceKind: manualAllowanceFormState.sourceKind,
      unit: manualAllowanceFormState.unit,
      limitAmount: Number(manualAllowanceFormState.limitAmount),
      remainingAmount: optionalNumberInput(manualAllowanceFormState.remainingAmount),
      resetAt: optionalTextInput(manualAllowanceFormState.resetAt)
    });
    if (!outcome.ok) {
      setManualAllowanceSaveState({ phase: "failed", message: outcome.error.error.message });
      return;
    }
    if (!isManualAllowanceSuccessPayload(outcome.result)) {
      setManualAllowanceSaveState({ phase: "failed", message: outcome.result.error.message });
      return;
    }

    setDashboardPayload(buildDashboardSummaryFromRefresh(outcome.result.storage_summary));
    setDashboardDataMode("local_refresh");
    setStartupStorageReadState({ phase: "loaded" });
    setManualAllowanceSaveState({
      phase: "succeeded",
      message: `Saved ${sourceLabels[outcome.result.allowance_window.source_kind]} allowance`
    });
  }

  const manualRefreshKey = manualRefreshBoundary.canInvoke
    ? [
        manualRefreshBoundary.draft.endDayUtc,
        manualRefreshBoundary.draft.codexJsonlRoot,
        manualRefreshBoundary.draft.claudeCodeJsonlRoot,
        manualRefreshBoundary.draft.geminiCliJsonlRoot
      ].join("|")
    : "";

  useEffect(() => {
    if (
      !shouldRunAutoRefresh({
        preferences: sourceRootPreferences,
        canInvoke: manualRefreshBoundary.canInvoke,
        isRunning: manualRefreshRunState.phase === "running",
        rootsAreSaved: rootsAreSavedForAutoRefresh
      }) ||
      !manualRefreshBoundary.canInvoke
    ) {
      return;
    }

    const draft = manualRefreshBoundary.draft;
    const timerId = window.setInterval(() => {
      void runRefreshWithDraft(draft);
    }, sourceRootPreferences.autoRefreshIntervalMinutes * 60 * 1000);

    return () => window.clearInterval(timerId);
  }, [
    manualRefreshKey,
    manualRefreshBoundary.canInvoke,
    manualRefreshRunState.phase,
    rootsAreSavedForAutoRefresh,
    sourceRootPreferences,
    sourceRootPreferences.autoRefreshIntervalMinutes
  ]);

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Primary navigation">
        <div className="brand">
          <span className="brand-wordmark">YourTokenHelper</span>
        </div>
        <nav className="nav-list">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                className={`nav-item ${item.id === activeView ? "active" : ""} ${item.secondary ? "secondary" : ""}`}
                key={item.id}
                onClick={() => setActiveView(item.id)}
                type="button"
              >
                <Icon size={16} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </aside>

      <main className="content">
        <header className="page-header">
          <div>
            <h1>{view.label}</h1>
            <p>{headerSubtitle(activeView, dashboardDataMode)}</p>
          </div>
          <div className="header-actions">
            <span className="quality-badge">{dashboardQualityLabel(dashboardDataMode, startupStorageReadState)}</span>
            <button
              aria-label={headerCanRefresh ? "Refresh local aggregate" : headerRefreshTitle}
              className="sync-button"
              disabled={!headerCanRefresh}
              onClick={handleHeaderRefresh}
              title={headerRefreshTitle}
              type="button"
            >
              <RefreshCw size={15} />
              {headerRefreshButtonLabel(headerRefreshState.isRunning)}
            </button>
          </div>
        </header>

        {renderView(
          activeView,
          dashboardPayload,
          dashboardDataMode,
          startupStorageReadState,
          lastRefreshResults,
          apiProviderCredentialFormState,
          apiProviderCredentialRunState,
          apiProviderCredentialStatuses,
          apiProviderEndpointDiagnostics,
          manualRefreshBoundary,
          manualRefreshRunState,
          manualAllowanceFormState,
          manualAllowanceSaveState,
          sourceRootPersistenceState,
          sourceRootPreferences,
          rootsAreSavedForAutoRefresh,
          clearExplicitRoot,
          forgetExplicitRoots,
          handleManualRefresh,
          removeApiProviderCredential,
          saveManualAllowance,
          saveApiProviderCredential,
          syncApiProviderBillingNow,
          saveExplicitRoots,
          setAutoRefreshEnabled,
          updateApiProviderCredentialDraft,
          updateManualAllowanceDraft,
          updateExplicitRoot
        )}
      </main>
    </div>
  );
}

function renderView(
  view: ViewId,
  payload: MockSummaryPayload,
  dataMode: DashboardDataMode,
  startupStorageReadState: StartupStorageReadState,
  lastRefreshResults: readonly RefreshResult[] | null,
  apiProviderCredentialFormState: ApiProviderCredentialFormState,
  apiProviderCredentialRunState: ApiProviderCredentialRunState,
  apiProviderCredentialStatuses: readonly ApiCostProviderStatus[],
  apiProviderEndpointDiagnostics: ApiProviderEndpointDiagnostics,
  manualRefreshBoundary: ReturnType<typeof buildManualRefreshDraftFromHiddenRoots>,
  manualRefreshRunState: ManualRefreshRunState,
  manualAllowanceFormState: ManualAllowanceFormState,
  manualAllowanceSaveState: ManualAllowanceSaveState,
  sourceRootPersistenceState: SourceRootPersistenceState,
  sourceRootPreferences: SourceRootPreferences,
  rootsAreSavedForAutoRefresh: boolean,
  onClearRoot: (sourceKind: ExplicitRootSourceKind) => void,
  onForgetRoots: () => void,
  onManualRefresh: () => void,
  onApiProviderCredentialRemove: () => void,
  onManualAllowanceSave: () => void,
  onApiProviderCredentialSave: () => void,
  onApiProviderBillingSync: () => void,
  onSaveRoots: () => void,
  onAutoRefreshChange: (enabled: boolean) => void,
  onApiProviderCredentialChange: (patch: Partial<ApiProviderCredentialFormState>) => void,
  onManualAllowanceChange: (patch: Partial<ManualAllowanceFormState>) => void,
  onRootChange: (sourceKind: ExplicitRootSourceKind, root: string) => void
) {
  const configuredSourceKinds = configuredUsageSourceKinds(sourceRootPreferences);

  if (view === "weekly") {
    return <WeeklyView configuredSourceKinds={configuredSourceKinds} dataMode={dataMode} payload={payload} />;
  }
  if (view === "sources") {
    return (
      <SourcesView
        dataMode={dataMode}
        lastRefreshResults={lastRefreshResults}
        manualAllowanceFormState={manualAllowanceFormState}
        manualAllowanceSaveState={manualAllowanceSaveState}
        manualRefreshBoundary={manualRefreshBoundary}
        manualRefreshRunState={manualRefreshRunState}
        onAutoRefreshChange={onAutoRefreshChange}
        onClearRoot={onClearRoot}
        onForgetRoots={onForgetRoots}
        onManualAllowanceChange={onManualAllowanceChange}
        onManualAllowanceSave={onManualAllowanceSave}
        onManualRefresh={onManualRefresh}
        onRootChange={onRootChange}
        onSaveRoots={onSaveRoots}
        payload={payload}
        rootsAreSavedForAutoRefresh={rootsAreSavedForAutoRefresh}
        sourceRootPersistenceState={sourceRootPersistenceState}
        sourceRootPreferences={sourceRootPreferences}
        startupStorageReadState={startupStorageReadState}
      />
    );
  }
  if (view === "api_costs") {
    return (
      <ApiCostsView
        credentialFormState={apiProviderCredentialFormState}
        credentialRunState={apiProviderCredentialRunState}
        credentialStatuses={apiProviderCredentialStatuses}
        dataMode={dataMode}
        endpointDiagnostics={apiProviderEndpointDiagnostics}
        onCredentialChange={onApiProviderCredentialChange}
        onCredentialRemove={onApiProviderCredentialRemove}
        onCredentialSave={onApiProviderCredentialSave}
        onProviderBillingSync={onApiProviderBillingSync}
        payload={payload}
      />
    );
  }
  if (view === "settings") {
    return <SettingsView payload={payload} />;
  }
  return <DailyView configuredSourceKinds={configuredSourceKinds} dataMode={dataMode} payload={payload} />;
}

function DailyView({
  configuredSourceKinds,
  dataMode,
  payload
}: {
  configuredSourceKinds: readonly SourceKind[];
  dataMode: DashboardDataMode;
  payload: MockSummaryPayload;
}) {
  const day = latestSummaryDay(payload) ?? manualRefreshEndDayUtc();
  const daily = payload.summary.by_day[day] ?? emptyTokenTotals();
  const dailySourceTotals = sourceTotalsForDay(payload, day);
  const remaining = firstKnownAllowance(payload, manualAllowanceSourceKinds);

  return (
    <>
      <PrimaryMetricStrip
        costSummary={payload.cost_summary}
        dataMode={dataMode}
        totals={daily}
        remaining={remaining}
        windowLabel="Today"
      />

      <section className="main-grid">
        <div className="left-stack">
          <Panel title="Source Usage">
            <SourceStack
              allowanceWindows={payload.allowance_windows}
              configuredSourceKinds={configuredSourceKinds}
              totals={dailySourceTotals}
            />
          </Panel>

          <Panel title="Token Split">
            <TokenSplit totals={daily} />
          </Panel>

          <Panel title="Top Drivers">
            <DriverTable payload={payload} totals={dailySourceTotals} />
          </Panel>
        </div>

        <aside className="right-stack">
          <Panel title="Sources">
            <SourceStatusList payload={payload} />
          </Panel>
        </aside>
      </section>
    </>
  );
}

function WeeklyView({
  configuredSourceKinds,
  dataMode,
  payload
}: {
  configuredSourceKinds: readonly SourceKind[];
  dataMode: DashboardDataMode;
  payload: MockSummaryPayload;
}) {
  const rolling = payload.summary.rolling_7d;
  const remaining = firstKnownAllowance(payload, manualAllowanceSourceKinds);
  const refreshRecency = refreshRecencyLabel(payload.refresh_state);

  return (
    <>
      <PrimaryMetricStrip
        costSummary={payload.cost_summary}
        dataMode={dataMode}
        totals={rolling.totals}
        remaining={remaining}
        windowLabel="Rolling 7 days"
      />

      <section className="main-grid">
        <div className="left-stack">
          <Panel title="Daily Trend">
            <DailyTrend payload={payload} />
          </Panel>

          <Panel title="Weekly Source Split">
            <SourceStack
              allowanceWindows={payload.allowance_windows}
              configuredSourceKinds={configuredSourceKinds}
              totals={payload.summary.by_source}
            />
          </Panel>
        </div>

        <aside className="right-stack">
          <Panel title="Rolling Window">
            <div className="fact-list">
              <Fact label="Start" value={rolling.window_start ?? "Unavailable"} />
              <Fact label="End" value={rolling.window_end ?? "Unavailable"} />
              <Fact label="Days" value={String(Object.keys(payload.summary.by_day).length)} />
              <Fact label="Refresh" value={refreshRecency.label} />
            </div>
          </Panel>

          <Panel title="Token Split">
            <TokenSplit totals={rolling.totals} />
          </Panel>
        </aside>
      </section>
    </>
  );
}

function SourcesView({
  dataMode,
  lastRefreshResults,
  manualAllowanceFormState,
  manualAllowanceSaveState,
  manualRefreshBoundary,
  manualRefreshRunState,
  onAutoRefreshChange,
  onClearRoot,
  onForgetRoots,
  onManualAllowanceChange,
  onManualAllowanceSave,
  onManualRefresh,
  onRootChange,
  onSaveRoots,
  payload,
  rootsAreSavedForAutoRefresh,
  sourceRootPersistenceState,
  sourceRootPreferences,
  startupStorageReadState
}: {
  dataMode: DashboardDataMode;
  lastRefreshResults: readonly RefreshResult[] | null;
  manualAllowanceFormState: ManualAllowanceFormState;
  manualAllowanceSaveState: ManualAllowanceSaveState;
  manualRefreshBoundary: ReturnType<typeof buildManualRefreshDraftFromHiddenRoots>;
  manualRefreshRunState: ManualRefreshRunState;
  onAutoRefreshChange: (enabled: boolean) => void;
  onClearRoot: (sourceKind: ExplicitRootSourceKind) => void;
  onForgetRoots: () => void;
  onManualAllowanceChange: (patch: Partial<ManualAllowanceFormState>) => void;
  onManualAllowanceSave: () => void;
  onManualRefresh: () => void;
  onRootChange: (sourceKind: ExplicitRootSourceKind, root: string) => void;
  onSaveRoots: () => void;
  payload: MockSummaryPayload;
  rootsAreSavedForAutoRefresh: boolean;
  sourceRootPersistenceState: SourceRootPersistenceState;
  sourceRootPreferences: SourceRootPreferences;
  startupStorageReadState: StartupStorageReadState;
}) {
  return (
    <section className="single-column">
      <Panel title="Connector Status">
        <table className="data-table">
          <thead>
            <tr>
              <th>Source</th>
              <th>Status</th>
              <th>Confidence</th>
              <th>Allowance</th>
            </tr>
          </thead>
          <tbody>
            {payload.source_states.map((source) => {
              const allowance = payload.allowance_windows.find((item) => item.source_kind === source.source_kind);
              return (
                <tr key={source.source_kind}>
                  <td>
                    <span className="source-name">
                      <span className="source-dot" style={{ background: sourceColors[source.source_kind] }} />
                      {sourceLabels[source.source_kind]}
                    </span>
                  </td>
                  <td><StatusBadge label={source.status.replace("_", " ")} /></td>
                  <td>{source.confidence.replace("_", " ")}</td>
                  <td>{allowanceStatusLabel(allowance)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Panel>

      <Panel title="Explicit Roots">
        <ExplicitRootsMock
          canSaveRoots={manualRefreshBoundary.canInvoke}
          onClearRoot={onClearRoot}
          onForgetRoots={onForgetRoots}
          onRootChange={onRootChange}
          onSaveRoots={onSaveRoots}
          rootDraft={sourceRootPreferences.rootDraft}
          rows={manualRefreshBoundary.rows}
          sourceRootPersistenceState={sourceRootPersistenceState}
          sourceRootPreferences={sourceRootPreferences}
        />
      </Panel>

      <Panel title="Manual Allowance">
        <ManualAllowanceForm
          formState={manualAllowanceFormState}
          onChange={onManualAllowanceChange}
          onSave={onManualAllowanceSave}
          saveState={manualAllowanceSaveState}
        />
      </Panel>

      <Panel title="Manual Refresh">
        <ManualRefreshMock
          autoRefreshEnabled={sourceRootPreferences.autoRefreshEnabled}
          autoRefreshIntervalMinutes={sourceRootPreferences.autoRefreshIntervalMinutes}
          canInvoke={manualRefreshBoundary.canInvoke}
          onAutoRefreshChange={onAutoRefreshChange}
          onRefresh={onManualRefresh}
          readiness={manualRefreshBoundary.readiness}
          rootsAreSavedForAutoRefresh={rootsAreSavedForAutoRefresh}
          runState={manualRefreshRunState}
        />
      </Panel>

      <Panel title="Saved Aggregate">
        <StartupStorageStatus
          dataMode={dataMode}
          refreshState={payload.refresh_state}
          state={startupStorageReadState}
        />
      </Panel>

      <Panel title="Last Refresh">
        <LastRefreshResults results={lastRefreshResults} />
      </Panel>
    </section>
  );
}

function StartupStorageStatus({
  dataMode,
  refreshState,
  state
}: {
  dataMode: DashboardDataMode;
  refreshState: RefreshState;
  state: StartupStorageReadState;
}) {
  const refreshRecency = refreshRecencyLabel(refreshState);

  return (
    <div className="manual-refresh-mock" aria-label="Saved aggregate readback state">
      <div className="manual-refresh-row">
        <span>Readback</span>
        <StatusBadge label={startupStorageStatusLabel(state)} />
      </div>
      <div className="manual-refresh-row">
        <span>Dashboard</span>
        <strong>{startupDashboardModeLabel(dataMode)}</strong>
      </div>
      <div className="manual-refresh-row">
        <span>Mode</span>
        <strong>Manual or auto</strong>
      </div>
      <div className="manual-refresh-row">
        <span>Refresh</span>
        <StatusBadge label={refreshRecency.label} />
      </div>
      <div className="manual-refresh-row">
        <span>Freshness</span>
        <strong>{refreshRecency.detail}</strong>
      </div>
      {state.phase === "unavailable" ? (
        <div className="manual-refresh-row">
          <span>Detail</span>
          <strong>{state.message}</strong>
        </div>
      ) : null}
    </div>
  );
}

function ManualAllowanceForm({
  formState,
  onChange,
  onSave,
  saveState
}: {
  formState: ManualAllowanceFormState;
  onChange: (patch: Partial<ManualAllowanceFormState>) => void;
  onSave: () => void;
  saveState: ManualAllowanceSaveState;
}) {
  const isSaving = saveState.phase === "saving";
  const stateLabel = saveState.phase === "idle" ? "Not configured" : saveState.phase;

  return (
    <form
      className="manual-allowance-form"
      onSubmit={(event) => {
        event.preventDefault();
        onSave();
      }}
    >
      <div className="allowance-input-grid">
        <label className="form-field">
          <span>Source</span>
          <select
            className="root-input"
            onChange={(event) => onChange({ sourceKind: event.currentTarget.value as SourceKind })}
            value={formState.sourceKind}
          >
            {manualAllowanceSourceKinds.map((sourceKind) => (
              <option key={sourceKind} value={sourceKind}>
                {sourceLabels[sourceKind]}
              </option>
            ))}
          </select>
        </label>
        <label className="form-field">
          <span>Unit</span>
          <select
            className="root-input"
            onChange={(event) => onChange({ unit: event.currentTarget.value as AllowanceWindow["unit"] })}
            value={formState.unit}
          >
            {manualAllowanceUnits.map((unit) => (
              <option key={unit} value={unit}>
                {allowanceUnitLabel(unit)}
              </option>
            ))}
          </select>
        </label>
        <label className="form-field">
          <span>Limit</span>
          <input
            className="root-input"
            inputMode="decimal"
            min="0"
            onChange={(event) => onChange({ limitAmount: event.currentTarget.value })}
            placeholder="100000"
            type="number"
            value={formState.limitAmount}
          />
        </label>
        <label className="form-field">
          <span>Remaining</span>
          <input
            className="root-input"
            inputMode="decimal"
            min="0"
            onChange={(event) => onChange({ remainingAmount: event.currentTarget.value })}
            placeholder="97460"
            type="number"
            value={formState.remainingAmount}
          />
        </label>
        <label className="form-field reset-field">
          <span>Reset</span>
          <input
            autoComplete="off"
            className="root-input"
            onChange={(event) => onChange({ resetAt: event.currentTarget.value })}
            placeholder="2026-06-21T00:00:00Z"
            spellCheck={false}
            type="text"
            value={formState.resetAt}
          />
        </label>
      </div>
      <div className="allowance-actions">
        <div className="manual-refresh-row">
          <span>State</span>
          <StatusBadge label={stateLabel} />
        </div>
        {saveState.phase === "succeeded" || saveState.phase === "failed" ? (
          <div className="manual-refresh-row">
            <span>Result</span>
            <strong>{saveState.message}</strong>
          </div>
        ) : null}
        <button className="sync-button" disabled={isSaving} type="submit">
          <Save size={15} />
          {isSaving ? "Saving" : "Save allowance"}
        </button>
      </div>
    </form>
  );
}

function ManualRefreshMock({
  autoRefreshEnabled,
  autoRefreshIntervalMinutes,
  canInvoke,
  onAutoRefreshChange,
  onRefresh,
  rootsAreSavedForAutoRefresh,
  runState,
  readiness
}: {
  autoRefreshEnabled: boolean;
  autoRefreshIntervalMinutes: number;
  canInvoke: boolean;
  onAutoRefreshChange: (enabled: boolean) => void;
  onRefresh: () => void;
  rootsAreSavedForAutoRefresh: boolean;
  runState: ManualRefreshRunState;
  readiness: ManualRefreshReadiness;
}) {
  const bridgeLabel = manualRefreshBridgeLabel(readiness);
  const isRunning = runState.phase === "running";
  const needsLabel = manualRefreshNeedsLabel(readiness);
  const stateLabel = manualRefreshStatusLabel(canInvoke, runState);
  const rootsLabel = manualRefreshRootsLabel(readiness);
  const autoStatusLabel = autoRefreshStatusLabel(
    {
      rootDraft: {},
      hasSavedRoots: rootsAreSavedForAutoRefresh,
      autoRefreshEnabled,
      autoRefreshIntervalMinutes
    },
    rootsAreSavedForAutoRefresh
  );

  return (
    <div className="manual-refresh-panel" aria-label="Manual refresh state">
      <div className="manual-refresh-hero">
        <div className={`refresh-state-mark ${runState.phase}`} />
        <div className="manual-refresh-copy">
          <span>State</span>
          <strong>{stateLabel}</strong>
          <small>{rootsLabel}</small>
        </div>
      </div>
      <div className="manual-refresh-actions">
        <label className="toggle-control">
          <input
            checked={autoRefreshEnabled}
            disabled={!canInvoke || !rootsAreSavedForAutoRefresh}
            onChange={(event) => onAutoRefreshChange(event.currentTarget.checked)}
            type="checkbox"
          />
          Auto
        </label>
        <button
          aria-label={canInvoke ? "Run manual refresh" : manualRefreshMockState.disabledAriaLabel}
          className="sync-button"
          disabled={!canInvoke || isRunning}
          onClick={onRefresh}
          title={canInvoke ? "Run production manual refresh" : manualRefreshMockState.disabledTitle}
          type="button"
        >
          <RefreshCw size={15} />
          {isRunning ? "Refreshing" : "Refresh"}
        </button>
      </div>
      {runState.phase === "succeeded" || runState.phase === "failed" ? (
        <div className={`manual-refresh-result ${runState.phase}`}>
          <span>Last run</span>
          <strong>{runState.message}</strong>
        </div>
      ) : null}
      <div className="manual-refresh-summary">
        <RefreshSummaryItem label="Ready check" value={needsLabel} detail={bridgeLabel} />
        <RefreshSummaryItem label="Auto refresh" value={autoStatusLabel} detail={`${autoRefreshIntervalMinutes} min`} />
        <RefreshSummaryItem label="Command" value={<code>{manualRefreshMockState.commandName}</code>} />
      </div>
    </div>
  );
}

function RefreshSummaryItem({
  detail,
  label,
  value
}: {
  detail?: string;
  label: string;
  value: ReactNode;
}) {
  return (
    <div className="refresh-summary-item">
      <span>{label}</span>
      <strong>{value}</strong>
      {detail ? <small>{detail}</small> : null}
    </div>
  );
}

function LastRefreshResults({ results }: { results: readonly RefreshResult[] | null }) {
  if (!results) {
    return (
      <div className="fact-list">
        <Fact label="Status" value="Not run this session" />
      </div>
    );
  }

  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>Source</th>
          <th>Status</th>
          <th>Confidence</th>
          <th>Events</th>
          <th>Sync run</th>
        </tr>
      </thead>
      <tbody>
        {results.map((result) => (
          <tr key={result.source_id}>
            <td>{sourceLabels[result.source_kind]}</td>
            <td><StatusBadge label={result.status.replace("_", " ")} /></td>
            <td>{result.confidence.replace("_", " ")}</td>
            <td className="numeric">{formatInteger(result.events_seen)}</td>
            <td className="numeric">{formatInteger(result.sync_run_id)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ExplicitRootsMock({
  canSaveRoots,
  onClearRoot,
  onForgetRoots,
  onRootChange,
  onSaveRoots,
  rootDraft,
  rows,
  sourceRootPersistenceState,
  sourceRootPreferences
}: {
  canSaveRoots: boolean;
  onClearRoot: (sourceKind: ExplicitRootSourceKind) => void;
  onForgetRoots: () => void;
  onRootChange: (sourceKind: ExplicitRootSourceKind, root: string) => void;
  onSaveRoots: () => void;
  rootDraft: ExplicitRootSelectionDraft;
  rows: readonly ExplicitRootMockRow[];
  sourceRootPersistenceState: SourceRootPersistenceState;
  sourceRootPreferences: SourceRootPreferences;
}) {
  return (
    <>
      <div className="setup-source-list">
        {rows.map((row) => (
          <div className="setup-source-row" key={row.sourceKind}>
            <span className="source-dot" style={{ background: sourceColors[row.sourceKind] }} />
            <div className="setup-source-meta">
              <strong>{sourceLabels[row.sourceKind]}</strong>
              <span>{row.detail}</span>
              <span>{row.nextStep}</span>
            </div>
            <span className="setup-source-value">{row.displayValue}</span>
            <StatusBadge label={pathPolicyLabels[row.pathPolicy]} />
            {isExplicitRootRow(row) ? (
              <div className="root-entry">
                <input
                  aria-label={`${sourceLabels[row.sourceKind]} root path, hidden`}
                  autoComplete="off"
                  className="root-input"
                  onChange={(event) => onRootChange(row.sourceKind, event.currentTarget.value)}
                  placeholder="Hidden root"
                  spellCheck={false}
                  type="password"
                  value={rootDraftValue(row.sourceKind, rootDraft)}
                />
                <button
                  aria-label={`Clear ${sourceLabels[row.sourceKind]} hidden root`}
                  className="icon-button"
                  disabled={!rootDraftValue(row.sourceKind, rootDraft)}
                  onClick={() => onClearRoot(row.sourceKind)}
                  title="Clear hidden root"
                  type="button"
                >
                  <X size={15} />
                </button>
              </div>
            ) : (
              <span className="setup-spacer" />
            )}
          </div>
        ))}
      </div>
      <div className="root-save-row">
        <div className="manual-refresh-row">
          <span>Storage</span>
          <StatusBadge label={sourceRootStorageLabel(sourceRootPreferences, sourceRootPersistenceState)} />
        </div>
        <button
          className="sync-button"
          disabled={!canSaveRoots || sourceRootPersistenceState.phase === "saving"}
          onClick={onSaveRoots}
          type="button"
        >
          Save roots
        </button>
        <button
          className="sync-button"
          disabled={!sourceRootPreferences.hasSavedRoots && sourceRootPersistenceState.phase !== "dirty"}
          onClick={onForgetRoots}
          type="button"
        >
          Forget
        </button>
      </div>
      {sourceRootPersistenceState.phase === "failed" ? (
        <div className="manual-refresh-row">
          <span>Save</span>
          <strong>{sourceRootPersistenceState.message}</strong>
        </div>
      ) : null}
    </>
  );
}

function isExplicitRootRow(row: ExplicitRootMockRow): row is ExplicitRootMockRow & { sourceKind: ExplicitRootSourceKind } {
  return Boolean(row.picker);
}

function rootDraftValue(sourceKind: ExplicitRootSourceKind, draft: ExplicitRootSelectionDraft) {
  if (sourceKind === "codex") {
    return draft.codexJsonlRoot ?? "";
  }
  if (sourceKind === "claude_code") {
    return draft.claudeCodeJsonlRoot ?? "";
  }
  if (sourceKind === "gemini_cli") {
    return draft.geminiCliJsonlRoot ?? "";
  }
  return "";
}

function ApiCostsView({
  credentialFormState,
  credentialRunState,
  credentialStatuses,
  dataMode,
  endpointDiagnostics,
  onCredentialChange,
  onCredentialRemove,
  onCredentialSave,
  onProviderBillingSync,
  payload
}: {
  credentialFormState: ApiProviderCredentialFormState;
  credentialRunState: ApiProviderCredentialRunState;
  credentialStatuses: readonly ApiCostProviderStatus[];
  dataMode: DashboardDataMode;
  endpointDiagnostics: ApiProviderEndpointDiagnostics;
  onCredentialChange: (patch: Partial<ApiProviderCredentialFormState>) => void;
  onCredentialRemove: () => void;
  onCredentialSave: () => void;
  onProviderBillingSync: () => void;
  payload: MockSummaryPayload;
}) {
  const costTotals = payload.summary.by_source.openai_api_cost;
  const costSummary = payload.cost_summary;
  const credentialStatusByProvider = apiProviderCredentialStatusByProvider(credentialStatuses);
  const providersWithCost = apiCostProviders.filter((provider) =>
    hasCostSourceTotals(costSummary.by_source[provider.sourceKind])
  );
  const costEstimateValue = formatUsd(costSummary.total_usd);
  const costEstimateUnit = costSummary.total_usd === null
    ? "no stored cost records"
    : dataMode === "mock"
      ? "mock stored aggregate"
      : "stored aggregate";
  const costWindowLabel = costSummary.window_start && costSummary.window_end
    ? `${costSummary.window_start} to ${costSummary.window_end}`
    : "No stored window";
  const openAiCostStatus = providerCostStatus("openai_api_cost", costSummary.by_source.openai_api_cost);

  return (
    <section className="single-column">
      <div className="metric-strip compact" aria-label="API cost metrics">
        <MetricTile label="Cost estimate" value={costEstimateValue} unit={costEstimateUnit} tone="secondary" />
        <MetricTile label="Providers" value={String(apiCostProviders.length)} unit="secondary sources" />
        <MetricTile label="Stored" value={String(providersWithCost.length)} unit="providers with cost records" />
        <MetricTile label="Cost source" value={openAiCostStatus} unit={costWindowLabel} />
      </div>

      <Panel title="Provider Status">
        <table className="data-table">
          <thead>
            <tr>
              <th>Provider</th>
              <th>Status</th>
              <th>Credential</th>
              <th>Usage API</th>
              <th>Costs API</th>
              <th>Stored cost</th>
              <th>Next step</th>
            </tr>
          </thead>
          <tbody>
            {apiCostProviders.map((provider) => {
              const providerCost = costSummary.by_source[provider.sourceKind];
              const credentialStatus = credentialStatusByProvider.get(provider.sourceKind)
                ?? apiCostProviderStatusFor(provider.sourceKind);
              const diagnostics = endpointDiagnostics[provider.sourceKind];
              return (
                <tr key={provider.sourceKind}>
                  <td>{sourceLabels[provider.sourceKind]}</td>
                  <td><StatusBadge label={providerCostStatus(provider.sourceKind, providerCost, credentialStatus)} /></td>
                  <td>{credentialStatus.credentialConfigured ? "Configured" : "Not configured"}</td>
                  <td><StatusBadge label={apiProviderEndpointStatusLabel(diagnostics?.usage)} /></td>
                  <td><StatusBadge label={apiProviderEndpointStatusLabel(diagnostics?.costs)} /></td>
                  <td>{providerCost ? formatUsd(providerCost.total_usd) : "No stored data"}</td>
                  <td>{providerCostNextStep(provider, providerCost, credentialStatus)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Panel>

      <Panel title="Provider Credentials">
        <ApiProviderCredentialForm
          formState={credentialFormState}
          onChange={onCredentialChange}
          onRemove={onCredentialRemove}
          onSave={onCredentialSave}
          onSync={onProviderBillingSync}
          runState={credentialRunState}
          statuses={credentialStatuses}
        />
      </Panel>

      <Panel title="Stored Cost Breakdown">
        <table className="data-table">
          <thead>
            <tr>
              <th>Provider</th>
              <th>Cost</th>
              <th>Buckets</th>
              <th>Events</th>
            </tr>
          </thead>
          <tbody>
            {providersWithCost.length ? providersWithCost.map((provider) => {
              const providerCost = costSummary.by_source[provider.sourceKind];
              return providerCost ? (
                <tr key={provider.sourceKind}>
                  <td>{sourceLabels[provider.sourceKind]}</td>
                  <td>{formatUsd(providerCost.total_usd)}</td>
                  <td>{formatInteger(providerCost.bucket_count)}</td>
                  <td>{formatInteger(providerCost.event_count)}</td>
                </tr>
              ) : null;
            }) : (
              <tr>
                <td colSpan={4}>No stored cost data. OpenAI org costs require an Admin API key, not a personal API key.</td>
              </tr>
            )}
          </tbody>
        </table>
      </Panel>

      <Panel title="OpenAI Admin Usage">
        <table className="data-table">
          <thead>
            <tr>
              <th>Input</th>
              <th>Cached</th>
              <th>Output</th>
              <th>Reasoning</th>
              <th>Total</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{formatTokens(costTotals.input_tokens)}</td>
              <td>{formatTokens(costTotals.cached_input_tokens)}</td>
              <td>{formatTokens(costTotals.output_tokens)}</td>
              <td>{formatTokens(costTotals.reasoning_output_tokens)}</td>
              <td>{formatTokens(costTotals.total_tokens)}</td>
            </tr>
          </tbody>
        </table>
      </Panel>
    </section>
  );
}

function ApiProviderCredentialForm({
  formState,
  onChange,
  onRemove,
  onSave,
  onSync,
  runState,
  statuses
}: {
  formState: ApiProviderCredentialFormState;
  onChange: (patch: Partial<ApiProviderCredentialFormState>) => void;
  onRemove: () => void;
  onSave: () => void;
  onSync: () => void;
  runState: ApiProviderCredentialRunState;
  statuses: readonly ApiCostProviderStatus[];
}) {
  const selectedStatus = apiProviderCredentialStatusByProvider(statuses).get(formState.providerId)
    ?? apiCostProviderStatusFor(formState.providerId);
  const isSaving = runState.phase === "saving";
  const isRemoving = runState.phase === "removing";
  const isSyncing = runState.phase === "syncing";
  const canSync = formState.providerId === "openai_api_cost"
    && selectedStatus.credentialConfigured
    && !isSaving
    && !isRemoving
    && !isSyncing;
  const stateLabel = apiProviderCredentialRunStateLabel(runState);

  return (
    <form
      className="manual-allowance-form"
      onSubmit={(event) => {
        event.preventDefault();
        onSave();
      }}
    >
      <div className="allowance-input-grid api-credential-grid">
        <label className="form-field">
          <span>Provider</span>
          <select
            className="root-input"
            onChange={(event) => onChange({ providerId: event.currentTarget.value as ApiCostSourceKind })}
            value={formState.providerId}
          >
            {apiCostProviderIds.map((providerId) => (
              <option key={providerId} value={providerId}>
                {sourceLabels[providerId]}
              </option>
            ))}
          </select>
        </label>
        <label className="form-field api-key-field">
          <span>Key</span>
          <input
            autoComplete="off"
            className="root-input"
            onChange={(event) => onChange({ apiKey: event.currentTarget.value })}
            placeholder="Paste key"
            spellCheck={false}
            type="password"
            value={formState.apiKey}
          />
        </label>
      </div>
      <div className="allowance-actions">
        <div className="manual-refresh-row">
          <span>State</span>
          <StatusBadge label={stateLabel} />
        </div>
        <div className="manual-refresh-row">
          <span>Credential</span>
          <strong>{selectedStatus.credentialConfigured ? "Configured" : "Not configured"}</strong>
        </div>
        <div className="manual-refresh-row">
          <span>Adapter</span>
          <strong>{apiCostProviderStatusLabel(selectedStatus.status)}</strong>
        </div>
        {runState.phase === "saved" || runState.phase === "synced" || runState.phase === "removed" || runState.phase === "failed" ? (
          <div className="manual-refresh-row">
            <span>Result</span>
            <strong>{runState.message}</strong>
          </div>
        ) : null}
        <button className="sync-button" disabled={isSaving || isSyncing || !formState.apiKey.trim()} type="submit">
          <Save size={15} />
          {isSaving ? "Saving" : "Save key"}
        </button>
        <button
          className="sync-button"
          disabled={!canSync}
          onClick={onSync}
          type="button"
        >
          <RefreshCw size={15} />
          {isSyncing ? "Syncing" : "Sync billing"}
        </button>
        <button
          className="sync-button secondary-action"
          disabled={isRemoving || isSyncing || !selectedStatus.credentialConfigured}
          onClick={onRemove}
          type="button"
        >
          <X size={15} />
          {isRemoving ? "Removing" : "Remove"}
        </button>
      </div>
    </form>
  );
}

function SettingsView({ payload }: { payload: MockSummaryPayload }) {
  return (
    <section className="single-column">
      <div className="two-column">
        <Panel title="Timezone">
          <div className="setting-row">
            <Clock3 size={17} />
            <span>Asia/Shanghai</span>
            <StatusBadge label="manual" />
          </div>
        </Panel>

        <Panel title="Privacy">
          <div className="setting-row">
            <CheckCircle2 size={17} />
            <span>Aggregates only</span>
            <StatusBadge label="enabled" />
          </div>
        </Panel>
      </div>

      <Panel title="Data Policy">
        <div className="fact-list">
          <Fact label="Prompt content" value={yesNo(payload.privacy.stores_prompt_content)} />
          <Fact label="Response content" value={yesNo(payload.privacy.stores_response_content)} />
          <Fact label="Tool output" value={yesNo(payload.privacy.stores_tool_output)} />
        </div>
      </Panel>
    </section>
  );
}

function PrimaryMetricStrip({
  costSummary,
  dataMode,
  totals,
  remaining,
  windowLabel
}: {
  costSummary: MockSummaryPayload["cost_summary"];
  dataMode: DashboardDataMode;
  totals: TokenTotals;
  remaining: AllowanceWindow | undefined;
  windowLabel: string;
}) {
  const costEstimateValue = formatUsd(costSummary.total_usd);
  const costEstimateUnit = costSummary.total_usd === null
    ? "no stored cost records"
    : dataMode === "mock"
      ? "mock stored aggregate"
      : "stored aggregate";

  return (
    <section className="metric-strip" aria-label={`${windowLabel} metrics`}>
      <MetricTile label="Usage consumed" value={formatMetricTokens(totals.total_tokens)} unit="tokens" tone="primary" />
      <MetricTile
        label="Remaining"
        value={remaining ? formatAllowance(remaining) : "Not configured"}
        unit={remaining ? `${remaining.status.replace("_", " ")} estimate` : "manual optional"}
        tone={remaining ? undefined : "muted"}
      />
      <MetricTile
        label="Reset"
        value={remaining?.reset_at ? formatDate(remaining.reset_at) : "Not configured"}
        unit="next known reset"
        tone={remaining?.reset_at ? undefined : "muted"}
      />
      <MetricTile
        label="Cost estimate"
        value={costEstimateValue}
        unit={costEstimateUnit}
        tone={costSummary.total_usd === null || costSummary.total_usd === undefined ? "muted" : "secondary"}
      />
      <MetricTile label="Window" value={windowLabel} unit={dataMode === "mock" ? "mock contract" : "local aggregate"} />
      <MetricTile label="Cached share" value={cachedShare(totals)} unit="input tokens" />
    </section>
  );
}

type MetricTileTone = "primary" | "secondary" | "muted";

function MetricTile({ label, value, unit, tone }: { label: string; value: string; unit: string; tone?: MetricTileTone }) {
  const valueClassName = isCompactMetricValue(value, tone) ? "compact-value" : "";

  return (
    <div className={["metric-tile", tone].filter(Boolean).join(" ")}>
      <span className="metric-label">{label}</span>
      <strong className={valueClassName}>{value}</strong>
      <span className="metric-unit">{unit}</span>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="panel">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

function SourceStack({
  allowanceWindows,
  configuredSourceKinds,
  totals
}: {
  allowanceWindows: readonly AllowanceWindow[];
  configuredSourceKinds: readonly SourceKind[];
  totals: Record<SourceKind, TokenTotals>;
}) {
  const rows = sourceUsageRows(totals, configuredSourceKinds, allowanceWindows);

  return (
    <div className="source-stack">
      {rows.map(({ sourceKind, totals: total, progress }) => {
        const barWidth = progress.percent > 0 ? Math.min(100, Math.max(4, progress.percent)) : 0;
        return (
          <div className="stack-row" key={sourceKind}>
            <div className="stack-label">
              <span>{sourceLabels[sourceKind]}</span>
              <span>{formatTokens(total.total_tokens)}</span>
            </div>
            <div className="stack-meta">
              <span>{sourceUsageProgressLabel(progress)}</span>
              <span>{sourceUsageProgressDetail(progress)}</span>
            </div>
            <div className="bar-track">
              <span className="bar-fill" style={{ width: `${barWidth}%`, background: sourceColors[sourceKind] }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function sourceUsageProgressLabel(progress: SourceUsageProgress) {
  if (progress.kind === "usage_share") {
    return `${formatPercent(progress.percent)} of visible usage`;
  }
  return `${formatPercent(progress.percent)} limit used`;
}

function sourceUsageProgressDetail(progress: SourceUsageProgress) {
  if (progress.kind === "usage_share") {
    return "visible usage split";
  }
  return `${formatCompactNumber(progress.usedAmount)} / ${formatCompactNumber(progress.limitAmount)} ${allowanceUnitLabel(progress.unit)} ${progress.status.replace("_", " ")}`;
}

function TokenSplit({ totals }: { totals: TokenTotals }) {
  const rows = [
    ["Input", totals.input_tokens],
    ["Output", totals.output_tokens],
    ["Cached", totals.cached_input_tokens],
    ["Reasoning", totals.reasoning_output_tokens]
  ] as const;
  const max = Math.max(...rows.map(([, value]) => value), 1);

  return (
    <div className="token-split">
      {rows.map(([label, value]) => (
        <div className="split-row" key={label}>
          <span>{label}</span>
          <div className="bar-track">
            <span className="bar-fill teal" style={{ width: `${barPercent(value, max, 3)}%` }} />
          </div>
          <strong>{formatTokens(value)}</strong>
        </div>
      ))}
    </div>
  );
}

function DailyTrend({ payload }: { payload: MockSummaryPayload }) {
  const rows = Object.entries(payload.summary.by_day);
  const max = Math.max(...rows.map(([, totals]) => totals.total_tokens), 1);

  return (
    <div className="trend-bars">
      {rows.map(([day, totals]) => (
        <div className="trend-row" key={day}>
          <span>{day.slice(5)}</span>
          <div className="bar-track">
            <span className="bar-fill teal" style={{ width: `${barPercent(totals.total_tokens, max, 3)}%` }} />
          </div>
          <strong>{formatTokens(totals.total_tokens)}</strong>
        </div>
      ))}
    </div>
  );
}

function DriverTable({ payload, totals }: { payload: MockSummaryPayload; totals: Record<SourceKind, TokenTotals> }) {
  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>Driver</th>
          <th>Source</th>
          <th>Tokens</th>
          <th>Confidence</th>
        </tr>
      </thead>
      <tbody>
        {sourceRows(totals, payload).map((row) => (
          <tr key={row.source}>
            <td>{row.driver}</td>
            <td>{sourceLabels[row.source]}</td>
            <td className="numeric">{formatTokens(row.tokens)}</td>
            <td><StatusBadge label={row.confidence} /></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function SourceStatusList({ payload }: { payload: MockSummaryPayload }) {
  return (
    <div className="source-list">
      {payload.source_states.map((source) => (
        <div className="source-row" key={source.source_kind}>
          <span className="source-dot" style={{ background: sourceColors[source.source_kind] }} />
          <span>{sourceLabels[source.source_kind]}</span>
          <StatusBadge label={source.status.replace("_", " ")} />
        </div>
      ))}
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="fact-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function StatusBadge({ label }: { label: string }) {
  return <span className="status-badge">{label}</span>;
}

function sourceRows(totals: Record<SourceKind, TokenTotals>, payload: MockSummaryPayload) {
  return Object.entries(totals)
    .filter(([, totals]) => totals.total_tokens > 0)
    .map(([source, totals]) => ({
      source: source as SourceKind,
      driver: sourceLabels[source as SourceKind],
      tokens: totals.total_tokens,
      confidence: payload.source_states.find((item) => item.source_kind === source)?.confidence ?? "unknown"
    }))
    .sort((left, right) => right.tokens - left.tokens)
    .slice(0, 5);
}

function isCompactMetricValue(value: string, tone?: MetricTileTone) {
  return tone !== "primary" && value.length >= 10;
}

function barPercent(value: number, max: number, minimumVisiblePercent: number) {
  if (value <= 0 || max <= 0) {
    return 0;
  }
  return Math.max(minimumVisiblePercent, Math.round((value / max) * 100));
}

function firstKnownAllowance(payload: MockSummaryPayload, sourceKinds: readonly SourceKind[]) {
  return payload.allowance_windows.find(
    (window) => sourceKinds.includes(window.source_kind) && window.remaining_amount !== undefined
  );
}

function allowanceStatusLabel(window: AllowanceWindow | undefined) {
  return window ? window.status.replace("_", " ") : "Not configured";
}

function hasCostSourceTotals(totals: MockSummaryPayload["cost_summary"]["by_source"][ApiCostSourceKind]) {
  return totals !== undefined && totals.bucket_count > 0;
}

function apiProviderCredentialStatusByProvider(statuses: readonly ApiCostProviderStatus[]) {
  return new Map(statuses.map((status) => [status.providerId, status]));
}

function replaceApiProviderCredentialStatus(
  statuses: readonly ApiCostProviderStatus[],
  replacement: ApiCostProviderStatus
) {
  const statusByProvider = apiProviderCredentialStatusByProvider(statuses);
  statusByProvider.set(replacement.providerId, replacement);
  return apiCostProviderIds.map((providerId) =>
    statusByProvider.get(providerId) ?? apiCostProviderStatusFor(providerId)
  );
}

function providerCostStatus(
  sourceKind: ApiCostSourceKind,
  totals: MockSummaryPayload["cost_summary"]["by_source"][ApiCostSourceKind] | undefined,
  credentialStatus: ApiCostProviderStatus = apiCostProviderStatusFor(sourceKind)
) {
  if (hasCostSourceTotals(totals)) {
    return "Stored";
  }
  return apiCostProviderStatusLabel(credentialStatus.status);
}

function apiProviderEndpointStatusLabel(
  status: ApiProviderEndpointStatusesPayload["usage"] | undefined
) {
  if (status === undefined) {
    return "Not checked";
  }
  const labels: Record<ApiProviderEndpointStatusesPayload["usage"], string> = {
    ready: "Ready",
    invalid_key: "Invalid key",
    permission_denied: "Permission denied",
    rate_limited: "Rate limited",
    unavailable: "Unavailable"
  };
  return labels[status];
}

function providerCostNextStep(
  provider: ApiCostProvider,
  totals: MockSummaryPayload["cost_summary"]["by_source"][ApiCostSourceKind] | undefined,
  credentialStatus: ApiCostProviderStatus = apiCostProviderStatusFor(provider.sourceKind)
) {
  if (hasCostSourceTotals(totals)) {
    return "Loaded from local aggregate storage";
  }
  if (credentialStatus.status === "not_configured") {
    return "Save a provider credential or import sanitized Admin payloads";
  }
  if (credentialStatus.status === "unavailable" && credentialStatus.credentialConfigured) {
    return "Credential stored with OS protection; sync billing to validate access";
  }
  if (credentialStatus.status === "invalid_key") {
    return "Stored key was read but OpenAI rejected it";
  }
  if (credentialStatus.status === "permission_denied") {
    return "Stored key was read but lacks OpenAI Admin billing access";
  }
  if (credentialStatus.status === "rate_limited") {
    return "Stored key was read; OpenAI rate limited the billing request";
  }
  if (credentialStatus.message) {
    return credentialStatus.message;
  }
  return provider.detail;
}

function apiProviderBillingSyncMessage(
  eventsSeen: number,
  providerStatus: ApiCostProviderStatus | undefined
) {
  if (providerStatus?.status === "invalid_key") {
    return "Stored key was read but OpenAI rejected it";
  }
  if (providerStatus?.status === "permission_denied") {
    return "Stored key was read but lacks OpenAI Admin billing access";
  }
  if (providerStatus?.status === "rate_limited") {
    return "Stored key was read; OpenAI rate limited the billing request";
  }
  if (providerStatus && providerStatus.status !== "ready") {
    return apiCostProviderStatusLabel(providerStatus.status);
  }
  return `Synced ${formatInteger(eventsSeen)} billing records`;
}

function apiProviderCredentialRunStateLabel(state: ApiProviderCredentialRunState) {
  const labels: Record<ApiProviderCredentialRunState["phase"], string> = {
    idle: "Idle",
    loading: "Loading",
    loaded: "Loaded",
    saving: "Saving",
    saved: "Saved",
    syncing: "Syncing",
    synced: "Synced",
    removing: "Removing",
    removed: "Removed",
    failed: "Unavailable"
  };
  return labels[state.phase];
}

function optionalNumberInput(value: string) {
  const text = value.trim();
  return text ? Number(text) : undefined;
}

function optionalTextInput(value: string) {
  const text = value.trim();
  return text || undefined;
}

function headerSubtitle(view: ViewId, dataMode: DashboardDataMode) {
  const summaryLabel =
    dataMode === "mock"
      ? "mock summary"
      : dataMode === "empty"
        ? "local aggregate once available"
        : "latest manual refresh aggregate";
  const subtitles: Record<ViewId, string> = {
    daily: `Local time: Asia/Shanghai. Today from the ${summaryLabel}.`,
    weekly: `Rolling 7-day aggregate from the ${summaryLabel}.`,
    sources: "Connector readiness and confidence labels.",
    api_costs: "Secondary API cost providers; unavailable data stays visible.",
    settings: "Timezone and privacy defaults for local aggregate storage."
  };
  return subtitles[view];
}

function startupDashboardModeLabel(dataMode: DashboardDataMode) {
  if (dataMode === "local_refresh") {
    return "Saved aggregate";
  }
  if (dataMode === "empty") {
    return "No local aggregate";
  }
  return "Mock fallback";
}

function configuredUsageSourceKinds(preferences: SourceRootPreferences): SourceKind[] {
  const configured: SourceKind[] = [];
  if (preferences.rootDraft.codexJsonlRoot?.trim()) {
    configured.push("codex");
  }
  if (preferences.rootDraft.claudeCodeJsonlRoot?.trim()) {
    configured.push("claude_code");
  }
  if (preferences.rootDraft.geminiCliJsonlRoot?.trim()) {
    configured.push("gemini_cli");
  }
  return configured;
}

function formatTokens(value: number) {
  return formatInteger(value);
}

function formatMetricTokens(value: number) {
  if (Math.abs(value) < 1_000_000) {
    return formatTokens(value);
  }
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 1,
    notation: "compact"
  }).format(value);
}

function formatInteger(value: number) {
  return new Intl.NumberFormat("en-US").format(value);
}

function formatCompactNumber(value: number) {
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: value < 10 ? 2 : 0
  }).format(value);
}

function formatUsd(value: number | null | undefined) {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "No data";
  }
  return new Intl.NumberFormat("en-US", {
    currency: "USD",
    style: "currency"
  }).format(value);
}

function formatPercent(value: number) {
  if (value > 0 && value < 1) {
    return "<1%";
  }
  return `${Math.round(value)}%`;
}

function allowanceUnitLabel(unit: AllowanceWindow["unit"]) {
  const labels: Record<AllowanceWindow["unit"], string> = {
    tokens: "tokens",
    credits: "credits",
    usd: "USD",
    requests: "requests",
    unknown: "allowance"
  };
  return labels[unit];
}

function formatAllowance(window: AllowanceWindow) {
  if (window.remaining_amount === undefined) {
    return "Not configured";
  }
  return window.unit === "tokens" ? formatTokens(window.remaining_amount) : `${window.remaining_amount}`;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

function cachedShare(totals: TokenTotals) {
  if (totals.input_tokens === 0) {
    return "Unavailable";
  }
  return `${Math.round((totals.cached_input_tokens / totals.input_tokens) * 100)}%`;
}

function yesNo(value: boolean) {
  return value ? "Yes" : "No";
}
