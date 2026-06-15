use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::{
    collections::BTreeMap,
    env, fs,
    io::{self, Write},
    path::{Path, PathBuf},
    process::{Command, Stdio},
};
use tauri::Manager;
use tauri_plugin_shell::{process::CommandEvent, ShellExt};

pub const SOURCE_REFRESH_SUMMARY_SAMPLE_COMMAND: &str = "source_refresh_summary_sample";
pub const REFRESH_SOURCES_MANUAL_COMMAND: &str = "refresh_sources_manual";
pub const LOAD_STORAGE_SUMMARY_COMMAND: &str = "load_storage_summary";
pub const SAVE_MANUAL_ALLOWANCE_WINDOW_COMMAND: &str = "save_manual_allowance_window";
pub const LOAD_SAVED_SOURCE_ROOTS_COMMAND: &str = "load_saved_source_roots";
pub const SAVE_SOURCE_ROOTS_COMMAND: &str = "save_source_roots";
pub const CLEAR_SAVED_SOURCE_ROOTS_COMMAND: &str = "clear_saved_source_roots";
pub const LOAD_API_PROVIDER_CREDENTIALS_COMMAND: &str = "load_api_provider_credentials";
pub const SAVE_API_PROVIDER_CREDENTIAL_COMMAND: &str = "save_api_provider_credential";
pub const REMOVE_API_PROVIDER_CREDENTIAL_COMMAND: &str = "remove_api_provider_credential";
pub const SYNC_API_PROVIDER_BILLING_COMMAND: &str = "sync_api_provider_billing";
pub const BACKEND_REFRESH_COMMAND_MODULE: &str = "backend.sources.refresh_command_cli";
pub const BACKEND_LOAD_STORAGE_SUMMARY_COMMAND_MODULE: &str = "backend.storage.summary_command_cli";
pub const BACKEND_MANUAL_ALLOWANCE_COMMAND_MODULE: &str =
    "backend.sources.manual_allowance_command_cli";
pub const BACKEND_API_PROVIDER_BILLING_SYNC_COMMAND_MODULE: &str =
    "backend.sources.api_provider_billing_sync_command_cli";
pub const BACKEND_SIDECAR_NAME: &str = "yth-backend";
pub const REFRESH_DATABASE_PATH_ENV_VAR: &str = "YTH_REFRESH_DATABASE_PATH";
pub const OPENAI_ADMIN_KEY_ENV_VAR: &str = "OPENAI_ADMIN_KEY";
pub const REFRESH_DATABASE_FILE_NAME: &str = "usage.sqlite";
pub const SOURCE_ROOTS_FILE_NAME: &str = "source-roots.json";
pub const API_PROVIDER_CREDENTIALS_FILE_NAME: &str = "api-provider-credentials.json";
pub const DEFAULT_AUTO_REFRESH_INTERVAL_MINUTES: u16 = 15;
const API_COST_PROVIDER_IDS: [&str; 4] = [
    "openai_api_cost",
    "claude_api_cost",
    "gemini_api_cost",
    "deepseek_api_cost",
];
const VERIFIED_API_COST_PROVIDER_IDS: [&str; 1] = ["openai_api_cost"];

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RefreshSourcesManualArgs {
    pub end_day_utc: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub codex_jsonl_root: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub claude_code_jsonl_root: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub gemini_cli_jsonl_root: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub started_at: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(untagged)]
pub enum RefreshSourcesManualResult {
    Error(RefreshCommandErrorPayload),
    Success(Value),
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct LoadStorageSummaryArgs {
    pub end_day_utc: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ManualAllowanceArgs {
    pub end_day_utc: String,
    pub source_kind: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub unit: Option<String>,
    pub limit_amount: f64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub used_amount: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub remaining_amount: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub window_start: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub window_end: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub reset_at: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SavedSourceRoots {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub codex_jsonl_root: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub claude_code_jsonl_root: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub gemini_cli_jsonl_root: Option<String>,
    #[serde(default)]
    pub auto_refresh_enabled: bool,
    #[serde(default = "default_auto_refresh_interval_minutes")]
    pub auto_refresh_interval_minutes: u16,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(deny_unknown_fields)]
pub struct ApiProviderCredentialStore {
    #[serde(default)]
    pub credentials: BTreeMap<String, ApiProviderCredentialRecord>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ApiProviderCredentialRecord {
    pub protected_api_key: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ApiProviderCredentialStatus {
    pub provider_id: String,
    pub status: String,
    pub adapter_verified: bool,
    pub credential_configured: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub message: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ApiProviderCredentialStatuses {
    pub providers: Vec<ApiProviderCredentialStatus>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SaveApiProviderCredentialArgs {
    pub provider_id: String,
    pub api_key: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RemoveApiProviderCredentialArgs {
    pub provider_id: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SyncApiProviderBillingArgs {
    pub provider_id: String,
    pub end_day_utc: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub started_at: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(untagged)]
pub enum LoadStorageSummaryResult {
    Error(RefreshCommandErrorPayload),
    Success(Value),
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(untagged)]
pub enum ManualAllowanceResult {
    Error(RefreshCommandErrorPayload),
    Success(Value),
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(untagged)]
pub enum ApiProviderBillingSyncResult {
    Error(RefreshCommandErrorPayload),
    Success(Value),
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RefreshCommandErrorPayload {
    pub error: RefreshCommandError,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RefreshCommandError {
    pub code: String,
    pub message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub field: Option<String>,
}

impl Default for SavedSourceRoots {
    fn default() -> Self {
        Self {
            codex_jsonl_root: None,
            claude_code_jsonl_root: None,
            gemini_cli_jsonl_root: None,
            auto_refresh_enabled: false,
            auto_refresh_interval_minutes: DEFAULT_AUTO_REFRESH_INTERVAL_MINUTES,
        }
    }
}

const SOURCE_REFRESH_SUMMARY_SAMPLE: &str = include_str!("../source-refresh-summary.sample.json");
const SOURCE_REFRESH_ERROR_SAMPLE: &str = include_str!("../source-refresh-error.sample.json");

pub fn source_refresh_summary_sample_payload() -> Value {
    serde_json::from_str(SOURCE_REFRESH_SUMMARY_SAMPLE)
        .expect("embedded source refresh summary sample must be valid JSON")
}

pub fn source_refresh_error_sample_payload() -> Value {
    serde_json::from_str(SOURCE_REFRESH_ERROR_SAMPLE)
        .expect("embedded source refresh error sample must be valid JSON")
}

pub fn backend_refresh_process_module_args() -> [&'static str; 2] {
    ["-m", BACKEND_REFRESH_COMMAND_MODULE]
}

pub fn backend_load_storage_summary_process_module_args() -> [&'static str; 2] {
    ["-m", BACKEND_LOAD_STORAGE_SUMMARY_COMMAND_MODULE]
}

pub fn backend_manual_allowance_process_module_args() -> [&'static str; 2] {
    ["-m", BACKEND_MANUAL_ALLOWANCE_COMMAND_MODULE]
}

pub fn backend_api_provider_billing_sync_process_module_args() -> [&'static str; 2] {
    ["-m", BACKEND_API_PROVIDER_BILLING_SYNC_COMMAND_MODULE]
}

pub fn refresh_sources_manual_stdin(
    args: &RefreshSourcesManualArgs,
) -> Result<String, serde_json::Error> {
    serde_json::to_string(args)
}

pub fn refresh_sources_manual_result_from_stdout(
    stdout: &str,
) -> Result<RefreshSourcesManualResult, serde_json::Error> {
    serde_json::from_str(stdout)
}

pub fn load_storage_summary_stdin(
    args: &LoadStorageSummaryArgs,
) -> Result<String, serde_json::Error> {
    serde_json::to_string(args)
}

pub fn load_storage_summary_result_from_stdout(
    stdout: &str,
) -> Result<LoadStorageSummaryResult, serde_json::Error> {
    serde_json::from_str(stdout)
}

pub fn save_manual_allowance_stdin(
    args: &ManualAllowanceArgs,
) -> Result<String, serde_json::Error> {
    serde_json::to_string(args)
}

pub fn save_manual_allowance_result_from_stdout(
    stdout: &str,
) -> Result<ManualAllowanceResult, serde_json::Error> {
    serde_json::from_str(stdout)
}

pub fn sync_api_provider_billing_stdin(
    args: &SyncApiProviderBillingArgs,
) -> Result<String, serde_json::Error> {
    serde_json::to_string(args)
}

pub fn api_provider_billing_sync_result_from_stdout(
    stdout: &str,
) -> Result<ApiProviderBillingSyncResult, serde_json::Error> {
    serde_json::from_str(stdout)
}

pub fn normalize_saved_source_roots(args: SavedSourceRoots) -> SavedSourceRoots {
    let codex_jsonl_root = normalize_optional_root(args.codex_jsonl_root);
    let claude_code_jsonl_root = normalize_optional_root(args.claude_code_jsonl_root);
    let gemini_cli_jsonl_root = normalize_optional_root(args.gemini_cli_jsonl_root);
    let has_any_root = codex_jsonl_root.is_some()
        || claude_code_jsonl_root.is_some()
        || gemini_cli_jsonl_root.is_some();

    SavedSourceRoots {
        codex_jsonl_root,
        claude_code_jsonl_root,
        gemini_cli_jsonl_root,
        auto_refresh_enabled: args.auto_refresh_enabled && has_any_root,
        auto_refresh_interval_minutes: normalize_auto_refresh_interval_minutes(
            args.auto_refresh_interval_minutes,
        ),
    }
}

pub fn load_saved_source_roots_from_path(path: &Path) -> Result<SavedSourceRoots, String> {
    if !path.exists() {
        return Ok(SavedSourceRoots::default());
    }

    let text =
        fs::read_to_string(path).map_err(|_| "saved source roots could not be read".to_string())?;
    let saved = serde_json::from_str::<SavedSourceRoots>(&text)
        .map_err(|_| "saved source roots were invalid".to_string())?;
    Ok(normalize_saved_source_roots(saved))
}

pub fn save_source_roots_to_path(
    path: &Path,
    args: &SavedSourceRoots,
) -> Result<SavedSourceRoots, String> {
    let saved = normalize_saved_source_roots(args.clone());
    if let Some(parent) = refresh_database_parent_dir(path) {
        fs::create_dir_all(parent)
            .map_err(|_| "failed to prepare source roots directory".to_string())?;
    }
    let text = serde_json::to_string(&saved)
        .map_err(|_| "failed to serialize source roots".to_string())?;
    fs::write(path, text).map_err(|_| "failed to save source roots".to_string())?;
    Ok(saved)
}

pub fn clear_saved_source_roots_at_path(path: &Path) -> Result<(), String> {
    match fs::remove_file(path) {
        Ok(()) => Ok(()),
        Err(error) if error.kind() == io::ErrorKind::NotFound => Ok(()),
        Err(_) => Err("failed to clear source roots".to_string()),
    }
}

pub fn load_api_provider_credentials_from_path(
    path: &Path,
) -> Result<ApiProviderCredentialStatuses, String> {
    let store = load_api_provider_credential_store_from_path(path)?;
    Ok(api_provider_credential_statuses_from_store(&store))
}

pub fn save_api_provider_credential_to_path(
    path: &Path,
    args: &SaveApiProviderCredentialArgs,
) -> Result<ApiProviderCredentialStatuses, String> {
    validate_api_provider_id(&args.provider_id)?;
    let api_key = normalize_api_provider_key(&args.api_key)?;
    let mut store = load_api_provider_credential_store_from_path(path)?;
    store.credentials.insert(
        args.provider_id.clone(),
        ApiProviderCredentialRecord {
            protected_api_key: protect_secret(&api_key)?,
        },
    );
    save_api_provider_credential_store_to_path(path, &store)?;
    Ok(api_provider_credential_statuses_from_store(&store))
}

pub fn remove_api_provider_credential_at_path(
    path: &Path,
    args: &RemoveApiProviderCredentialArgs,
) -> Result<ApiProviderCredentialStatuses, String> {
    validate_api_provider_id(&args.provider_id)?;
    let mut store = load_api_provider_credential_store_from_path(path)?;
    store.credentials.remove(&args.provider_id);
    save_api_provider_credential_store_to_path(path, &store)?;
    Ok(api_provider_credential_statuses_from_store(&store))
}

fn load_api_provider_credential_store_from_path(
    path: &Path,
) -> Result<ApiProviderCredentialStore, String> {
    if !path.exists() {
        return Ok(ApiProviderCredentialStore::default());
    }

    let text = fs::read_to_string(path)
        .map_err(|_| "API provider credentials could not be read".to_string())?;
    serde_json::from_str::<ApiProviderCredentialStore>(&text)
        .map_err(|_| "API provider credentials were invalid".to_string())
}

fn save_api_provider_credential_store_to_path(
    path: &Path,
    store: &ApiProviderCredentialStore,
) -> Result<(), String> {
    if let Some(parent) = refresh_database_parent_dir(path) {
        fs::create_dir_all(parent)
            .map_err(|_| "failed to prepare API provider credential directory".to_string())?;
    }
    let text = serde_json::to_string(store)
        .map_err(|_| "failed to serialize API provider credentials".to_string())?;
    fs::write(path, text).map_err(|_| "failed to save API provider credentials".to_string())
}

pub fn load_api_provider_credential_from_path(
    path: &Path,
    provider_id: &str,
) -> Result<Option<String>, String> {
    validate_api_provider_id(provider_id)?;
    let store = load_api_provider_credential_store_from_path(path)?;
    let Some(record) = store.credentials.get(provider_id) else {
        return Ok(None);
    };
    Ok(Some(unprotect_secret(&record.protected_api_key)?))
}

fn api_provider_credential_statuses_from_store(
    store: &ApiProviderCredentialStore,
) -> ApiProviderCredentialStatuses {
    ApiProviderCredentialStatuses {
        providers: API_COST_PROVIDER_IDS
            .iter()
            .map(|provider_id| {
                api_provider_credential_status(
                    provider_id,
                    store.credentials.contains_key(*provider_id),
                )
            })
            .collect(),
    }
}

fn api_provider_credential_status(
    provider_id: &str,
    credential_configured: bool,
) -> ApiProviderCredentialStatus {
    let adapter_verified = VERIFIED_API_COST_PROVIDER_IDS.contains(&provider_id);
    if !adapter_verified {
        return ApiProviderCredentialStatus {
            provider_id: provider_id.to_string(),
            status: "needs_verified_adapter".to_string(),
            adapter_verified: false,
            credential_configured,
            message: Some("Provider billing adapter has not been verified.".to_string()),
        };
    }
    if !credential_configured {
        return ApiProviderCredentialStatus {
            provider_id: provider_id.to_string(),
            status: "not_configured".to_string(),
            adapter_verified: true,
            credential_configured: false,
            message: None,
        };
    }
    ApiProviderCredentialStatus {
        provider_id: provider_id.to_string(),
        status: "unavailable".to_string(),
        adapter_verified: true,
        credential_configured: true,
        message: Some("Provider credential has not been validated.".to_string()),
    }
}

fn validate_api_provider_id(provider_id: &str) -> Result<(), String> {
    if API_COST_PROVIDER_IDS.contains(&provider_id) {
        return Ok(());
    }
    Err("Unknown API cost provider".to_string())
}

fn normalize_api_provider_key(api_key: &str) -> Result<String, String> {
    let normalized = api_key.trim();
    if normalized.is_empty() {
        return Err("API provider credential is required".to_string());
    }
    Ok(normalized.to_string())
}

fn normalize_optional_root(root: Option<String>) -> Option<String> {
    root.map(|value| value.trim().to_string())
        .filter(|value| !value.is_empty())
}

fn normalize_auto_refresh_interval_minutes(minutes: u16) -> u16 {
    if minutes < 5 {
        return DEFAULT_AUTO_REFRESH_INTERVAL_MINUTES;
    }
    minutes.min(1440)
}

fn default_auto_refresh_interval_minutes() -> u16 {
    DEFAULT_AUTO_REFRESH_INTERVAL_MINUTES
}

pub fn run_refresh_sources_manual_backend_process(
    python_executable: &Path,
    workspace_root: &Path,
    args: &RefreshSourcesManualArgs,
) -> Result<RefreshSourcesManualResult, String> {
    run_refresh_sources_manual_backend_process_with_database_path(
        python_executable,
        workspace_root,
        args,
        None,
    )
}

pub fn run_refresh_sources_manual_backend_process_with_database_path(
    python_executable: &Path,
    workspace_root: &Path,
    args: &RefreshSourcesManualArgs,
    refresh_database_path: Option<&Path>,
) -> Result<RefreshSourcesManualResult, String> {
    let stdin = refresh_sources_manual_stdin(args)
        .map_err(|_| "failed to serialize refresh request".to_string())?;
    let mut command = Command::new(python_executable);
    command
        .args(backend_refresh_process_module_args())
        .current_dir(workspace_root);
    if let Some(path) = refresh_database_path {
        if let Some(parent) = refresh_database_parent_dir(path) {
            fs::create_dir_all(parent)
                .map_err(|_| "failed to prepare refresh database directory".to_string())?;
        }
        command.env(REFRESH_DATABASE_PATH_ENV_VAR, path);
    }
    let mut child = command
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|_| "failed to start backend refresh process".to_string())?;

    let mut child_stdin = child
        .stdin
        .take()
        .ok_or_else(|| "failed to open backend refresh stdin".to_string())?;
    child_stdin
        .write_all(stdin.as_bytes())
        .map_err(|_| "failed to write backend refresh stdin".to_string())?;
    drop(child_stdin);

    let output = child
        .wait_with_output()
        .map_err(|_| "failed to read backend refresh output".to_string())?;
    if !output.status.success() {
        return Err("backend refresh process failed".to_string());
    }
    let stdout = String::from_utf8(output.stdout)
        .map_err(|_| "backend refresh stdout was not utf-8".to_string())?;
    refresh_sources_manual_result_from_stdout(&stdout)
        .map_err(|_| "backend refresh stdout was not a valid refresh result".to_string())
}

pub fn run_load_storage_summary_backend_process_with_database_path(
    python_executable: &Path,
    workspace_root: &Path,
    args: &LoadStorageSummaryArgs,
    refresh_database_path: Option<&Path>,
) -> Result<LoadStorageSummaryResult, String> {
    let stdin = load_storage_summary_stdin(args)
        .map_err(|_| "failed to serialize storage summary request".to_string())?;
    let mut command = Command::new(python_executable);
    command
        .args(backend_load_storage_summary_process_module_args())
        .current_dir(workspace_root);
    if let Some(path) = refresh_database_path {
        command.env(REFRESH_DATABASE_PATH_ENV_VAR, path);
    }
    let mut child = command
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|_| "failed to start backend storage summary process".to_string())?;

    let mut child_stdin = child
        .stdin
        .take()
        .ok_or_else(|| "failed to open backend storage summary stdin".to_string())?;
    child_stdin
        .write_all(stdin.as_bytes())
        .map_err(|_| "failed to write backend storage summary stdin".to_string())?;
    drop(child_stdin);

    let output = child
        .wait_with_output()
        .map_err(|_| "failed to read backend storage summary output".to_string())?;
    if !output.status.success() {
        return Err("backend storage summary process failed".to_string());
    }
    let stdout = String::from_utf8(output.stdout)
        .map_err(|_| "backend storage summary stdout was not utf-8".to_string())?;
    load_storage_summary_result_from_stdout(&stdout)
        .map_err(|_| "backend storage summary stdout was not a valid result".to_string())
}

pub fn run_save_manual_allowance_backend_process_with_database_path(
    python_executable: &Path,
    workspace_root: &Path,
    args: &ManualAllowanceArgs,
    refresh_database_path: Option<&Path>,
) -> Result<ManualAllowanceResult, String> {
    let stdin = save_manual_allowance_stdin(args)
        .map_err(|_| "failed to serialize manual allowance request".to_string())?;
    let mut command = Command::new(python_executable);
    command
        .args(backend_manual_allowance_process_module_args())
        .current_dir(workspace_root);
    if let Some(path) = refresh_database_path {
        if let Some(parent) = refresh_database_parent_dir(path) {
            fs::create_dir_all(parent)
                .map_err(|_| "failed to prepare refresh database directory".to_string())?;
        }
        command.env(REFRESH_DATABASE_PATH_ENV_VAR, path);
    }
    let mut child = command
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|_| "failed to start backend manual allowance process".to_string())?;

    let mut child_stdin = child
        .stdin
        .take()
        .ok_or_else(|| "failed to open backend manual allowance stdin".to_string())?;
    child_stdin
        .write_all(stdin.as_bytes())
        .map_err(|_| "failed to write backend manual allowance stdin".to_string())?;
    drop(child_stdin);

    let output = child
        .wait_with_output()
        .map_err(|_| "failed to read backend manual allowance output".to_string())?;
    if !output.status.success() {
        return Err("backend manual allowance process failed".to_string());
    }
    let stdout = String::from_utf8(output.stdout)
        .map_err(|_| "backend manual allowance stdout was not utf-8".to_string())?;
    save_manual_allowance_result_from_stdout(&stdout)
        .map_err(|_| "backend manual allowance stdout was not a valid result".to_string())
}

pub fn run_api_provider_billing_sync_backend_process_with_database_path(
    python_executable: &Path,
    workspace_root: &Path,
    args: &SyncApiProviderBillingArgs,
    refresh_database_path: Option<&Path>,
    api_key: Option<&str>,
) -> Result<ApiProviderBillingSyncResult, String> {
    let stdin = sync_api_provider_billing_stdin(args)
        .map_err(|_| "failed to serialize API provider billing sync request".to_string())?;
    let mut command = Command::new(python_executable);
    command
        .args(backend_api_provider_billing_sync_process_module_args())
        .current_dir(workspace_root);
    if let Some(path) = refresh_database_path {
        if let Some(parent) = refresh_database_parent_dir(path) {
            fs::create_dir_all(parent)
                .map_err(|_| "failed to prepare refresh database directory".to_string())?;
        }
        command.env(REFRESH_DATABASE_PATH_ENV_VAR, path);
    }
    command.env_remove(OPENAI_ADMIN_KEY_ENV_VAR);
    if let Some(key) = api_key {
        command.env(OPENAI_ADMIN_KEY_ENV_VAR, key);
    }
    let mut child = command
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|_| "failed to start backend API provider billing sync process".to_string())?;

    let mut child_stdin = child
        .stdin
        .take()
        .ok_or_else(|| "failed to open backend API provider billing sync stdin".to_string())?;
    child_stdin
        .write_all(stdin.as_bytes())
        .map_err(|_| "failed to write backend API provider billing sync stdin".to_string())?;
    drop(child_stdin);

    let output = child
        .wait_with_output()
        .map_err(|_| "failed to read backend API provider billing sync output".to_string())?;
    if !output.status.success() {
        return Err("backend API provider billing sync process failed".to_string());
    }
    let stdout = String::from_utf8(output.stdout)
        .map_err(|_| "backend API provider billing sync stdout was not utf-8".to_string())?;
    api_provider_billing_sync_result_from_stdout(&stdout)
        .map_err(|_| "backend API provider billing sync stdout was not a valid result".to_string())
}

pub fn run_gated_refresh_sources_manual_backend_process(
    python_executable: &Path,
    workspace_root: &Path,
    args: &RefreshSourcesManualArgs,
) -> Result<RefreshSourcesManualResult, String> {
    run_gated_refresh_sources_manual_backend_process_with_database_path(
        python_executable,
        workspace_root,
        args,
        None,
    )
}

pub fn run_gated_refresh_sources_manual_backend_process_with_database_path(
    python_executable: &Path,
    workspace_root: &Path,
    args: &RefreshSourcesManualArgs,
    refresh_database_path: Option<&Path>,
) -> Result<RefreshSourcesManualResult, String> {
    if !has_any_refresh_source_root(args) {
        return Ok(invalid_refresh_request(
            "codex_jsonl_root",
            "at least one source root is required for manual refresh",
        ));
    }

    run_refresh_sources_manual_backend_process_with_database_path(
        python_executable,
        workspace_root,
        args,
        refresh_database_path,
    )
}

fn run_gated_refresh_sources_manual_sidecar_process_with_database_path(
    app: &tauri::AppHandle,
    args: &RefreshSourcesManualArgs,
    refresh_database_path: Option<&Path>,
) -> Result<RefreshSourcesManualResult, String> {
    if !has_any_refresh_source_root(args) {
        return Ok(invalid_refresh_request(
            "codex_jsonl_root",
            "at least one source root is required for manual refresh",
        ));
    }

    run_refresh_sources_manual_sidecar_process_with_database_path(app, args, refresh_database_path)
}

fn run_refresh_sources_manual_sidecar_process_with_database_path(
    app: &tauri::AppHandle,
    args: &RefreshSourcesManualArgs,
    refresh_database_path: Option<&Path>,
) -> Result<RefreshSourcesManualResult, String> {
    let stdin = refresh_sources_manual_stdin(args)
        .map_err(|_| "failed to serialize refresh request".to_string())?;
    let stdout = run_backend_sidecar_process(
        app,
        REFRESH_SOURCES_MANUAL_COMMAND,
        &stdin,
        refresh_database_path,
        None,
    )?;
    refresh_sources_manual_result_from_stdout(&stdout)
        .map_err(|_| "backend refresh stdout was not a valid refresh result".to_string())
}

fn run_load_storage_summary_sidecar_process_with_database_path(
    app: &tauri::AppHandle,
    args: &LoadStorageSummaryArgs,
    refresh_database_path: Option<&Path>,
) -> Result<LoadStorageSummaryResult, String> {
    let stdin = load_storage_summary_stdin(args)
        .map_err(|_| "failed to serialize storage summary request".to_string())?;
    let stdout = run_backend_sidecar_process(
        app,
        LOAD_STORAGE_SUMMARY_COMMAND,
        &stdin,
        refresh_database_path,
        None,
    )?;
    load_storage_summary_result_from_stdout(&stdout)
        .map_err(|_| "backend storage summary stdout was not a valid result".to_string())
}

fn run_save_manual_allowance_sidecar_process_with_database_path(
    app: &tauri::AppHandle,
    args: &ManualAllowanceArgs,
    refresh_database_path: Option<&Path>,
) -> Result<ManualAllowanceResult, String> {
    let stdin = save_manual_allowance_stdin(args)
        .map_err(|_| "failed to serialize manual allowance request".to_string())?;
    let stdout = run_backend_sidecar_process(
        app,
        SAVE_MANUAL_ALLOWANCE_WINDOW_COMMAND,
        &stdin,
        refresh_database_path,
        None,
    )?;
    save_manual_allowance_result_from_stdout(&stdout)
        .map_err(|_| "backend manual allowance stdout was not a valid result".to_string())
}

fn run_api_provider_billing_sync_sidecar_process_with_database_path(
    app: &tauri::AppHandle,
    args: &SyncApiProviderBillingArgs,
    refresh_database_path: Option<&Path>,
    openai_admin_key: Option<&str>,
) -> Result<ApiProviderBillingSyncResult, String> {
    let stdin = sync_api_provider_billing_stdin(args)
        .map_err(|_| "failed to serialize API provider billing sync request".to_string())?;
    let stdout = run_backend_sidecar_process(
        app,
        SYNC_API_PROVIDER_BILLING_COMMAND,
        &stdin,
        refresh_database_path,
        openai_admin_key,
    )?;
    api_provider_billing_sync_result_from_stdout(&stdout)
        .map_err(|_| "backend API provider billing sync stdout was not a valid result".to_string())
}

fn run_backend_sidecar_process(
    app: &tauri::AppHandle,
    command_name: &str,
    stdin: &str,
    refresh_database_path: Option<&Path>,
    openai_admin_key: Option<&str>,
) -> Result<String, String> {
    tauri::async_runtime::block_on(async {
        let mut command = app
            .shell()
            .sidecar(BACKEND_SIDECAR_NAME)
            .map_err(|_| "failed to resolve backend sidecar".to_string())?
            .arg(command_name);
        if let Some(path) = refresh_database_path {
            command = command.env(REFRESH_DATABASE_PATH_ENV_VAR, path.as_os_str());
        }
        command = command.env(OPENAI_ADMIN_KEY_ENV_VAR, "");
        if let Some(api_key) = openai_admin_key {
            command = command.env(OPENAI_ADMIN_KEY_ENV_VAR, api_key);
        }

        let (mut rx, mut child) = command
            .spawn()
            .map_err(|_| "failed to start backend sidecar process".to_string())?;
        child
            .write(stdin.as_bytes())
            .map_err(|_| "failed to write backend sidecar stdin".to_string())?;
        drop(child);

        let mut stdout = Vec::new();
        let mut exit_code = None;
        let mut process_error = false;
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(bytes) => {
                    stdout.extend(bytes);
                    stdout.push(b'\n');
                }
                CommandEvent::Stderr(_) => {}
                CommandEvent::Terminated(payload) => {
                    exit_code = payload.code;
                }
                CommandEvent::Error(_) => {
                    process_error = true;
                }
                _ => {}
            }
        }

        if process_error || exit_code != Some(0) {
            return Err("backend sidecar process failed".to_string());
        }

        String::from_utf8(stdout).map_err(|_| "backend sidecar stdout was not utf-8".to_string())
    })
}

fn has_any_refresh_source_root(args: &RefreshSourcesManualArgs) -> bool {
    root_is_present(&args.codex_jsonl_root)
        || root_is_present(&args.claude_code_jsonl_root)
        || root_is_present(&args.gemini_cli_jsonl_root)
}

fn root_is_present(value: &Option<String>) -> bool {
    match value.as_deref() {
        Some(text) => !text.trim().is_empty(),
        None => false,
    }
}

fn invalid_refresh_request(field: &str, message: &str) -> RefreshSourcesManualResult {
    RefreshSourcesManualResult::Error(RefreshCommandErrorPayload {
        error: RefreshCommandError {
            code: "invalid_refresh_request".to_string(),
            message: message.to_string(),
            field: Some(field.to_string()),
        },
    })
}

fn api_provider_billing_sync_error(
    code: &str,
    field: &str,
    message: &str,
) -> ApiProviderBillingSyncResult {
    ApiProviderBillingSyncResult::Error(RefreshCommandErrorPayload {
        error: RefreshCommandError {
            code: code.to_string(),
            message: message.to_string(),
            field: Some(field.to_string()),
        },
    })
}

fn is_verified_api_cost_provider(provider_id: &str) -> bool {
    VERIFIED_API_COST_PROVIDER_IDS.contains(&provider_id)
}

#[tauri::command]
fn source_refresh_summary_sample() -> Value {
    source_refresh_summary_sample_payload()
}

#[tauri::command]
fn refresh_sources_manual(
    app: tauri::AppHandle,
    args: RefreshSourcesManualArgs,
) -> Result<RefreshSourcesManualResult, String> {
    let refresh_database_path = runtime_refresh_database_path(&app)?;
    if should_use_dev_python_backend() {
        return refresh_sources_manual_command(args, &refresh_database_path);
    }
    run_gated_refresh_sources_manual_sidecar_process_with_database_path(
        &app,
        &args,
        Some(&refresh_database_path),
    )
}

fn refresh_sources_manual_command(
    args: RefreshSourcesManualArgs,
    refresh_database_path: &Path,
) -> Result<RefreshSourcesManualResult, String> {
    run_gated_refresh_sources_manual_backend_process_with_database_path(
        &runtime_python_executable(),
        &runtime_workspace_root(),
        &args,
        Some(refresh_database_path),
    )
}

#[tauri::command]
fn load_storage_summary(
    app: tauri::AppHandle,
    args: LoadStorageSummaryArgs,
) -> Result<LoadStorageSummaryResult, String> {
    let refresh_database_path = runtime_refresh_database_path(&app)?;
    if should_use_dev_python_backend() {
        return load_storage_summary_command(args, &refresh_database_path);
    }
    run_load_storage_summary_sidecar_process_with_database_path(
        &app,
        &args,
        Some(&refresh_database_path),
    )
}

fn load_storage_summary_command(
    args: LoadStorageSummaryArgs,
    refresh_database_path: &Path,
) -> Result<LoadStorageSummaryResult, String> {
    run_load_storage_summary_backend_process_with_database_path(
        &runtime_python_executable(),
        &runtime_workspace_root(),
        &args,
        Some(refresh_database_path),
    )
}

#[tauri::command]
fn save_manual_allowance_window(
    app: tauri::AppHandle,
    args: ManualAllowanceArgs,
) -> Result<ManualAllowanceResult, String> {
    let refresh_database_path = runtime_refresh_database_path(&app)?;
    if should_use_dev_python_backend() {
        return save_manual_allowance_command(args, &refresh_database_path);
    }
    run_save_manual_allowance_sidecar_process_with_database_path(
        &app,
        &args,
        Some(&refresh_database_path),
    )
}

fn save_manual_allowance_command(
    args: ManualAllowanceArgs,
    refresh_database_path: &Path,
) -> Result<ManualAllowanceResult, String> {
    run_save_manual_allowance_backend_process_with_database_path(
        &runtime_python_executable(),
        &runtime_workspace_root(),
        &args,
        Some(refresh_database_path),
    )
}

#[tauri::command]
fn load_saved_source_roots(app: tauri::AppHandle) -> Result<SavedSourceRoots, String> {
    let path = runtime_source_roots_path(&app)?;
    load_saved_source_roots_from_path(&path)
}

#[tauri::command]
fn save_source_roots(
    app: tauri::AppHandle,
    args: SavedSourceRoots,
) -> Result<SavedSourceRoots, String> {
    let path = runtime_source_roots_path(&app)?;
    save_source_roots_to_path(&path, &args)
}

#[tauri::command]
fn clear_saved_source_roots(app: tauri::AppHandle) -> Result<SavedSourceRoots, String> {
    let path = runtime_source_roots_path(&app)?;
    clear_saved_source_roots_at_path(&path)?;
    Ok(SavedSourceRoots::default())
}

#[tauri::command]
fn load_api_provider_credentials(
    app: tauri::AppHandle,
) -> Result<ApiProviderCredentialStatuses, String> {
    let path = runtime_api_provider_credentials_path(&app)?;
    load_api_provider_credentials_from_path(&path)
}

#[tauri::command]
fn save_api_provider_credential(
    app: tauri::AppHandle,
    args: SaveApiProviderCredentialArgs,
) -> Result<ApiProviderCredentialStatuses, String> {
    let path = runtime_api_provider_credentials_path(&app)?;
    save_api_provider_credential_to_path(&path, &args)
}

#[tauri::command]
fn remove_api_provider_credential(
    app: tauri::AppHandle,
    args: RemoveApiProviderCredentialArgs,
) -> Result<ApiProviderCredentialStatuses, String> {
    let path = runtime_api_provider_credentials_path(&app)?;
    remove_api_provider_credential_at_path(&path, &args)
}

#[tauri::command]
fn sync_api_provider_billing(
    app: tauri::AppHandle,
    args: SyncApiProviderBillingArgs,
) -> Result<ApiProviderBillingSyncResult, String> {
    let refresh_database_path = runtime_refresh_database_path(&app)?;
    let credential_path = runtime_api_provider_credentials_path(&app)?;
    sync_api_provider_billing_runtime_command(&app, args, &refresh_database_path, &credential_path)
}

fn sync_api_provider_billing_command(
    args: SyncApiProviderBillingArgs,
    refresh_database_path: &Path,
    credential_path: &Path,
) -> Result<ApiProviderBillingSyncResult, String> {
    if let Err(message) = validate_api_provider_id(&args.provider_id) {
        return Ok(api_provider_billing_sync_error(
            "invalid_api_provider_billing_sync_request",
            "provider_id",
            &message,
        ));
    }
    if !is_verified_api_cost_provider(&args.provider_id) {
        return Ok(api_provider_billing_sync_error(
            "api_provider_billing_sync_unavailable",
            "provider_id",
            "Provider billing adapter has not been verified",
        ));
    }

    let api_key = match load_api_provider_credential_from_path(credential_path, &args.provider_id)?
    {
        Some(value) => value,
        None => {
            return Ok(api_provider_billing_sync_error(
                "api_provider_billing_sync_unavailable",
                "credential",
                "OpenAI API provider credential is not configured",
            ));
        }
    };

    run_api_provider_billing_sync_backend_process_with_database_path(
        &runtime_python_executable(),
        &runtime_workspace_root(),
        &args,
        Some(refresh_database_path),
        Some(&api_key),
    )
}

fn sync_api_provider_billing_runtime_command(
    app: &tauri::AppHandle,
    args: SyncApiProviderBillingArgs,
    refresh_database_path: &Path,
    credential_path: &Path,
) -> Result<ApiProviderBillingSyncResult, String> {
    if should_use_dev_python_backend() {
        return sync_api_provider_billing_command(args, refresh_database_path, credential_path);
    }
    if let Err(message) = validate_api_provider_id(&args.provider_id) {
        return Ok(api_provider_billing_sync_error(
            "invalid_api_provider_billing_sync_request",
            "provider_id",
            &message,
        ));
    }
    if !is_verified_api_cost_provider(&args.provider_id) {
        return Ok(api_provider_billing_sync_error(
            "api_provider_billing_sync_unavailable",
            "provider_id",
            "Provider billing adapter has not been verified",
        ));
    }

    let api_key = match load_api_provider_credential_from_path(credential_path, &args.provider_id)?
    {
        Some(value) => value,
        None => {
            return Ok(api_provider_billing_sync_error(
                "api_provider_billing_sync_unavailable",
                "credential",
                "OpenAI API provider credential is not configured",
            ));
        }
    };

    run_api_provider_billing_sync_sidecar_process_with_database_path(
        app,
        &args,
        Some(refresh_database_path),
        Some(&api_key),
    )
}

fn should_use_dev_python_backend() -> bool {
    cfg!(debug_assertions)
        || env::var_os("YTH_PYTHON").is_some()
        || env::var_os("YTH_WORKSPACE_ROOT").is_some()
}

fn runtime_python_executable() -> PathBuf {
    env::var_os("YTH_PYTHON")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("python"))
}

fn runtime_workspace_root() -> PathBuf {
    env::var_os("YTH_WORKSPACE_ROOT")
        .map(PathBuf::from)
        .unwrap_or_else(workspace_root_from_manifest)
}

fn runtime_refresh_database_path(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    let app_data_dir = app
        .path()
        .app_data_dir()
        .map_err(|_| "failed to resolve refresh database directory".to_string())?;
    Ok(refresh_database_path_from_env_or_app_data_dir(
        env::var_os(REFRESH_DATABASE_PATH_ENV_VAR).map(PathBuf::from),
        &app_data_dir,
    ))
}

fn refresh_database_path_from_env_or_app_data_dir(
    env_path: Option<PathBuf>,
    app_data_dir: &Path,
) -> PathBuf {
    env_path.unwrap_or_else(|| refresh_database_path_from_app_data_dir(app_data_dir))
}

fn refresh_database_path_from_app_data_dir(app_data_dir: &Path) -> PathBuf {
    app_data_dir.join(REFRESH_DATABASE_FILE_NAME)
}

fn runtime_source_roots_path(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    let app_data_dir = app
        .path()
        .app_data_dir()
        .map_err(|_| "failed to resolve source roots directory".to_string())?;
    Ok(source_roots_path_from_app_data_dir(&app_data_dir))
}

fn source_roots_path_from_app_data_dir(app_data_dir: &Path) -> PathBuf {
    app_data_dir.join(SOURCE_ROOTS_FILE_NAME)
}

fn runtime_api_provider_credentials_path(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    let app_data_dir = app
        .path()
        .app_data_dir()
        .map_err(|_| "failed to resolve API provider credential directory".to_string())?;
    Ok(api_provider_credentials_path_from_app_data_dir(
        &app_data_dir,
    ))
}

fn api_provider_credentials_path_from_app_data_dir(app_data_dir: &Path) -> PathBuf {
    app_data_dir.join(API_PROVIDER_CREDENTIALS_FILE_NAME)
}

fn refresh_database_parent_dir(path: &Path) -> Option<&Path> {
    path.parent()
        .filter(|parent| !parent.as_os_str().is_empty())
}

fn workspace_root_from_manifest() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(3)
        .expect("src-tauri must live under apps/desktop")
        .to_path_buf()
}

fn protect_secret(secret: &str) -> Result<String, String> {
    platform_protect_secret(secret.as_bytes())
        .map(|bytes| hex_encode(&bytes))
        .map_err(|_| "failed to protect API provider credential".to_string())
}

fn unprotect_secret(protected_secret: &str) -> Result<String, String> {
    let bytes = hex_decode(protected_secret)
        .map_err(|_| "failed to read API provider credential".to_string())?;
    let secret = platform_unprotect_secret(&bytes)
        .map_err(|_| "failed to read API provider credential".to_string())?;
    String::from_utf8(secret).map_err(|_| "failed to read API provider credential".to_string())
}

fn hex_encode(bytes: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut encoded = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        encoded.push(HEX[(byte >> 4) as usize] as char);
        encoded.push(HEX[(byte & 0x0f) as usize] as char);
    }
    encoded
}

fn hex_decode(text: &str) -> Result<Vec<u8>, ()> {
    if text.len() % 2 != 0 {
        return Err(());
    }
    let mut decoded = Vec::with_capacity(text.len() / 2);
    for chunk in text.as_bytes().chunks_exact(2) {
        decoded.push((hex_value(chunk[0])? << 4) | hex_value(chunk[1])?);
    }
    Ok(decoded)
}

fn hex_value(byte: u8) -> Result<u8, ()> {
    match byte {
        b'0'..=b'9' => Ok(byte - b'0'),
        b'a'..=b'f' => Ok(byte - b'a' + 10),
        b'A'..=b'F' => Ok(byte - b'A' + 10),
        _ => Err(()),
    }
}

#[cfg(windows)]
fn platform_protect_secret(secret: &[u8]) -> Result<Vec<u8>, ()> {
    windows_dpapi::protect(secret)
}

#[cfg(windows)]
fn platform_unprotect_secret(protected_secret: &[u8]) -> Result<Vec<u8>, ()> {
    windows_dpapi::unprotect(protected_secret)
}

#[cfg(not(windows))]
fn platform_protect_secret(_secret: &[u8]) -> Result<Vec<u8>, ()> {
    Err(())
}

#[cfg(not(windows))]
fn platform_unprotect_secret(_protected_secret: &[u8]) -> Result<Vec<u8>, ()> {
    Err(())
}

#[cfg(windows)]
mod windows_dpapi {
    use std::{ffi::c_void, ptr, slice};

    #[repr(C)]
    struct DataBlob {
        cb_data: u32,
        pb_data: *mut u8,
    }

    #[link(name = "Crypt32")]
    extern "system" {
        #[link_name = "CryptProtectData"]
        fn crypt_protect_data(
            data_in: *mut DataBlob,
            data_description: *const u16,
            optional_entropy: *mut DataBlob,
            reserved: *mut c_void,
            prompt_struct: *mut c_void,
            flags: u32,
            data_out: *mut DataBlob,
        ) -> i32;

        #[link_name = "CryptUnprotectData"]
        fn crypt_unprotect_data(
            data_in: *mut DataBlob,
            data_description: *mut *mut u16,
            optional_entropy: *mut DataBlob,
            reserved: *mut c_void,
            prompt_struct: *mut c_void,
            flags: u32,
            data_out: *mut DataBlob,
        ) -> i32;
    }

    #[link(name = "Kernel32")]
    extern "system" {
        #[link_name = "LocalFree"]
        fn local_free(memory: *mut c_void) -> *mut c_void;
    }

    pub fn protect(secret: &[u8]) -> Result<Vec<u8>, ()> {
        let mut input = secret.to_vec();
        let mut input_blob = DataBlob {
            cb_data: input.len() as u32,
            pb_data: input.as_mut_ptr(),
        };
        let mut output_blob = DataBlob {
            cb_data: 0,
            pb_data: ptr::null_mut(),
        };

        let ok = unsafe {
            crypt_protect_data(
                &mut input_blob,
                ptr::null(),
                ptr::null_mut(),
                ptr::null_mut(),
                ptr::null_mut(),
                0,
                &mut output_blob,
            )
        };
        copy_and_free_blob(ok, output_blob)
    }

    pub fn unprotect(protected_secret: &[u8]) -> Result<Vec<u8>, ()> {
        let mut input = protected_secret.to_vec();
        let mut input_blob = DataBlob {
            cb_data: input.len() as u32,
            pb_data: input.as_mut_ptr(),
        };
        let mut output_blob = DataBlob {
            cb_data: 0,
            pb_data: ptr::null_mut(),
        };

        let ok = unsafe {
            crypt_unprotect_data(
                &mut input_blob,
                ptr::null_mut(),
                ptr::null_mut(),
                ptr::null_mut(),
                ptr::null_mut(),
                0,
                &mut output_blob,
            )
        };
        copy_and_free_blob(ok, output_blob)
    }

    fn copy_and_free_blob(ok: i32, output_blob: DataBlob) -> Result<Vec<u8>, ()> {
        if ok == 0 || output_blob.pb_data.is_null() {
            return Err(());
        }
        let bytes =
            unsafe { slice::from_raw_parts(output_blob.pb_data, output_blob.cb_data as usize) }
                .to_vec();
        unsafe {
            local_free(output_blob.pb_data.cast::<c_void>());
        }
        Ok(bytes)
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            source_refresh_summary_sample,
            refresh_sources_manual,
            load_storage_summary,
            save_manual_allowance_window,
            load_saved_source_roots,
            save_source_roots,
            clear_saved_source_roots,
            load_api_provider_credentials,
            save_api_provider_credential,
            remove_api_provider_credential,
            sync_api_provider_billing
        ])
        .run(tauri::generate_context!())
        .expect("error while running YourTokenHelper");
}

#[cfg(test)]
mod tests {
    use super::{
        api_provider_billing_sync_result_from_stdout,
        api_provider_credentials_path_from_app_data_dir,
        backend_api_provider_billing_sync_process_module_args,
        backend_load_storage_summary_process_module_args,
        backend_manual_allowance_process_module_args, backend_refresh_process_module_args,
        clear_saved_source_roots_at_path, load_api_provider_credential_from_path,
        load_api_provider_credentials_from_path, load_saved_source_roots_from_path,
        load_storage_summary_command, load_storage_summary_result_from_stdout,
        load_storage_summary_stdin, normalize_saved_source_roots, refresh_database_parent_dir,
        refresh_database_path_from_app_data_dir, refresh_database_path_from_env_or_app_data_dir,
        refresh_sources_manual_command, refresh_sources_manual_result_from_stdout,
        refresh_sources_manual_stdin, remove_api_provider_credential_at_path,
        run_api_provider_billing_sync_backend_process_with_database_path,
        run_gated_refresh_sources_manual_backend_process,
        run_gated_refresh_sources_manual_backend_process_with_database_path,
        run_load_storage_summary_backend_process_with_database_path,
        run_refresh_sources_manual_backend_process,
        run_refresh_sources_manual_backend_process_with_database_path,
        run_save_manual_allowance_backend_process_with_database_path,
        save_api_provider_credential_to_path, save_manual_allowance_command,
        save_manual_allowance_result_from_stdout, save_manual_allowance_stdin,
        save_source_roots_to_path, source_refresh_error_sample_payload,
        source_refresh_summary_sample_payload, source_roots_path_from_app_data_dir,
        sync_api_provider_billing_command, sync_api_provider_billing_stdin,
        workspace_root_from_manifest, ApiProviderBillingSyncResult, LoadStorageSummaryArgs,
        LoadStorageSummaryResult, ManualAllowanceArgs, ManualAllowanceResult,
        RefreshSourcesManualArgs, RefreshSourcesManualResult, RemoveApiProviderCredentialArgs,
        SaveApiProviderCredentialArgs, SavedSourceRoots, SyncApiProviderBillingArgs,
        API_PROVIDER_CREDENTIALS_FILE_NAME, BACKEND_API_PROVIDER_BILLING_SYNC_COMMAND_MODULE,
        BACKEND_LOAD_STORAGE_SUMMARY_COMMAND_MODULE, BACKEND_MANUAL_ALLOWANCE_COMMAND_MODULE,
        BACKEND_REFRESH_COMMAND_MODULE, CLEAR_SAVED_SOURCE_ROOTS_COMMAND,
        DEFAULT_AUTO_REFRESH_INTERVAL_MINUTES, LOAD_API_PROVIDER_CREDENTIALS_COMMAND,
        LOAD_SAVED_SOURCE_ROOTS_COMMAND, LOAD_STORAGE_SUMMARY_COMMAND, OPENAI_ADMIN_KEY_ENV_VAR,
        REFRESH_DATABASE_FILE_NAME, REFRESH_DATABASE_PATH_ENV_VAR, REFRESH_SOURCES_MANUAL_COMMAND,
        REMOVE_API_PROVIDER_CREDENTIAL_COMMAND, SAVE_API_PROVIDER_CREDENTIAL_COMMAND,
        SAVE_MANUAL_ALLOWANCE_WINDOW_COMMAND, SAVE_SOURCE_ROOTS_COMMAND,
        SOURCE_REFRESH_SUMMARY_SAMPLE_COMMAND, SOURCE_ROOTS_FILE_NAME,
        SYNC_API_PROVIDER_BILLING_COMMAND,
    };
    use serde_json::json;
    use std::{
        env, fs,
        path::{Path, PathBuf},
        process,
        time::{SystemTime, UNIX_EPOCH},
    };

    #[test]
    fn source_refresh_command_names_match_desktop_contract() {
        assert_eq!(
            SOURCE_REFRESH_SUMMARY_SAMPLE_COMMAND,
            "source_refresh_summary_sample"
        );
        assert_eq!(REFRESH_SOURCES_MANUAL_COMMAND, "refresh_sources_manual");
        assert_eq!(LOAD_STORAGE_SUMMARY_COMMAND, "load_storage_summary");
        assert_eq!(
            SAVE_MANUAL_ALLOWANCE_WINDOW_COMMAND,
            "save_manual_allowance_window"
        );
        assert_eq!(LOAD_SAVED_SOURCE_ROOTS_COMMAND, "load_saved_source_roots");
        assert_eq!(SAVE_SOURCE_ROOTS_COMMAND, "save_source_roots");
        assert_eq!(CLEAR_SAVED_SOURCE_ROOTS_COMMAND, "clear_saved_source_roots");
        assert_eq!(
            LOAD_API_PROVIDER_CREDENTIALS_COMMAND,
            "load_api_provider_credentials"
        );
        assert_eq!(
            SAVE_API_PROVIDER_CREDENTIAL_COMMAND,
            "save_api_provider_credential"
        );
        assert_eq!(
            REMOVE_API_PROVIDER_CREDENTIAL_COMMAND,
            "remove_api_provider_credential"
        );
        assert_eq!(
            SYNC_API_PROVIDER_BILLING_COMMAND,
            "sync_api_provider_billing"
        );
        assert_ne!(
            REFRESH_SOURCES_MANUAL_COMMAND,
            SOURCE_REFRESH_SUMMARY_SAMPLE_COMMAND
        );
        assert_ne!(
            LOAD_STORAGE_SUMMARY_COMMAND,
            SOURCE_REFRESH_SUMMARY_SAMPLE_COMMAND
        );
        assert_ne!(LOAD_STORAGE_SUMMARY_COMMAND, REFRESH_SOURCES_MANUAL_COMMAND);
        assert_ne!(
            SAVE_MANUAL_ALLOWANCE_WINDOW_COMMAND,
            SOURCE_REFRESH_SUMMARY_SAMPLE_COMMAND
        );
        assert_ne!(
            SAVE_MANUAL_ALLOWANCE_WINDOW_COMMAND,
            REFRESH_SOURCES_MANUAL_COMMAND
        );
        assert_ne!(SAVE_SOURCE_ROOTS_COMMAND, REFRESH_SOURCES_MANUAL_COMMAND);
        assert_ne!(
            SAVE_API_PROVIDER_CREDENTIAL_COMMAND,
            REFRESH_SOURCES_MANUAL_COMMAND
        );
        assert_ne!(
            SYNC_API_PROVIDER_BILLING_COMMAND,
            REFRESH_SOURCES_MANUAL_COMMAND
        );
    }

    #[test]
    fn backend_refresh_process_module_args_point_to_cli_boundary() {
        let args = backend_refresh_process_module_args();

        assert_eq!(
            BACKEND_REFRESH_COMMAND_MODULE,
            "backend.sources.refresh_command_cli"
        );
        assert_eq!(args, ["-m", "backend.sources.refresh_command_cli"]);
        assert!(!args.contains(&SOURCE_REFRESH_SUMMARY_SAMPLE_COMMAND));
        assert!(!args.contains(&REFRESH_SOURCES_MANUAL_COMMAND));
    }

    #[test]
    fn backend_load_storage_summary_process_module_args_point_to_cli_boundary() {
        let args = backend_load_storage_summary_process_module_args();

        assert_eq!(
            BACKEND_LOAD_STORAGE_SUMMARY_COMMAND_MODULE,
            "backend.storage.summary_command_cli"
        );
        assert_eq!(args, ["-m", "backend.storage.summary_command_cli"]);
        assert!(!args.contains(&SOURCE_REFRESH_SUMMARY_SAMPLE_COMMAND));
        assert!(!args.contains(&REFRESH_SOURCES_MANUAL_COMMAND));
    }

    #[test]
    fn backend_manual_allowance_process_module_args_point_to_cli_boundary() {
        let args = backend_manual_allowance_process_module_args();

        assert_eq!(
            BACKEND_MANUAL_ALLOWANCE_COMMAND_MODULE,
            "backend.sources.manual_allowance_command_cli"
        );
        assert_eq!(args, ["-m", "backend.sources.manual_allowance_command_cli"]);
        assert!(!args.contains(&SOURCE_REFRESH_SUMMARY_SAMPLE_COMMAND));
        assert!(!args.contains(&REFRESH_SOURCES_MANUAL_COMMAND));
    }

    #[test]
    fn backend_api_provider_billing_sync_process_module_args_point_to_cli_boundary() {
        let args = backend_api_provider_billing_sync_process_module_args();

        assert_eq!(
            BACKEND_API_PROVIDER_BILLING_SYNC_COMMAND_MODULE,
            "backend.sources.api_provider_billing_sync_command_cli"
        );
        assert_eq!(
            args,
            [
                "-m",
                "backend.sources.api_provider_billing_sync_command_cli"
            ]
        );
        assert!(!args.contains(&SOURCE_REFRESH_SUMMARY_SAMPLE_COMMAND));
        assert!(!args.contains(&SYNC_API_PROVIDER_BILLING_COMMAND));
    }

    #[test]
    fn refresh_sources_manual_args_match_backend_boundary_names() {
        let args: RefreshSourcesManualArgs = serde_json::from_value(json!({
            "end_day_utc": "2026-06-14",
            "started_at": "2026-06-14T00:00:00Z"
        }))
        .unwrap();
        let serialized = serde_json::to_value(&args).unwrap();

        assert_eq!(args.end_day_utc, "2026-06-14");
        assert_eq!(args.started_at.as_deref(), Some("2026-06-14T00:00:00Z"));
        assert_eq!(serialized["end_day_utc"], "2026-06-14");
        assert_eq!(serialized["started_at"], "2026-06-14T00:00:00Z");
        assert!(serialized.get("codex_jsonl_root").is_none());
        assert!(serialized.get("claude_code_jsonl_root").is_none());
        assert!(serialized.get("gemini_cli_jsonl_root").is_none());
    }

    #[test]
    fn refresh_sources_manual_args_keep_roots_explicit() {
        let args: RefreshSourcesManualArgs = serde_json::from_value(json!({
            "end_day_utc": "2026-06-14",
            "codex_jsonl_root": "synthetic-codex-root",
            "claude_code_jsonl_root": "synthetic-claude-root",
            "gemini_cli_jsonl_root": "synthetic-gemini-root"
        }))
        .unwrap();
        let text = serde_json::to_string(&args).unwrap();

        assert_eq!(
            args.codex_jsonl_root.as_deref(),
            Some("synthetic-codex-root")
        );
        assert_eq!(
            args.claude_code_jsonl_root.as_deref(),
            Some("synthetic-claude-root")
        );
        assert_eq!(
            args.gemini_cli_jsonl_root.as_deref(),
            Some("synthetic-gemini-root")
        );
        assert!(text.contains("codex_jsonl_root"));
        assert!(text.contains("claude_code_jsonl_root"));
        assert!(text.contains("gemini_cli_jsonl_root"));
        assert!(!text.contains("auto_discover"));
    }

    #[test]
    fn refresh_sources_manual_args_reject_unsupported_source_roots() {
        let cursor_result = serde_json::from_value::<RefreshSourcesManualArgs>(json!({
            "end_day_utc": "2026-06-14",
            "cursor_jsonl_root": "synthetic-cursor-root"
        }));
        let copilot_result = serde_json::from_value::<RefreshSourcesManualArgs>(json!({
            "end_day_utc": "2026-06-14",
            "github_copilot_jsonl_root": "synthetic-copilot-root"
        }));

        assert!(cursor_result.is_err());
        assert!(copilot_result.is_err());
    }

    #[test]
    fn refresh_sources_manual_stdin_serializes_only_explicit_args() {
        let args = RefreshSourcesManualArgs {
            end_day_utc: "2026-06-14".to_string(),
            codex_jsonl_root: Some("synthetic-codex-root".to_string()),
            claude_code_jsonl_root: None,
            gemini_cli_jsonl_root: Some("synthetic-gemini-root".to_string()),
            started_at: Some("2026-06-14T00:00:00Z".to_string()),
        };
        let text = refresh_sources_manual_stdin(&args).unwrap();

        assert!(text.contains("\"end_day_utc\":\"2026-06-14\""));
        assert!(text.contains("\"codex_jsonl_root\":\"synthetic-codex-root\""));
        assert!(text.contains("\"gemini_cli_jsonl_root\":\"synthetic-gemini-root\""));
        assert!(text.contains("\"started_at\":\"2026-06-14T00:00:00Z\""));
        assert!(!text.contains("claude_code_jsonl_root"));
        assert!(!text.contains("auto_discover"));
        assert!(!text.contains("source_refresh_summary_sample"));
    }

    #[test]
    fn refresh_sources_manual_args_reject_implicit_discovery_fields() {
        let result = serde_json::from_value::<RefreshSourcesManualArgs>(json!({
            "end_day_utc": "2026-06-14",
            "auto_discover": true
        }));

        assert!(result.is_err());
    }

    #[test]
    fn load_storage_summary_args_reject_database_path_fields() {
        let result = serde_json::from_value::<LoadStorageSummaryArgs>(json!({
            "end_day_utc": "2026-06-14",
            "database_path": "synthetic.sqlite"
        }));

        assert!(result.is_err());
    }

    #[test]
    fn manual_allowance_args_match_backend_boundary_names() {
        let args: ManualAllowanceArgs = serde_json::from_value(json!({
            "end_day_utc": "2026-06-14",
            "source_kind": "codex",
            "unit": "tokens",
            "limit_amount": 100000,
            "remaining_amount": 97460,
            "reset_at": "2026-06-21T00:00:00Z"
        }))
        .unwrap();
        let serialized = serde_json::to_value(&args).unwrap();

        assert_eq!(args.end_day_utc, "2026-06-14");
        assert_eq!(args.source_kind, "codex");
        assert_eq!(args.unit.as_deref(), Some("tokens"));
        assert_eq!(args.limit_amount, 100000.0);
        assert_eq!(args.remaining_amount, Some(97460.0));
        assert_eq!(args.reset_at.as_deref(), Some("2026-06-21T00:00:00Z"));
        assert_eq!(serialized["end_day_utc"], "2026-06-14");
        assert_eq!(serialized["source_kind"], "codex");
        assert_eq!(serialized["limit_amount"], 100000.0);
        assert!(serialized.get("used_amount").is_none());
        assert!(serialized.get("window_start").is_none());
        assert!(serialized.get("database_path").is_none());
        assert!(serialized.get("source_id").is_none());
        assert!(serialized.get("note").is_none());
    }

    #[test]
    fn manual_allowance_args_reject_untrusted_fields() {
        for field in ["database_path", "source_id", "note", "raw_payload"] {
            let mut value = json!({
                "end_day_utc": "2026-06-14",
                "source_kind": "codex",
                "limit_amount": 100000
            });
            value[field] = json!("C:/Users/example/secret");
            let result = serde_json::from_value::<ManualAllowanceArgs>(value);

            assert!(result.is_err());
        }
    }

    #[test]
    fn api_provider_billing_sync_args_match_backend_boundary_names() {
        let args: SyncApiProviderBillingArgs = serde_json::from_value(json!({
            "provider_id": "openai_api_cost",
            "end_day_utc": "2026-06-14",
            "started_at": "2026-06-14T00:00:00Z"
        }))
        .unwrap();
        let serialized = serde_json::to_value(&args).unwrap();

        assert_eq!(args.provider_id, "openai_api_cost");
        assert_eq!(args.end_day_utc, "2026-06-14");
        assert_eq!(args.started_at.as_deref(), Some("2026-06-14T00:00:00Z"));
        assert_eq!(serialized["provider_id"], "openai_api_cost");
        assert_eq!(serialized["end_day_utc"], "2026-06-14");
        assert!(serialized.get("api_key").is_none());
        assert!(serialized.get("database_path").is_none());
        assert!(serialized.get("payload").is_none());
    }

    #[test]
    fn api_provider_billing_sync_args_reject_key_material_fields() {
        for field in ["api_key", "database_path", "payload", "source_path"] {
            let mut value = json!({
                "provider_id": "openai_api_cost",
                "end_day_utc": "2026-06-14"
            });
            value[field] = json!("C:/Users/example/secret");
            let result = serde_json::from_value::<SyncApiProviderBillingArgs>(value);

            assert!(result.is_err());
        }
    }

    #[test]
    fn sync_api_provider_billing_stdin_serializes_without_api_key() {
        let args = SyncApiProviderBillingArgs {
            provider_id: "openai_api_cost".to_string(),
            end_day_utc: "2026-06-14".to_string(),
            started_at: Some("2026-06-14T00:00:00Z".to_string()),
        };
        let text = sync_api_provider_billing_stdin(&args).unwrap();

        assert!(text.contains("\"provider_id\":\"openai_api_cost\""));
        assert!(text.contains("\"end_day_utc\":\"2026-06-14\""));
        assert!(text.contains("\"started_at\":\"2026-06-14T00:00:00Z\""));
        assert!(!text.contains("api_key"));
        assert!(!text.contains(OPENAI_ADMIN_KEY_ENV_VAR));
        assert!(!text.contains("database_path"));
    }

    #[test]
    fn api_provider_billing_sync_result_from_stdout_accepts_success_and_error() {
        let success = api_provider_billing_sync_result_from_stdout(
            "{\"sync_result\":{\"status\":\"ready\"},\"storage_summary\":{}}\n",
        )
        .unwrap();
        let error = api_provider_billing_sync_result_from_stdout(
            "{\"error\":{\"code\":\"api_provider_billing_sync_unavailable\",\"message\":\"missing\"}}\n",
        )
        .unwrap();

        match success {
            ApiProviderBillingSyncResult::Success(payload) => {
                assert_eq!(payload["sync_result"]["status"], "ready");
            }
            ApiProviderBillingSyncResult::Error(_) => panic!("expected success payload"),
        }
        match error {
            ApiProviderBillingSyncResult::Error(payload) => {
                assert_eq!(payload.error.code, "api_provider_billing_sync_unavailable");
            }
            ApiProviderBillingSyncResult::Success(_) => panic!("expected error payload"),
        }
    }

    #[test]
    fn save_manual_allowance_stdin_serializes_only_structured_args() {
        let args = ManualAllowanceArgs {
            end_day_utc: "2026-06-14".to_string(),
            source_kind: "codex".to_string(),
            unit: Some("tokens".to_string()),
            limit_amount: 100000.0,
            used_amount: None,
            remaining_amount: Some(97460.0),
            window_start: None,
            window_end: None,
            reset_at: Some("2026-06-21T00:00:00Z".to_string()),
        };
        let text = save_manual_allowance_stdin(&args).unwrap();

        assert!(text.contains("\"end_day_utc\":\"2026-06-14\""));
        assert!(text.contains("\"source_kind\":\"codex\""));
        assert!(text.contains("\"limit_amount\":100000.0"));
        assert!(text.contains("\"remaining_amount\":97460.0"));
        assert!(!text.contains("database_path"));
        assert!(!text.contains("source_id"));
        assert!(!text.contains("note"));
        assert!(!text.contains(REFRESH_DATABASE_PATH_ENV_VAR));
    }

    #[test]
    fn load_storage_summary_stdin_serializes_only_end_day() {
        let args = LoadStorageSummaryArgs {
            end_day_utc: "2026-06-14".to_string(),
        };

        let text = load_storage_summary_stdin(&args).unwrap();

        assert_eq!(text, "{\"end_day_utc\":\"2026-06-14\"}");
        assert!(!text.contains("database_path"));
        assert!(!text.contains(REFRESH_DATABASE_PATH_ENV_VAR));
    }

    #[test]
    fn refresh_sources_manual_result_accepts_success_payload() {
        let result: RefreshSourcesManualResult =
            serde_json::from_value(source_refresh_summary_sample_payload()).unwrap();

        match result {
            RefreshSourcesManualResult::Success(payload) => {
                assert!(payload.get("error").is_none());
                assert_eq!(
                    payload["storage_summary"]["summary"]["totals"]["total_tokens"],
                    17040
                );
            }
            RefreshSourcesManualResult::Error(_) => {
                panic!("expected success payload");
            }
        }
    }

    #[test]
    fn refresh_sources_manual_result_parses_success_stdout() {
        let stdout = format!("{}\n", source_refresh_summary_sample_payload());
        let result = refresh_sources_manual_result_from_stdout(&stdout).unwrap();

        match result {
            RefreshSourcesManualResult::Success(payload) => {
                assert_eq!(
                    payload["storage_summary"]["summary"]["totals"]["total_tokens"],
                    17040
                );
            }
            RefreshSourcesManualResult::Error(_) => {
                panic!("expected success stdout");
            }
        }
    }

    #[test]
    fn load_storage_summary_result_parses_success_stdout() {
        let storage_summary = source_refresh_summary_sample_payload()["storage_summary"].clone();
        let stdout = format!("{storage_summary}\n");
        let result = load_storage_summary_result_from_stdout(&stdout).unwrap();

        match result {
            LoadStorageSummaryResult::Success(payload) => {
                assert!(payload.get("error").is_none());
                assert_eq!(payload["summary"]["totals"]["total_tokens"], 17040);
                assert!(payload.get("refresh_results").is_none());
            }
            LoadStorageSummaryResult::Error(_) => {
                panic!("expected storage summary success payload");
            }
        }
    }

    #[test]
    fn save_manual_allowance_result_parses_success_stdout() {
        let payload = json!({
            "allowance_window": {
                "limit_amount": 100000,
                "source_id": "codex:manual_allowance",
                "source_kind": "codex",
                "status": "manual",
                "unit": "tokens"
            },
            "storage_summary": {
                "allowance_windows": [],
                "generated_from": "backend.sources.manual_allowance_commands",
                "privacy": {
                    "stores_prompt_content": false,
                    "stores_response_content": false,
                    "stores_tool_output": false,
                    "synthetic": false
                },
                "refresh_state": {
                    "attempted_source_count": 0,
                    "events_seen": 0,
                    "last_attempt_at": null,
                    "last_status": "never_refreshed",
                    "last_success_at": null,
                    "successful_source_count": 0
                },
                "schema_version": 1,
                "source_states": [],
                "summary": {
                    "by_day": {},
                    "by_day_source": {},
                    "by_source": {},
                    "event_count": 0,
                    "rolling_7d": {
                        "totals": {
                            "cached_input_tokens": 0,
                            "input_tokens": 0,
                            "output_tokens": 0,
                            "reasoning_output_tokens": 0,
                            "total_tokens": 0
                        },
                        "window_end": null,
                        "window_start": null
                    },
                    "totals": {
                        "cached_input_tokens": 0,
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "reasoning_output_tokens": 0,
                        "total_tokens": 0
                    }
                }
            }
        });
        let stdout = format!("{payload}\n");
        let result = save_manual_allowance_result_from_stdout(&stdout).unwrap();

        match result {
            ManualAllowanceResult::Success(payload) => {
                assert_eq!(
                    payload["allowance_window"]["source_id"],
                    "codex:manual_allowance"
                );
                assert_eq!(payload["allowance_window"]["status"], "manual");
            }
            ManualAllowanceResult::Error(_) => {
                panic!("expected manual allowance success payload");
            }
        }
    }

    #[test]
    fn save_manual_allowance_result_parses_structured_error_stdout() {
        let stdout = "{\"error\":{\"code\":\"invalid_manual_allowance_request\",\"field\":\"limit_amount\",\"message\":\"limit_amount must be positive\"}}\n";
        let result = save_manual_allowance_result_from_stdout(stdout).unwrap();

        match result {
            ManualAllowanceResult::Error(payload) => {
                assert_eq!(payload.error.code, "invalid_manual_allowance_request");
                assert_eq!(payload.error.field.as_deref(), Some("limit_amount"));
            }
            ManualAllowanceResult::Success(_) => {
                panic!("expected manual allowance error payload");
            }
        }
    }

    #[test]
    fn refresh_sources_manual_result_accepts_structured_error_payload() {
        let result: RefreshSourcesManualResult =
            serde_json::from_value(source_refresh_error_sample_payload()).unwrap();

        match result {
            RefreshSourcesManualResult::Error(payload) => {
                assert_eq!(payload.error.code, "invalid_refresh_request");
                assert_eq!(payload.error.field.as_deref(), Some("end_day_utc"));
                assert_eq!(payload.error.message, "end_day_utc must be YYYY-MM-DD");
            }
            RefreshSourcesManualResult::Success(_) => {
                panic!("expected structured error payload");
            }
        }
    }

    #[test]
    fn refresh_sources_manual_result_parses_structured_error_stdout() {
        let stdout = format!("{}\n", source_refresh_error_sample_payload());
        let result = refresh_sources_manual_result_from_stdout(&stdout).unwrap();

        match result {
            RefreshSourcesManualResult::Error(payload) => {
                assert_eq!(payload.error.code, "invalid_refresh_request");
                assert_eq!(payload.error.field.as_deref(), Some("end_day_utc"));
            }
            RefreshSourcesManualResult::Success(_) => {
                panic!("expected error stdout");
            }
        }
    }

    #[test]
    fn load_storage_summary_result_parses_structured_error_stdout() {
        let stdout = "{\"error\":{\"code\":\"storage_summary_unavailable\",\"field\":\"database_path\",\"message\":\"storage summary database is unavailable\"}}\n";
        let result = load_storage_summary_result_from_stdout(stdout).unwrap();

        match result {
            LoadStorageSummaryResult::Error(payload) => {
                assert_eq!(payload.error.code, "storage_summary_unavailable");
                assert_eq!(payload.error.field.as_deref(), Some("database_path"));
            }
            LoadStorageSummaryResult::Success(_) => {
                panic!("expected storage summary error payload");
            }
        }
    }

    #[test]
    fn refresh_sources_manual_backend_process_returns_fixture_success() {
        let workspace_root = workspace_root_for_tests();
        let fixture_root = workspace_root.join("experiments/fixtures/local_sources");
        let args = RefreshSourcesManualArgs {
            end_day_utc: "2026-06-14".to_string(),
            codex_jsonl_root: Some(path_text(&fixture_root.join("codex"))),
            claude_code_jsonl_root: Some(path_text(&fixture_root.join("claude_code"))),
            gemini_cli_jsonl_root: None,
            started_at: Some("2026-06-14T00:00:00Z".to_string()),
        };

        let result = run_refresh_sources_manual_backend_process(
            &python_executable_for_tests(),
            &workspace_root,
            &args,
        )
        .unwrap();
        let text = serde_json::to_string(&result).unwrap();

        match result {
            RefreshSourcesManualResult::Success(payload) => {
                assert_eq!(payload["refresh_results"].as_array().unwrap().len(), 5);
                assert_eq!(payload["refresh_results"][0]["events_seen"], 2);
                assert_eq!(payload["refresh_results"][1]["events_seen"], 2);
                assert_eq!(
                    payload["storage_summary"]["summary"]["totals"]["total_tokens"],
                    7570
                );
            }
            RefreshSourcesManualResult::Error(_) => {
                panic!("expected backend process success");
            }
        }
        assert!(!text.contains("experiments/fixtures"));
        assert!(!text.contains("local_sources"));
        assert!(!text.contains("sessions"));
        assert!(!text.contains("projects"));
    }

    #[test]
    fn refresh_sources_manual_backend_process_uses_file_backed_database_path() {
        let workspace_root = workspace_root_for_tests();
        let fixture_root = workspace_root.join("experiments/fixtures/local_sources");
        let database_path = refresh_database_path_for_tests("file-backed-refresh");
        let args = RefreshSourcesManualArgs {
            end_day_utc: "2026-06-14".to_string(),
            codex_jsonl_root: Some(path_text(&fixture_root.join("codex"))),
            claude_code_jsonl_root: Some(path_text(&fixture_root.join("claude_code"))),
            gemini_cli_jsonl_root: None,
            started_at: Some("2026-06-14T00:00:00Z".to_string()),
        };

        let first_result = run_refresh_sources_manual_backend_process_with_database_path(
            &python_executable_for_tests(),
            &workspace_root,
            &args,
            Some(&database_path),
        )
        .unwrap();
        assert!(database_path.exists());

        let second_result = run_refresh_sources_manual_backend_process_with_database_path(
            &python_executable_for_tests(),
            &workspace_root,
            &RefreshSourcesManualArgs {
                end_day_utc: "2026-06-14".to_string(),
                codex_jsonl_root: None,
                claude_code_jsonl_root: None,
                gemini_cli_jsonl_root: None,
                started_at: Some("2026-06-14T00:10:00Z".to_string()),
            },
            Some(&database_path),
        )
        .unwrap();
        let text = serde_json::to_string(&second_result).unwrap();

        match (first_result, second_result) {
            (
                RefreshSourcesManualResult::Success(first_payload),
                RefreshSourcesManualResult::Success(second_payload),
            ) => {
                assert_eq!(
                    first_payload["storage_summary"]["summary"]["totals"]["total_tokens"],
                    7570
                );
                assert_eq!(
                    second_payload["storage_summary"]["summary"]["totals"]["total_tokens"],
                    7570
                );
                assert_eq!(second_payload["refresh_results"][0]["events_seen"], 0);
            }
            _ => {
                panic!("expected file-backed backend process successes");
            }
        }
        assert!(!text.contains(&path_text(&database_path)));
        assert!(!text.contains(REFRESH_DATABASE_PATH_ENV_VAR));
    }

    #[test]
    fn save_manual_allowance_backend_process_uses_file_backed_database_path() {
        let workspace_root = workspace_root_for_tests();
        let database_path = refresh_database_path_for_tests("file-backed-manual-allowance");
        let args = ManualAllowanceArgs {
            end_day_utc: "2026-06-14".to_string(),
            source_kind: "codex".to_string(),
            unit: Some("tokens".to_string()),
            limit_amount: 100000.0,
            used_amount: None,
            remaining_amount: Some(97460.0),
            window_start: None,
            window_end: None,
            reset_at: Some("2026-06-21T00:00:00Z".to_string()),
        };

        let save_result = run_save_manual_allowance_backend_process_with_database_path(
            &python_executable_for_tests(),
            &workspace_root,
            &args,
            Some(&database_path),
        )
        .unwrap();
        let save_text = serde_json::to_string(&save_result).unwrap();
        assert!(database_path.exists());

        match save_result {
            ManualAllowanceResult::Success(payload) => {
                assert_eq!(
                    payload["allowance_window"]["source_id"],
                    "codex:manual_allowance"
                );
                assert_eq!(
                    payload["storage_summary"]["allowance_windows"][0]["remaining_amount"],
                    97460.0
                );
            }
            ManualAllowanceResult::Error(_) => {
                panic!("expected manual allowance save success");
            }
        }
        assert!(!save_text.contains(&path_text(&database_path)));
        assert!(!save_text.contains(REFRESH_DATABASE_PATH_ENV_VAR));

        let load_result = load_storage_summary_command(
            LoadStorageSummaryArgs {
                end_day_utc: "2026-06-14".to_string(),
            },
            &database_path,
        )
        .unwrap();

        match load_result {
            LoadStorageSummaryResult::Success(payload) => {
                assert_eq!(
                    payload["allowance_windows"][0]["source_id"],
                    "codex:manual_allowance"
                );
                assert_eq!(payload["allowance_windows"][0]["status"], "manual");
            }
            LoadStorageSummaryResult::Error(_) => {
                panic!("expected storage summary with manual allowance");
            }
        }
    }

    #[test]
    fn save_manual_allowance_command_returns_redacted_backend_errors() {
        let database_path = refresh_database_path_for_tests("command-manual-allowance-error");
        let result = save_manual_allowance_command(
            ManualAllowanceArgs {
                end_day_utc: "2026-06-14".to_string(),
                source_kind: "C:/Users/example/secret/codex".to_string(),
                unit: Some("tokens".to_string()),
                limit_amount: 100000.0,
                used_amount: None,
                remaining_amount: None,
                window_start: None,
                window_end: None,
                reset_at: None,
            },
            &database_path,
        )
        .unwrap();
        let text = serde_json::to_string(&result).unwrap();

        match result {
            ManualAllowanceResult::Error(payload) => {
                assert_eq!(payload.error.code, "invalid_manual_allowance_request");
                assert_eq!(payload.error.field.as_deref(), Some("source_kind"));
                assert_eq!(payload.error.message, "unknown source_kind");
            }
            ManualAllowanceResult::Success(_) => {
                panic!("expected manual allowance error");
            }
        }
        assert!(!text.contains("C:/Users"));
        assert!(!text.contains("secret"));
        assert!(!text.contains(&path_text(&database_path)));
    }

    #[test]
    fn load_storage_summary_backend_process_missing_database_is_unavailable() {
        let workspace_root = workspace_root_for_tests();
        let database_path = refresh_database_path_for_tests("missing-load-summary");
        let result = run_load_storage_summary_backend_process_with_database_path(
            &python_executable_for_tests(),
            &workspace_root,
            &LoadStorageSummaryArgs {
                end_day_utc: "2026-06-14".to_string(),
            },
            Some(&database_path),
        )
        .unwrap();
        let text = serde_json::to_string(&result).unwrap();

        match result {
            LoadStorageSummaryResult::Error(payload) => {
                assert_eq!(payload.error.code, "storage_summary_unavailable");
                assert_eq!(payload.error.field.as_deref(), Some("database_path"));
            }
            LoadStorageSummaryResult::Success(_) => {
                panic!("expected missing storage summary error");
            }
        }
        assert!(!database_path.exists());
        assert!(!text.contains(&path_text(&database_path)));
        assert!(!text.contains(REFRESH_DATABASE_PATH_ENV_VAR));
    }

    #[test]
    fn load_storage_summary_command_reads_file_backed_refresh_database() {
        let workspace_root = workspace_root_for_tests();
        let fixture_root = workspace_root.join("experiments/fixtures/local_sources");
        let database_path = refresh_database_path_for_tests("command-load-summary");

        let refresh_result = refresh_sources_manual_command(
            RefreshSourcesManualArgs {
                end_day_utc: "2026-06-14".to_string(),
                codex_jsonl_root: Some(path_text(&fixture_root.join("codex"))),
                claude_code_jsonl_root: Some(path_text(&fixture_root.join("claude_code"))),
                gemini_cli_jsonl_root: None,
                started_at: Some("2026-06-14T00:00:00Z".to_string()),
            },
            &database_path,
        )
        .unwrap();
        match refresh_result {
            RefreshSourcesManualResult::Success(_) => {}
            RefreshSourcesManualResult::Error(_) => {
                panic!("expected refresh command success before load");
            }
        }

        let load_result = load_storage_summary_command(
            LoadStorageSummaryArgs {
                end_day_utc: "2026-06-14".to_string(),
            },
            &database_path,
        )
        .unwrap();
        let text = serde_json::to_string(&load_result).unwrap();

        match load_result {
            LoadStorageSummaryResult::Success(payload) => {
                assert_eq!(payload["summary"]["totals"]["total_tokens"], 7570);
                assert!(payload.get("refresh_results").is_none());
            }
            LoadStorageSummaryResult::Error(_) => {
                panic!("expected storage summary load success");
            }
        }
        assert!(!text.contains(&path_text(&database_path)));
        assert!(!text.contains("experiments/fixtures"));
        assert!(!text.contains("local_sources"));
    }

    #[test]
    fn refresh_database_path_prefers_env_override_before_app_data_default() {
        let app_data_dir = PathBuf::from("synthetic-app-data-dir");
        let env_path = PathBuf::from("synthetic-override.sqlite");

        assert_eq!(
            refresh_database_path_from_app_data_dir(&app_data_dir),
            app_data_dir.join(REFRESH_DATABASE_FILE_NAME)
        );
        assert_eq!(
            refresh_database_path_from_env_or_app_data_dir(None, &app_data_dir),
            app_data_dir.join(REFRESH_DATABASE_FILE_NAME)
        );
        assert_eq!(
            refresh_database_path_from_env_or_app_data_dir(Some(env_path.clone()), &app_data_dir),
            env_path
        );
    }

    #[test]
    fn source_roots_path_uses_app_data_config_file() {
        let app_data_dir = PathBuf::from("synthetic-app-data-dir");

        assert_eq!(
            source_roots_path_from_app_data_dir(&app_data_dir),
            app_data_dir.join(SOURCE_ROOTS_FILE_NAME)
        );
    }

    #[test]
    fn api_provider_credentials_path_uses_app_data_config_file() {
        let app_data_dir = PathBuf::from("synthetic-app-data-dir");

        assert_eq!(
            api_provider_credentials_path_from_app_data_dir(&app_data_dir),
            app_data_dir.join(API_PROVIDER_CREDENTIALS_FILE_NAME)
        );
    }

    #[test]
    fn saved_source_roots_normalize_roots_and_auto_refresh_gate() {
        let saved = normalize_saved_source_roots(SavedSourceRoots {
            codex_jsonl_root: Some(" synthetic-codex-root ".to_string()),
            claude_code_jsonl_root: Some(" synthetic-claude-root ".to_string()),
            gemini_cli_jsonl_root: None,
            auto_refresh_enabled: true,
            auto_refresh_interval_minutes: 1,
        });

        assert_eq!(
            saved.codex_jsonl_root.as_deref(),
            Some("synthetic-codex-root")
        );
        assert_eq!(
            saved.claude_code_jsonl_root.as_deref(),
            Some("synthetic-claude-root")
        );
        assert!(saved.auto_refresh_enabled);
        assert_eq!(
            saved.auto_refresh_interval_minutes,
            DEFAULT_AUTO_REFRESH_INTERVAL_MINUTES
        );

        let missing_claude = normalize_saved_source_roots(SavedSourceRoots {
            codex_jsonl_root: Some("synthetic-codex-root".to_string()),
            claude_code_jsonl_root: None,
            gemini_cli_jsonl_root: None,
            auto_refresh_enabled: true,
            auto_refresh_interval_minutes: 1441,
        });

        assert!(missing_claude.auto_refresh_enabled);
        assert_eq!(missing_claude.auto_refresh_interval_minutes, 1440);
    }

    #[test]
    fn saved_source_roots_file_round_trips_without_path_echo_errors() {
        let path = refresh_database_path_for_tests("source-roots").with_extension("json");
        let saved = save_source_roots_to_path(
            &path,
            &SavedSourceRoots {
                codex_jsonl_root: Some("synthetic-codex-root".to_string()),
                claude_code_jsonl_root: Some("synthetic-claude-root".to_string()),
                gemini_cli_jsonl_root: None,
                auto_refresh_enabled: true,
                auto_refresh_interval_minutes: 15,
            },
        )
        .unwrap();

        assert_eq!(
            saved.codex_jsonl_root.as_deref(),
            Some("synthetic-codex-root")
        );
        assert!(path.exists());

        let loaded = load_saved_source_roots_from_path(&path).unwrap();
        assert_eq!(loaded, saved);

        clear_saved_source_roots_at_path(&path).unwrap();
        assert!(!path.exists());
        assert_eq!(
            load_saved_source_roots_from_path(&path).unwrap(),
            SavedSourceRoots::default()
        );
    }

    #[test]
    fn saved_source_roots_invalid_file_returns_redacted_error() {
        let path = refresh_database_path_for_tests("invalid-source-roots").with_extension("json");
        fs::write(&path, "{\"codex_jsonl_root\":42}").unwrap();

        let result = load_saved_source_roots_from_path(&path).unwrap_err();

        assert_eq!(result, "saved source roots were invalid");
        assert!(!result.contains(&path_text(&path)));
    }

    #[test]
    fn missing_api_provider_credentials_return_default_statuses() {
        let path = refresh_database_path_for_tests("missing-api-provider-credentials")
            .with_extension("json");

        let statuses = load_api_provider_credentials_from_path(&path).unwrap();

        assert_eq!(statuses.providers.len(), 4);
        assert_eq!(statuses.providers[0].provider_id, "openai_api_cost");
        assert_eq!(statuses.providers[0].status, "not_configured");
        assert!(!statuses.providers[0].credential_configured);
        assert_eq!(statuses.providers[1].provider_id, "claude_api_cost");
        assert_eq!(statuses.providers[1].status, "needs_verified_adapter");
    }

    #[cfg(windows)]
    #[test]
    fn api_provider_credential_file_round_trips_without_plaintext_key() {
        let path =
            refresh_database_path_for_tests("api-provider-credentials").with_extension("json");
        let secret = " sk-admin-fixture-secret ";

        let statuses = save_api_provider_credential_to_path(
            &path,
            &SaveApiProviderCredentialArgs {
                provider_id: "openai_api_cost".to_string(),
                api_key: secret.to_string(),
            },
        )
        .unwrap();
        let openai_status = statuses
            .providers
            .iter()
            .find(|status| status.provider_id == "openai_api_cost")
            .unwrap();

        assert_eq!(openai_status.status, "unavailable");
        assert!(openai_status.adapter_verified);
        assert!(openai_status.credential_configured);
        let file_text = fs::read_to_string(&path).unwrap();
        assert!(file_text.contains("protected_api_key"));
        assert!(!file_text.contains("sk-admin-fixture-secret"));
        assert!(!file_text.contains("secret"));

        assert_eq!(
            load_api_provider_credential_from_path(&path, "openai_api_cost").unwrap(),
            Some("sk-admin-fixture-secret".to_string())
        );

        let removed = remove_api_provider_credential_at_path(
            &path,
            &RemoveApiProviderCredentialArgs {
                provider_id: "openai_api_cost".to_string(),
            },
        )
        .unwrap();
        let removed_openai_status = removed
            .providers
            .iter()
            .find(|status| status.provider_id == "openai_api_cost")
            .unwrap();
        assert_eq!(removed_openai_status.status, "not_configured");
        assert!(!removed_openai_status.credential_configured);
        assert_eq!(
            load_api_provider_credential_from_path(&path, "openai_api_cost").unwrap(),
            None
        );
    }

    #[cfg(windows)]
    #[test]
    fn unverified_api_provider_credential_stays_needs_verified_adapter() {
        let path = refresh_database_path_for_tests("unverified-api-provider-credentials")
            .with_extension("json");

        let statuses = save_api_provider_credential_to_path(
            &path,
            &SaveApiProviderCredentialArgs {
                provider_id: "claude_api_cost".to_string(),
                api_key: "sk-claude-fixture-secret".to_string(),
            },
        )
        .unwrap();
        let claude_status = statuses
            .providers
            .iter()
            .find(|status| status.provider_id == "claude_api_cost")
            .unwrap();

        assert_eq!(claude_status.status, "needs_verified_adapter");
        assert!(!claude_status.adapter_verified);
        assert!(claude_status.credential_configured);
        assert!(!fs::read_to_string(&path)
            .unwrap()
            .contains("sk-claude-fixture-secret"));
    }

    #[test]
    fn api_provider_credential_rejects_unknown_provider_without_echoing_input() {
        let path = refresh_database_path_for_tests("unknown-api-provider-credential")
            .with_extension("json");
        let provider_id = "C:/Users/example/secret/provider";

        let result = save_api_provider_credential_to_path(
            &path,
            &SaveApiProviderCredentialArgs {
                provider_id: provider_id.to_string(),
                api_key: "sk-admin-fixture-secret".to_string(),
            },
        )
        .unwrap_err();

        assert_eq!(result, "Unknown API cost provider");
        assert!(!result.contains(provider_id));
        assert!(!result.contains("sk-admin-fixture-secret"));
        assert!(!path.exists());
    }

    #[test]
    fn api_provider_credential_rejects_empty_key_without_writing_file() {
        let path =
            refresh_database_path_for_tests("empty-api-provider-credential").with_extension("json");

        let result = save_api_provider_credential_to_path(
            &path,
            &SaveApiProviderCredentialArgs {
                provider_id: "openai_api_cost".to_string(),
                api_key: "  ".to_string(),
            },
        )
        .unwrap_err();

        assert_eq!(result, "API provider credential is required");
        assert!(!path.exists());
    }

    #[test]
    fn sync_api_provider_billing_command_requires_configured_openai_credential() {
        let database_path = refresh_database_path_for_tests("missing-api-billing-key");
        let credential_path =
            refresh_database_path_for_tests("missing-api-billing-key-credentials")
                .with_extension("json");

        let result = sync_api_provider_billing_command(
            SyncApiProviderBillingArgs {
                provider_id: "openai_api_cost".to_string(),
                end_day_utc: "2026-06-14".to_string(),
                started_at: None,
            },
            &database_path,
            &credential_path,
        )
        .unwrap();
        let text = serde_json::to_string(&result).unwrap();

        match result {
            ApiProviderBillingSyncResult::Error(payload) => {
                assert_eq!(payload.error.code, "api_provider_billing_sync_unavailable");
                assert_eq!(payload.error.field.as_deref(), Some("credential"));
                assert_eq!(
                    payload.error.message,
                    "OpenAI API provider credential is not configured"
                );
            }
            ApiProviderBillingSyncResult::Success(_) => {
                panic!("expected missing credential error");
            }
        }
        assert!(!database_path.exists());
        assert!(!text.contains(&path_text(&database_path)));
        assert!(!text.contains(&path_text(&credential_path)));
    }

    #[test]
    fn sync_api_provider_billing_command_rejects_unverified_provider_before_key_lookup() {
        let database_path = refresh_database_path_for_tests("unverified-api-billing");
        let credential_path = refresh_database_path_for_tests("unverified-api-billing-credentials")
            .with_extension("json");

        let result = sync_api_provider_billing_command(
            SyncApiProviderBillingArgs {
                provider_id: "claude_api_cost".to_string(),
                end_day_utc: "2026-06-14".to_string(),
                started_at: None,
            },
            &database_path,
            &credential_path,
        )
        .unwrap();

        match result {
            ApiProviderBillingSyncResult::Error(payload) => {
                assert_eq!(payload.error.code, "api_provider_billing_sync_unavailable");
                assert_eq!(payload.error.field.as_deref(), Some("provider_id"));
                assert_eq!(
                    payload.error.message,
                    "Provider billing adapter has not been verified"
                );
            }
            ApiProviderBillingSyncResult::Success(_) => {
                panic!("expected unverified provider error");
            }
        }
        assert!(!database_path.exists());
        assert!(!credential_path.exists());
    }

    #[test]
    fn api_provider_billing_sync_backend_process_reports_missing_env_without_key_stdin() {
        let workspace_root = workspace_root_for_tests();
        let database_path = refresh_database_path_for_tests("api-billing-missing-env");
        let args = SyncApiProviderBillingArgs {
            provider_id: "openai_api_cost".to_string(),
            end_day_utc: "2026-06-14".to_string(),
            started_at: None,
        };

        let result = run_api_provider_billing_sync_backend_process_with_database_path(
            &python_executable_for_tests(),
            &workspace_root,
            &args,
            Some(&database_path),
            None,
        )
        .unwrap();
        let text = serde_json::to_string(&result).unwrap();

        match result {
            ApiProviderBillingSyncResult::Error(payload) => {
                assert_eq!(payload.error.code, "api_provider_billing_sync_unavailable");
                assert_eq!(payload.error.field.as_deref(), Some("credential"));
            }
            ApiProviderBillingSyncResult::Success(_) => {
                panic!("expected missing env error");
            }
        }
        assert!(!text.contains(OPENAI_ADMIN_KEY_ENV_VAR));
        assert!(!text.contains(&path_text(&database_path)));
    }

    #[test]
    fn refresh_database_parent_dir_ignores_empty_relative_parent() {
        assert_eq!(refresh_database_parent_dir(Path::new("usage.sqlite")), None);
        assert_eq!(
            refresh_database_parent_dir(Path::new("nested/usage.sqlite")),
            Some(Path::new("nested"))
        );
    }

    #[test]
    fn refresh_sources_manual_backend_process_returns_redacted_error() {
        let workspace_root = workspace_root_for_tests();
        let args = RefreshSourcesManualArgs {
            end_day_utc: "2026-6-14".to_string(),
            codex_jsonl_root: Some("C:/Users/example/secret/codex".to_string()),
            claude_code_jsonl_root: None,
            gemini_cli_jsonl_root: None,
            started_at: None,
        };

        let result = run_refresh_sources_manual_backend_process(
            &python_executable_for_tests(),
            &workspace_root,
            &args,
        )
        .unwrap();
        let text = serde_json::to_string(&result).unwrap();

        match result {
            RefreshSourcesManualResult::Error(payload) => {
                assert_eq!(payload.error.code, "invalid_refresh_request");
                assert_eq!(payload.error.field.as_deref(), Some("end_day_utc"));
                assert_eq!(payload.error.message, "end_day_utc must be YYYY-MM-DD");
            }
            RefreshSourcesManualResult::Success(_) => {
                panic!("expected backend process error");
            }
        }
        assert!(!text.contains("C:/Users"));
        assert!(!text.contains("secret"));
        assert!(!text.contains("codex"));
    }

    #[test]
    fn gated_refresh_sources_manual_backend_process_requires_one_root() {
        let workspace_root = workspace_root_for_tests();
        let args = RefreshSourcesManualArgs {
            end_day_utc: "2026-06-14".to_string(),
            codex_jsonl_root: None,
            claude_code_jsonl_root: None,
            gemini_cli_jsonl_root: None,
            started_at: None,
        };

        let result = run_gated_refresh_sources_manual_backend_process(
            &python_executable_for_tests(),
            &workspace_root,
            &args,
        )
        .unwrap();
        let text = serde_json::to_string(&result).unwrap();

        match result {
            RefreshSourcesManualResult::Error(payload) => {
                assert_eq!(payload.error.code, "invalid_refresh_request");
                assert_eq!(payload.error.field.as_deref(), Some("codex_jsonl_root"));
                assert_eq!(
                    payload.error.message,
                    "at least one source root is required for manual refresh"
                );
            }
            RefreshSourcesManualResult::Success(_) => {
                panic!("expected missing source root error");
            }
        }
        assert!(!text.contains("C:/Users"));
    }

    #[test]
    fn gated_refresh_sources_manual_backend_process_rejects_before_database_setup() {
        let workspace_root = workspace_root_for_tests();
        let database_path = refresh_database_path_for_tests("missing-root-refresh");
        let args = RefreshSourcesManualArgs {
            end_day_utc: "2026-06-14".to_string(),
            codex_jsonl_root: None,
            claude_code_jsonl_root: None,
            gemini_cli_jsonl_root: None,
            started_at: None,
        };

        let result = run_gated_refresh_sources_manual_backend_process_with_database_path(
            &python_executable_for_tests(),
            &workspace_root,
            &args,
            Some(&database_path),
        )
        .unwrap();
        let text = serde_json::to_string(&result).unwrap();

        match result {
            RefreshSourcesManualResult::Error(payload) => {
                assert_eq!(payload.error.code, "invalid_refresh_request");
                assert_eq!(payload.error.field.as_deref(), Some("codex_jsonl_root"));
            }
            RefreshSourcesManualResult::Success(_) => {
                panic!("expected missing Codex root error");
            }
        }
        assert!(!database_path.exists());
        assert!(!text.contains(&path_text(&database_path)));
        assert!(!text.contains("synthetic"));
    }

    #[test]
    fn refresh_sources_manual_command_requires_one_root() {
        let database_path = refresh_database_path_for_tests("command-missing-root");
        let args = RefreshSourcesManualArgs {
            end_day_utc: "2026-06-14".to_string(),
            codex_jsonl_root: None,
            claude_code_jsonl_root: None,
            gemini_cli_jsonl_root: None,
            started_at: None,
        };

        let result = refresh_sources_manual_command(args, &database_path).unwrap();
        let text = serde_json::to_string(&result).unwrap();

        match result {
            RefreshSourcesManualResult::Error(payload) => {
                assert_eq!(payload.error.code, "invalid_refresh_request");
                assert_eq!(payload.error.field.as_deref(), Some("codex_jsonl_root"));
                assert_eq!(
                    payload.error.message,
                    "at least one source root is required for manual refresh"
                );
            }
            RefreshSourcesManualResult::Success(_) => {
                panic!("expected missing source root error");
            }
        }
        assert!(!database_path.exists());
        assert!(!text.contains("synthetic"));
    }

    #[test]
    fn refresh_sources_manual_command_returns_fixture_success() {
        let workspace_root = workspace_root_for_tests();
        let fixture_root = workspace_root.join("experiments/fixtures/local_sources");
        let database_path = refresh_database_path_for_tests("command-fixture-success");
        let args = RefreshSourcesManualArgs {
            end_day_utc: "2026-06-14".to_string(),
            codex_jsonl_root: Some(path_text(&fixture_root.join("codex"))),
            claude_code_jsonl_root: Some(path_text(&fixture_root.join("claude_code"))),
            gemini_cli_jsonl_root: Some(path_text(&fixture_root.join("gemini_cli"))),
            started_at: Some("2026-06-14T00:00:00Z".to_string()),
        };

        let result = refresh_sources_manual_command(args, &database_path).unwrap();
        let text = serde_json::to_string(&result).unwrap();

        match result {
            RefreshSourcesManualResult::Success(payload) => {
                assert_eq!(
                    payload["storage_summary"]["summary"]["totals"]["total_tokens"],
                    9820
                );
            }
            RefreshSourcesManualResult::Error(_) => {
                panic!("expected refresh command success");
            }
        }
        assert!(database_path.exists());
        assert!(!text.contains("experiments/fixtures"));
        assert!(!text.contains("local_sources"));
    }

    #[test]
    fn gated_refresh_sources_manual_backend_process_accepts_single_codex_root() {
        let workspace_root = workspace_root_for_tests();
        let fixture_root = workspace_root.join("experiments/fixtures/local_sources");
        let args = RefreshSourcesManualArgs {
            end_day_utc: "2026-06-14".to_string(),
            codex_jsonl_root: Some(path_text(&fixture_root.join("codex"))),
            claude_code_jsonl_root: None,
            gemini_cli_jsonl_root: None,
            started_at: Some("2026-06-14T00:00:00Z".to_string()),
        };

        let result = run_gated_refresh_sources_manual_backend_process(
            &python_executable_for_tests(),
            &workspace_root,
            &args,
        )
        .unwrap();
        let text = serde_json::to_string(&result).unwrap();

        match result {
            RefreshSourcesManualResult::Success(payload) => {
                assert_eq!(
                    payload["storage_summary"]["summary"]["totals"]["total_tokens"],
                    2540
                );
            }
            RefreshSourcesManualResult::Error(_) => {
                panic!("expected single Codex root success");
            }
        }
        assert!(!text.contains("synthetic-codex-root"));
    }

    #[test]
    fn gated_refresh_sources_manual_backend_process_returns_fixture_success() {
        let workspace_root = workspace_root_for_tests();
        let fixture_root = workspace_root.join("experiments/fixtures/local_sources");
        let args = RefreshSourcesManualArgs {
            end_day_utc: "2026-06-14".to_string(),
            codex_jsonl_root: Some(path_text(&fixture_root.join("codex"))),
            claude_code_jsonl_root: Some(path_text(&fixture_root.join("claude_code"))),
            gemini_cli_jsonl_root: Some(path_text(&fixture_root.join("gemini_cli"))),
            started_at: Some("2026-06-14T00:00:00Z".to_string()),
        };

        let result = run_gated_refresh_sources_manual_backend_process(
            &python_executable_for_tests(),
            &workspace_root,
            &args,
        )
        .unwrap();

        match result {
            RefreshSourcesManualResult::Success(payload) => {
                assert_eq!(
                    payload["storage_summary"]["summary"]["totals"]["total_tokens"],
                    9820
                );
            }
            RefreshSourcesManualResult::Error(_) => {
                panic!("expected gated backend process success");
            }
        }
    }

    #[test]
    fn source_refresh_summary_sample_has_expected_totals() {
        let payload = source_refresh_summary_sample_payload();

        assert_eq!(payload["refresh_results"].as_array().unwrap().len(), 5);
        assert_eq!(payload["refresh_results"][0]["events_seen"], 2);
        assert_eq!(
            payload["storage_summary"]["summary"]["totals"]["total_tokens"],
            17040
        );
    }

    #[test]
    fn source_refresh_summary_sample_does_not_expose_source_paths() {
        let text = source_refresh_summary_sample_payload().to_string();

        assert!(!text.contains("experiments/fixtures"));
        assert!(!text.contains("local_sources"));
        assert!(!text.contains("sessions"));
        assert!(!text.contains("projects"));
    }

    #[test]
    fn source_refresh_error_sample_has_expected_error_shape() {
        let payload = source_refresh_error_sample_payload();

        assert!(payload.get("refresh_results").is_none());
        assert_eq!(payload["error"]["code"], "invalid_refresh_request");
        assert_eq!(payload["error"]["field"], "end_day_utc");
        assert_eq!(
            payload["error"]["message"],
            "end_day_utc must be YYYY-MM-DD"
        );
    }

    #[test]
    fn source_refresh_success_and_error_samples_are_disjoint() {
        let success_payload = source_refresh_summary_sample_payload();
        let error_payload = source_refresh_error_sample_payload();

        assert!(success_payload.get("error").is_none());
        assert!(error_payload.get("storage_summary").is_none());
    }

    #[test]
    fn source_refresh_error_sample_does_not_expose_source_paths() {
        let text = source_refresh_error_sample_payload().to_string();

        assert!(!text.contains("C:/Users"));
        assert!(!text.contains("secret"));
        assert!(!text.contains("source_root"));
        assert!(!text.contains("source_path"));
    }

    fn python_executable_for_tests() -> PathBuf {
        env::var_os("YTH_PYTHON")
            .map(PathBuf::from)
            .unwrap_or_else(|| PathBuf::from("python"))
    }

    fn workspace_root_for_tests() -> PathBuf {
        workspace_root_from_manifest()
    }

    fn refresh_database_path_for_tests(prefix: &str) -> PathBuf {
        let directory = workspace_root_for_tests()
            .join("apps")
            .join("desktop")
            .join("src-tauri")
            .join("target")
            .join("refresh-database-tests");
        fs::create_dir_all(&directory).unwrap();
        let suffix = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        directory.join(format!("{prefix}-{}-{suffix}.sqlite", process::id()))
    }

    fn path_text(path: &Path) -> String {
        path.to_string_lossy().into_owned()
    }
}
