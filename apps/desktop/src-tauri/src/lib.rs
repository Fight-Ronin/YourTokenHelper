use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::{
    env, fs,
    io::{self, Write},
    path::{Path, PathBuf},
    process::{Command, Stdio},
};
use tauri::Manager;

pub const SOURCE_REFRESH_SUMMARY_SAMPLE_COMMAND: &str = "source_refresh_summary_sample";
pub const REFRESH_SOURCES_MANUAL_COMMAND: &str = "refresh_sources_manual";
pub const LOAD_STORAGE_SUMMARY_COMMAND: &str = "load_storage_summary";
pub const LOAD_SAVED_SOURCE_ROOTS_COMMAND: &str = "load_saved_source_roots";
pub const SAVE_SOURCE_ROOTS_COMMAND: &str = "save_source_roots";
pub const CLEAR_SAVED_SOURCE_ROOTS_COMMAND: &str = "clear_saved_source_roots";
pub const BACKEND_REFRESH_COMMAND_MODULE: &str = "backend.sources.refresh_command_cli";
pub const BACKEND_LOAD_STORAGE_SUMMARY_COMMAND_MODULE: &str = "backend.storage.summary_command_cli";
pub const REFRESH_DATABASE_PATH_ENV_VAR: &str = "YTH_REFRESH_DATABASE_PATH";
pub const REFRESH_DATABASE_FILE_NAME: &str = "usage.sqlite";
pub const SOURCE_ROOTS_FILE_NAME: &str = "source-roots.json";
pub const DEFAULT_AUTO_REFRESH_INTERVAL_MINUTES: u16 = 15;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RefreshSourcesManualArgs {
    pub end_day_utc: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub codex_jsonl_root: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub claude_code_jsonl_root: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cursor_jsonl_root: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub gemini_cli_jsonl_root: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub github_copilot_jsonl_root: Option<String>,
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

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SavedSourceRoots {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub codex_jsonl_root: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub claude_code_jsonl_root: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cursor_jsonl_root: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub gemini_cli_jsonl_root: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub github_copilot_jsonl_root: Option<String>,
    #[serde(default)]
    pub auto_refresh_enabled: bool,
    #[serde(default = "default_auto_refresh_interval_minutes")]
    pub auto_refresh_interval_minutes: u16,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(untagged)]
pub enum LoadStorageSummaryResult {
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
            cursor_jsonl_root: None,
            gemini_cli_jsonl_root: None,
            github_copilot_jsonl_root: None,
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

pub fn normalize_saved_source_roots(args: SavedSourceRoots) -> SavedSourceRoots {
    let codex_jsonl_root = normalize_optional_root(args.codex_jsonl_root);
    let claude_code_jsonl_root = normalize_optional_root(args.claude_code_jsonl_root);
    let cursor_jsonl_root = normalize_optional_root(args.cursor_jsonl_root);
    let gemini_cli_jsonl_root = normalize_optional_root(args.gemini_cli_jsonl_root);
    let github_copilot_jsonl_root = normalize_optional_root(args.github_copilot_jsonl_root);
    let has_any_root = codex_jsonl_root.is_some()
        || claude_code_jsonl_root.is_some()
        || cursor_jsonl_root.is_some()
        || gemini_cli_jsonl_root.is_some()
        || github_copilot_jsonl_root.is_some();

    SavedSourceRoots {
        codex_jsonl_root,
        claude_code_jsonl_root,
        cursor_jsonl_root,
        gemini_cli_jsonl_root,
        github_copilot_jsonl_root,
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

fn has_any_refresh_source_root(args: &RefreshSourcesManualArgs) -> bool {
    root_is_present(&args.codex_jsonl_root)
        || root_is_present(&args.claude_code_jsonl_root)
        || root_is_present(&args.cursor_jsonl_root)
        || root_is_present(&args.gemini_cli_jsonl_root)
        || root_is_present(&args.github_copilot_jsonl_root)
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
    refresh_sources_manual_command(args, &refresh_database_path)
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
    load_storage_summary_command(args, &refresh_database_path)
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

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            source_refresh_summary_sample,
            refresh_sources_manual,
            load_storage_summary,
            load_saved_source_roots,
            save_source_roots,
            clear_saved_source_roots
        ])
        .run(tauri::generate_context!())
        .expect("error while running YourTokenHelper");
}

#[cfg(test)]
mod tests {
    use super::{
        backend_load_storage_summary_process_module_args, backend_refresh_process_module_args,
        clear_saved_source_roots_at_path, load_saved_source_roots_from_path,
        load_storage_summary_command, load_storage_summary_result_from_stdout,
        load_storage_summary_stdin, normalize_saved_source_roots, refresh_database_parent_dir,
        refresh_database_path_from_app_data_dir, refresh_database_path_from_env_or_app_data_dir,
        refresh_sources_manual_command, refresh_sources_manual_result_from_stdout,
        refresh_sources_manual_stdin, run_gated_refresh_sources_manual_backend_process,
        run_gated_refresh_sources_manual_backend_process_with_database_path,
        run_load_storage_summary_backend_process_with_database_path,
        run_refresh_sources_manual_backend_process,
        run_refresh_sources_manual_backend_process_with_database_path, save_source_roots_to_path,
        source_refresh_error_sample_payload, source_refresh_summary_sample_payload,
        source_roots_path_from_app_data_dir, workspace_root_from_manifest, LoadStorageSummaryArgs,
        LoadStorageSummaryResult, RefreshSourcesManualArgs, RefreshSourcesManualResult,
        SavedSourceRoots, BACKEND_LOAD_STORAGE_SUMMARY_COMMAND_MODULE,
        BACKEND_REFRESH_COMMAND_MODULE, CLEAR_SAVED_SOURCE_ROOTS_COMMAND,
        DEFAULT_AUTO_REFRESH_INTERVAL_MINUTES, LOAD_SAVED_SOURCE_ROOTS_COMMAND,
        LOAD_STORAGE_SUMMARY_COMMAND, REFRESH_DATABASE_FILE_NAME, REFRESH_DATABASE_PATH_ENV_VAR,
        REFRESH_SOURCES_MANUAL_COMMAND, SAVE_SOURCE_ROOTS_COMMAND,
        SOURCE_REFRESH_SUMMARY_SAMPLE_COMMAND, SOURCE_ROOTS_FILE_NAME,
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
        assert_eq!(LOAD_SAVED_SOURCE_ROOTS_COMMAND, "load_saved_source_roots");
        assert_eq!(SAVE_SOURCE_ROOTS_COMMAND, "save_source_roots");
        assert_eq!(CLEAR_SAVED_SOURCE_ROOTS_COMMAND, "clear_saved_source_roots");
        assert_ne!(
            REFRESH_SOURCES_MANUAL_COMMAND,
            SOURCE_REFRESH_SUMMARY_SAMPLE_COMMAND
        );
        assert_ne!(
            LOAD_STORAGE_SUMMARY_COMMAND,
            SOURCE_REFRESH_SUMMARY_SAMPLE_COMMAND
        );
        assert_ne!(LOAD_STORAGE_SUMMARY_COMMAND, REFRESH_SOURCES_MANUAL_COMMAND);
        assert_ne!(SAVE_SOURCE_ROOTS_COMMAND, REFRESH_SOURCES_MANUAL_COMMAND);
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
        assert!(serialized.get("cursor_jsonl_root").is_none());
        assert!(serialized.get("gemini_cli_jsonl_root").is_none());
        assert!(serialized.get("github_copilot_jsonl_root").is_none());
    }

    #[test]
    fn refresh_sources_manual_args_keep_roots_explicit() {
        let args: RefreshSourcesManualArgs = serde_json::from_value(json!({
            "end_day_utc": "2026-06-14",
            "codex_jsonl_root": "synthetic-codex-root",
            "claude_code_jsonl_root": "synthetic-claude-root",
            "cursor_jsonl_root": "synthetic-cursor-root",
            "gemini_cli_jsonl_root": "synthetic-gemini-root",
            "github_copilot_jsonl_root": "synthetic-copilot-root"
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
            args.cursor_jsonl_root.as_deref(),
            Some("synthetic-cursor-root")
        );
        assert_eq!(
            args.gemini_cli_jsonl_root.as_deref(),
            Some("synthetic-gemini-root")
        );
        assert_eq!(
            args.github_copilot_jsonl_root.as_deref(),
            Some("synthetic-copilot-root")
        );
        assert!(text.contains("codex_jsonl_root"));
        assert!(text.contains("claude_code_jsonl_root"));
        assert!(text.contains("cursor_jsonl_root"));
        assert!(text.contains("gemini_cli_jsonl_root"));
        assert!(text.contains("github_copilot_jsonl_root"));
        assert!(!text.contains("auto_discover"));
    }

    #[test]
    fn refresh_sources_manual_stdin_serializes_only_explicit_args() {
        let args = RefreshSourcesManualArgs {
            end_day_utc: "2026-06-14".to_string(),
            codex_jsonl_root: Some("synthetic-codex-root".to_string()),
            claude_code_jsonl_root: None,
            cursor_jsonl_root: Some("synthetic-cursor-root".to_string()),
            gemini_cli_jsonl_root: None,
            github_copilot_jsonl_root: None,
            started_at: Some("2026-06-14T00:00:00Z".to_string()),
        };
        let text = refresh_sources_manual_stdin(&args).unwrap();

        assert!(text.contains("\"end_day_utc\":\"2026-06-14\""));
        assert!(text.contains("\"codex_jsonl_root\":\"synthetic-codex-root\""));
        assert!(text.contains("\"cursor_jsonl_root\":\"synthetic-cursor-root\""));
        assert!(text.contains("\"started_at\":\"2026-06-14T00:00:00Z\""));
        assert!(!text.contains("claude_code_jsonl_root"));
        assert!(!text.contains("gemini_cli_jsonl_root"));
        assert!(!text.contains("github_copilot_jsonl_root"));
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
            cursor_jsonl_root: None,
            gemini_cli_jsonl_root: None,
            github_copilot_jsonl_root: None,
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
            cursor_jsonl_root: None,
            gemini_cli_jsonl_root: None,
            github_copilot_jsonl_root: None,
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
                cursor_jsonl_root: None,
                gemini_cli_jsonl_root: None,
                github_copilot_jsonl_root: None,
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
                cursor_jsonl_root: None,
                gemini_cli_jsonl_root: None,
                github_copilot_jsonl_root: None,
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
    fn saved_source_roots_normalize_roots_and_auto_refresh_gate() {
        let saved = normalize_saved_source_roots(SavedSourceRoots {
            codex_jsonl_root: Some(" synthetic-codex-root ".to_string()),
            claude_code_jsonl_root: Some(" synthetic-claude-root ".to_string()),
            cursor_jsonl_root: Some(" synthetic-cursor-root ".to_string()),
            gemini_cli_jsonl_root: None,
            github_copilot_jsonl_root: None,
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
        assert_eq!(
            saved.cursor_jsonl_root.as_deref(),
            Some("synthetic-cursor-root")
        );
        assert!(saved.auto_refresh_enabled);
        assert_eq!(
            saved.auto_refresh_interval_minutes,
            DEFAULT_AUTO_REFRESH_INTERVAL_MINUTES
        );

        let missing_claude = normalize_saved_source_roots(SavedSourceRoots {
            codex_jsonl_root: Some("synthetic-codex-root".to_string()),
            claude_code_jsonl_root: None,
            cursor_jsonl_root: None,
            gemini_cli_jsonl_root: None,
            github_copilot_jsonl_root: None,
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
                cursor_jsonl_root: Some("synthetic-cursor-root".to_string()),
                gemini_cli_jsonl_root: None,
                github_copilot_jsonl_root: None,
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
            cursor_jsonl_root: None,
            gemini_cli_jsonl_root: None,
            github_copilot_jsonl_root: None,
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
            cursor_jsonl_root: None,
            gemini_cli_jsonl_root: None,
            github_copilot_jsonl_root: None,
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
            cursor_jsonl_root: None,
            gemini_cli_jsonl_root: None,
            github_copilot_jsonl_root: None,
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
            cursor_jsonl_root: None,
            gemini_cli_jsonl_root: None,
            github_copilot_jsonl_root: None,
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
            cursor_jsonl_root: Some(path_text(&fixture_root.join("cursor"))),
            gemini_cli_jsonl_root: Some(path_text(&fixture_root.join("gemini_cli"))),
            github_copilot_jsonl_root: Some(path_text(&fixture_root.join("github_copilot"))),
            started_at: Some("2026-06-14T00:00:00Z".to_string()),
        };

        let result = refresh_sources_manual_command(args, &database_path).unwrap();
        let text = serde_json::to_string(&result).unwrap();

        match result {
            RefreshSourcesManualResult::Success(payload) => {
                assert_eq!(
                    payload["storage_summary"]["summary"]["totals"]["total_tokens"],
                    17040
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
            cursor_jsonl_root: None,
            gemini_cli_jsonl_root: None,
            github_copilot_jsonl_root: None,
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
            cursor_jsonl_root: Some(path_text(&fixture_root.join("cursor"))),
            gemini_cli_jsonl_root: Some(path_text(&fixture_root.join("gemini_cli"))),
            github_copilot_jsonl_root: Some(path_text(&fixture_root.join("github_copilot"))),
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
                    17040
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
