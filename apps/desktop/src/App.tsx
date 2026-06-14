import { useEffect, useState, type ReactNode } from "react";
import {
  AlertTriangle,
  BarChart3,
  CalendarDays,
  CheckCircle2,
  CircleDollarSign,
  Clock3,
  Database,
  Gauge,
  RefreshCw,
  Settings,
  ShieldCheck,
  TableProperties,
  X
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { loadStartupStorageSummary } from "./commands/loadStorageSummaryClient.js";
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
import mockSummary from "./data/mock-v1-summary.json";
import {
  buildDashboardSummaryFromRefresh,
  dashboardQualityLabel,
  emptyTokenTotals,
  latestSummaryDay,
  sourceUsageRows,
  sourceTotalsForDay,
  startupStorageStatusLabel,
  type DashboardDataMode,
  type StartupStorageReadState
} from "./data/dashboard-summary.js";
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
  RefreshStorageSummaryPayload,
  SourceKind,
  SourceRefreshSummaryPayload,
  TokenTotals
} from "./types";

const initialPayload = buildDashboardSummaryFromRefresh(mockSummary as RefreshStorageSummaryPayload);

type ViewId = "daily" | "weekly" | "sources" | "api_costs" | "settings";

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
  status: "Secondary source" | "Planned";
  detail: string;
};

const apiCostProviders: readonly ApiCostProvider[] = [
  {
    sourceKind: "openai_api_cost",
    status: "Secondary source",
    detail: "Admin/API cost sync is reserved for PR6"
  },
  {
    sourceKind: "claude_api_cost",
    status: "Planned",
    detail: "Provider billing export or official API required"
  },
  {
    sourceKind: "gemini_api_cost",
    status: "Planned",
    detail: "Provider billing export or official API required"
  },
  {
    sourceKind: "deepseek_api_cost",
    status: "Planned",
    detail: "Provider billing export or official API required"
  }
];

const navItems: Array<{ id: ViewId; label: string; icon: LucideIcon; secondary?: boolean }> = [
  { id: "daily", label: "Daily", icon: CalendarDays },
  { id: "weekly", label: "Weekly", icon: BarChart3 },
  { id: "sources", label: "Sources", icon: TableProperties },
  { id: "api_costs", label: "API Costs", icon: CircleDollarSign, secondary: true },
  { id: "settings", label: "Settings", icon: Settings }
];

export function App() {
  const [activeView, setActiveView] = useState<ViewId>("daily");
  const [dashboardPayload, setDashboardPayload] = useState<MockSummaryPayload>(initialPayload);
  const [dashboardDataMode, setDashboardDataMode] = useState<DashboardDataMode>("mock");
  const [lastRefreshResults, setLastRefreshResults] = useState<readonly RefreshResult[] | null>(null);
  const [startupStorageReadState, setStartupStorageReadState] = useState<StartupStorageReadState>({ phase: "idle" });
  const [sourceRootPreferences, setSourceRootPreferences] = useState<SourceRootPreferences>(
    defaultSourceRootPreferences
  );
  const [sourceRootPersistenceState, setSourceRootPersistenceState] =
    useState<SourceRootPersistenceState>({ phase: "idle" });
  const [manualRefreshRunState, setManualRefreshRunState] = useState<ManualRefreshRunState>({ phase: "idle" });
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

  function handleRefreshSummary(refreshSummary: SourceRefreshSummaryPayload) {
    setDashboardPayload(buildDashboardSummaryFromRefresh(refreshSummary.storage_summary));
    setDashboardDataMode("local_refresh");
    setLastRefreshResults(refreshSummary.refresh_results);
    setStartupStorageReadState({ phase: "loaded" });
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

    handleRefreshSummary(outcome.result);
    setManualRefreshRunState({
      phase: "succeeded",
      message: manualRefreshSuccessMessage(outcome.result.storage_summary.summary.totals.total_tokens)
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

  const manualRefreshKey = manualRefreshBoundary.canInvoke
    ? [
        manualRefreshBoundary.draft.endDayUtc,
        manualRefreshBoundary.draft.codexJsonlRoot,
        manualRefreshBoundary.draft.claudeCodeJsonlRoot
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
          <Gauge size={20} />
          <span>YourTokenHelper</span>
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
          manualRefreshBoundary,
          manualRefreshRunState,
          sourceRootPersistenceState,
          sourceRootPreferences,
          rootsAreSavedForAutoRefresh,
          clearExplicitRoot,
          forgetExplicitRoots,
          handleManualRefresh,
          saveExplicitRoots,
          setAutoRefreshEnabled,
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
  manualRefreshBoundary: ReturnType<typeof buildManualRefreshDraftFromHiddenRoots>,
  manualRefreshRunState: ManualRefreshRunState,
  sourceRootPersistenceState: SourceRootPersistenceState,
  sourceRootPreferences: SourceRootPreferences,
  rootsAreSavedForAutoRefresh: boolean,
  onClearRoot: (sourceKind: ExplicitRootSourceKind) => void,
  onForgetRoots: () => void,
  onManualRefresh: () => void,
  onSaveRoots: () => void,
  onAutoRefreshChange: (enabled: boolean) => void,
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
        manualRefreshBoundary={manualRefreshBoundary}
        manualRefreshRunState={manualRefreshRunState}
        onAutoRefreshChange={onAutoRefreshChange}
        onClearRoot={onClearRoot}
        onForgetRoots={onForgetRoots}
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
    return <ApiCostsView dataMode={dataMode} payload={payload} />;
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
  const remaining = firstKnownAllowance(payload, ["codex", "claude_code"]);
  const missingAllowances = payload.allowance_windows.filter((item) => item.status === "unavailable");

  return (
    <>
      <PrimaryMetricStrip dataMode={dataMode} totals={daily} remaining={remaining} windowLabel="Today" />

      <section className="main-grid">
        <div className="left-stack">
          <Panel title="Source Usage">
            <SourceStack
              configuredSourceKinds={configuredSourceKinds}
              totals={dailySourceTotals}
              overallTotal={daily.total_tokens}
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
          <Panel title="Trust">
            <div className="trust-row">
              <ShieldCheck size={16} />
              <div>
                <strong>{dataMode === "mock" ? "Contract-backed mock" : "Live local aggregate"}</strong>
                <span>
                  {dataMode === "mock"
                    ? "Local exact where ready; estimates are labeled."
                    : "Manual refresh aggregate; unavailable allowance stays labeled."}
                </span>
              </div>
            </div>
            <div className="issue-list">
              {missingAllowances.map((item) => (
                <div className="issue" key={item.source_kind}>
                  <span>{sourceLabels[item.source_kind]}</span>
                  <StatusBadge label="Allowance unavailable" />
                </div>
              ))}
            </div>
          </Panel>

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
  const remaining = firstKnownAllowance(payload, ["codex", "claude_code"]);

  return (
    <>
      <PrimaryMetricStrip dataMode={dataMode} totals={rolling.totals} remaining={remaining} windowLabel="Rolling 7 days" />

      <section className="main-grid">
        <div className="left-stack">
          <Panel title="Daily Trend">
            <DailyTrend payload={payload} />
          </Panel>

          <Panel title="Weekly Source Split">
            <SourceStack
              configuredSourceKinds={configuredSourceKinds}
              totals={payload.summary.by_source}
              overallTotal={rolling.totals.total_tokens}
            />
          </Panel>
        </div>

        <aside className="right-stack">
          <Panel title="Rolling Window">
            <div className="fact-list">
              <Fact label="Start" value={rolling.window_start ?? "Unavailable"} />
              <Fact label="End" value={rolling.window_end ?? "Unavailable"} />
              <Fact label="Days" value={String(Object.keys(payload.summary.by_day).length)} />
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
  manualRefreshBoundary,
  manualRefreshRunState,
  onAutoRefreshChange,
  onClearRoot,
  onForgetRoots,
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
  manualRefreshBoundary: ReturnType<typeof buildManualRefreshDraftFromHiddenRoots>;
  manualRefreshRunState: ManualRefreshRunState;
  onAutoRefreshChange: (enabled: boolean) => void;
  onClearRoot: (sourceKind: ExplicitRootSourceKind) => void;
  onForgetRoots: () => void;
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
                  <td>{allowance ? allowance.status.replace("_", " ") : "unavailable"}</td>
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
        <StartupStorageStatus dataMode={dataMode} state={startupStorageReadState} />
      </Panel>

      <Panel title="Last Refresh">
        <LastRefreshResults results={lastRefreshResults} />
      </Panel>

      <div className="two-column">
        <StatePanel icon={<Database size={18} />} title="First Launch" action="Choose sources" />
        <StatePanel icon={<AlertTriangle size={18} />} title="No Local Sources" action="Open settings" />
      </div>
    </section>
  );
}

function StartupStorageStatus({
  dataMode,
  state
}: {
  dataMode: DashboardDataMode;
  state: StartupStorageReadState;
}) {
  return (
    <div className="manual-refresh-mock" aria-label="Saved aggregate readback state">
      <div className="manual-refresh-row">
        <span>Readback</span>
        <StatusBadge label={startupStorageStatusLabel(state)} />
      </div>
      <div className="manual-refresh-row">
        <span>Dashboard</span>
        <strong>{dataMode === "local_refresh" ? "Saved aggregate" : "Mock fallback"}</strong>
      </div>
      <div className="manual-refresh-row">
        <span>Refresh</span>
        <strong>Manual or auto</strong>
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
    <div className="manual-refresh-mock" aria-label="Manual refresh mock state">
      <div className="manual-refresh-row">
        <span>Command</span>
        <strong>{manualRefreshMockState.commandName}</strong>
      </div>
      <div className="manual-refresh-row">
        <span>State</span>
        <StatusBadge label={stateLabel} />
      </div>
      <div className="manual-refresh-row">
        <span>Roots</span>
        <strong>{rootsLabel}</strong>
      </div>
      <div className="manual-refresh-row">
        <span>Needs</span>
        <strong>{needsLabel}</strong>
      </div>
      <div className="manual-refresh-row">
        <span>Bridge</span>
        <StatusBadge label={bridgeLabel} />
      </div>
      <div className="manual-refresh-row">
        <span>Auto</span>
        <StatusBadge label={autoStatusLabel} />
      </div>
      <div className="manual-refresh-row">
        <span>Interval</span>
        <strong>{autoRefreshIntervalMinutes} min</strong>
      </div>
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
        aria-label={canInvoke ? "Run gated manual refresh" : manualRefreshMockState.disabledAriaLabel}
        className="sync-button"
        disabled={!canInvoke || isRunning}
        onClick={onRefresh}
        title={canInvoke ? "Run production manual refresh" : manualRefreshMockState.disabledTitle}
        type="button"
      >
        <RefreshCw size={15} />
        {isRunning ? "Refreshing" : "Refresh"}
      </button>
      {runState.phase === "succeeded" || runState.phase === "failed" ? (
        <div className="manual-refresh-row">
          <span>Result</span>
          <strong>{runState.message}</strong>
        </div>
      ) : null}
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
  return row.sourceKind === "codex" || row.sourceKind === "claude_code";
}

function rootDraftValue(sourceKind: ExplicitRootSourceKind, draft: ExplicitRootSelectionDraft) {
  return sourceKind === "codex" ? draft.codexJsonlRoot ?? "" : draft.claudeCodeJsonlRoot ?? "";
}

function ApiCostsView({ dataMode, payload }: { dataMode: DashboardDataMode; payload: MockSummaryPayload }) {
  const costTotals = payload.summary.by_source.openai_api_cost;
  const costWindow = payload.allowance_windows.find((item) => item.source_kind === "openai_api_cost");
  const costEstimateValue = dataMode === "mock" ? "$1.03" : "Unavailable";
  const costEstimateUnit = dataMode === "mock" ? "mock estimate" : "secondary source not connected";

  return (
    <section className="single-column">
      <div className="metric-strip compact" aria-label="API cost metrics">
        <MetricTile label="Cost estimate" value={costEstimateValue} unit={costEstimateUnit} tone="secondary" />
        <MetricTile label="Providers" value={String(apiCostProviders.length)} unit="secondary sources" />
        <MetricTile label="Connected" value="0" unit="cost sync unavailable" />
        <MetricTile label="Cost source" value="Unavailable" unit={costWindow?.status.replace("_", " ") ?? "not connected"} />
      </div>

      <Panel title="Provider Status">
        <table className="data-table">
          <thead>
            <tr>
              <th>Provider</th>
              <th>Status</th>
              <th>Next step</th>
            </tr>
          </thead>
          <tbody>
            {apiCostProviders.map((provider) => (
              <tr key={provider.sourceKind}>
                <td>{sourceLabels[provider.sourceKind]}</td>
                <td><StatusBadge label={provider.status} /></td>
                <td>{provider.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>

      <Panel title="API Cost Breakdown">
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
  dataMode,
  totals,
  remaining,
  windowLabel
}: {
  dataMode: DashboardDataMode;
  totals: TokenTotals;
  remaining: AllowanceWindow | undefined;
  windowLabel: string;
}) {
  const costEstimateValue = dataMode === "mock" ? "$1.03" : "Unavailable";
  const costEstimateUnit = dataMode === "mock" ? "secondary source" : "secondary source not connected";

  return (
    <section className="metric-strip" aria-label={`${windowLabel} metrics`}>
      <MetricTile label="Usage consumed" value={formatTokens(totals.total_tokens)} unit="tokens" tone="primary" />
      <MetricTile
        label="Remaining"
        value={remaining ? formatAllowance(remaining) : "Unavailable"}
        unit={remaining?.status === "manual" ? "manual estimate" : "derived estimate"}
      />
      <MetricTile label="Reset" value={remaining?.reset_at ? formatDate(remaining.reset_at) : "Unavailable"} unit="next known reset" />
      <MetricTile label="Cost estimate" value={costEstimateValue} unit={costEstimateUnit} tone="secondary" />
      <MetricTile label="Window" value={windowLabel} unit={dataMode === "mock" ? "mock contract" : "local aggregate"} />
      <MetricTile label="Cached share" value={cachedShare(totals)} unit="input tokens" />
    </section>
  );
}

function MetricTile({ label, value, unit, tone }: { label: string; value: string; unit: string; tone?: "primary" | "secondary" }) {
  const valueClassName = isCompactMetricValue(value, tone) ? "compact-value" : "";

  return (
    <div className={`metric-tile ${tone ?? ""}`}>
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
  configuredSourceKinds,
  totals,
  overallTotal
}: {
  configuredSourceKinds: readonly SourceKind[];
  totals: Record<SourceKind, TokenTotals>;
  overallTotal: number;
}) {
  const rows = sourceUsageRows(totals, configuredSourceKinds);

  return (
    <div className="source-stack">
      {rows.map(({ sourceKind, totals: total }) => {
        const percent = barPercent(total.total_tokens, overallTotal, 4);
        return (
          <div className="stack-row" key={sourceKind}>
            <div className="stack-label">
              <span>{sourceLabels[sourceKind]}</span>
              <span>{formatTokens(total.total_tokens)}</span>
            </div>
            <div className="bar-track">
              <span className="bar-fill" style={{ width: `${percent}%`, background: sourceColors[sourceKind] }} />
            </div>
          </div>
        );
      })}
    </div>
  );
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

function StatePanel({ icon, title, action }: { icon: ReactNode; title: string; action: string }) {
  return (
    <Panel title={title}>
      <div className="empty-state">
        {icon}
        <strong>{title}</strong>
        <button className="sync-button" disabled type="button">{action}</button>
      </div>
    </Panel>
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

function isCompactMetricValue(value: string, tone?: "primary" | "secondary") {
  return tone !== "primary" && value.length >= 10;
}

function barPercent(value: number, max: number, minimumVisiblePercent: number) {
  if (value <= 0 || max <= 0) {
    return 0;
  }
  return Math.max(minimumVisiblePercent, Math.round((value / max) * 100));
}

function firstKnownAllowance(payload: MockSummaryPayload, sourceKinds: SourceKind[]) {
  return payload.allowance_windows.find(
    (window) => sourceKinds.includes(window.source_kind) && window.remaining_amount !== undefined
  );
}

function headerSubtitle(view: ViewId, dataMode: DashboardDataMode) {
  const summaryLabel = dataMode === "mock" ? "mock summary" : "latest manual refresh aggregate";
  const subtitles: Record<ViewId, string> = {
    daily: `Local time: Asia/Shanghai. Today from the ${summaryLabel}.`,
    weekly: `Rolling 7-day aggregate from the ${summaryLabel}.`,
    sources: "Connector readiness and confidence labels.",
    api_costs: "Secondary API cost providers; unavailable data stays visible.",
    settings: "Timezone and privacy defaults for the mock shell."
  };
  return subtitles[view];
}

function configuredUsageSourceKinds(preferences: SourceRootPreferences): SourceKind[] {
  const configured: SourceKind[] = [];
  if (preferences.rootDraft.codexJsonlRoot?.trim()) {
    configured.push("codex");
  }
  if (preferences.rootDraft.claudeCodeJsonlRoot?.trim()) {
    configured.push("claude_code");
  }
  return configured;
}

function formatTokens(value: number) {
  return formatInteger(value);
}

function formatInteger(value: number) {
  return new Intl.NumberFormat("en-US").format(value);
}

function formatAllowance(window: AllowanceWindow) {
  if (window.remaining_amount === undefined) {
    return "Unavailable";
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
