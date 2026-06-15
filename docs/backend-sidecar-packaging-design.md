# Backend Sidecar Packaging Design

## Goal

Package the desktop app so a Windows user can install and run YourTokenHelper
without installing Python, cloning this repository, or setting `YTH_PYTHON` /
`YTH_WORKSPACE_ROOT`.

Initial scope is Windows x64. The design keeps room for macOS/Linux target
triples, but those are not required for the first release.

## Current State

The Tauri shell is already a desktop app. The frontend calls Rust commands, and
Rust currently shells out to Python modules:

- `backend.sources.refresh_command_cli`
- `backend.storage.summary_command_cli`
- `backend.sources.manual_allowance_command_cli`
- `backend.sources.api_provider_billing_sync_command_cli`

Those modules all use the same shape:

- read one JSON request from stdin
- write one JSON response to stdout
- use `YTH_REFRESH_DATABASE_PATH` for the app-data SQLite database
- use `OPENAI_ADMIN_KEY` only for the billing sync process
- avoid returning local paths or plaintext secrets

The backend is currently standard-library Python. That makes it a good
candidate for a frozen sidecar binary.

## Recommendation

Use one PyInstaller-built backend sidecar binary and register it as a Tauri
`externalBin`.

The sidecar should be named `yth-backend` and expose a small dispatcher:

```text
yth-backend refresh_sources_manual
yth-backend load_storage_summary
yth-backend save_manual_allowance_window
yth-backend sync_api_provider_billing
```

Each subcommand preserves the existing stdin/stdout JSON contract. The Tauri
Rust layer changes only how it launches the backend, not what payloads cross the
boundary.

## Why This Route

### Chosen: PyInstaller one-file sidecar

Pros:

- Smallest change to the existing Python backend.
- Does not require users to install Python.
- Fits Tauri's sidecar model for external binaries.
- Keeps backend isolated as a child process, which matches today's security and
  redaction boundary.
- One binary can route all four backend commands.

Cons:

- Windows builds must be produced on Windows.
- Startup pays PyInstaller bootstrap cost for every backend invocation.
- Antivirus false positives are possible with frozen Python apps.

The startup cost is acceptable for v1 because backend calls are user-triggered,
startup summary readback, or 15-minute auto refresh. If it becomes noticeable,
we can later move from one-shot CLI calls to a long-lived sidecar daemon.

### Rejected for v1: bundle raw `.py` files plus embedded Python

This avoids PyInstaller, but it is more fragile: we would need to ship a Python
distribution, manage import paths, patch working directories, and harden a much
larger file layout. It also keeps the current "run Python from a repo-like
workspace" assumption alive.

### Rejected for v1: rewrite backend in Rust

This likely gives the cleanest final binary, but it turns packaging work into a
backend rewrite. That is too large for the immediate goal.

## Target Architecture

```text
React UI
  -> Tauri invoke(command, args)
    -> Rust command validates redacted UI boundary
      -> yth-backend sidecar <subcommand>
        -> existing Python command handler
          -> app-data SQLite / source roots / provider APIs
```

The source roots remain explicit user inputs. The backend sidecar must not
perform implicit local discovery, and command responses must continue to avoid
echoing root paths, filenames, prompts, responses, API keys, or raw provider
payloads.

## Python Changes

Add a single dispatcher module, for example:

```text
backend/sidecar_cli.py
```

Responsibilities:

- parse `argv[1]` as a command name
- dispatch to the existing `run_*_command_io(sys.stdin, sys.stdout)` functions
- return exit code `2` for unknown commands
- write only fixed, non-sensitive errors to stderr for launcher failures

Command mapping:

```text
refresh_sources_manual      -> backend.sources.refresh_command_cli.run_primary_refresh_command_io
load_storage_summary        -> backend.storage.summary_command_cli.run_load_storage_summary_command_io
save_manual_allowance_window -> backend.sources.manual_allowance_command_cli.run_manual_allowance_command_io
sync_api_provider_billing   -> backend.sources.api_provider_billing_sync_command_cli.run_api_provider_billing_sync_command_io
```

The existing module CLIs stay in place for development and tests.

## Build Changes

Add a backend sidecar build script, preferably under:

```text
apps/desktop/scripts/build-backend-sidecar.mjs
```

The script should:

1. Run `rustc --print host-tuple`.
2. Run PyInstaller against `backend/sidecar_cli.py`.
3. Copy or emit the executable as:

```text
apps/desktop/src-tauri/binaries/yth-backend-<target-triple>.exe
```

For Windows x64, the expected target is:

```text
apps/desktop/src-tauri/binaries/yth-backend-x86_64-pc-windows-msvc.exe
```

Add generated files to `.gitignore` unless we intentionally commit release
artifacts. The `src-tauri/binaries/` directory can keep a `.gitkeep`, while the
platform-suffixed executables remain build outputs.

Add PyInstaller to the development environment:

```yaml
dependencies:
  - pyinstaller
```

If conda-forge PyInstaller is unavailable in a particular environment, install
it through pip in the same `tokenviz` environment.

## Tauri Configuration

Update `apps/desktop/src-tauri/tauri.conf.json`:

```json
{
  "build": {
    "beforeBuildCommand": "npm run build && npm run build:backend-sidecar"
  },
  "bundle": {
    "active": true,
    "targets": ["nsis"],
    "externalBin": ["binaries/yth-backend"]
  }
}
```

Tauri expects the configured `externalBin` name without the target suffix, while
the actual file on disk includes the `-<target-triple>` suffix.

Keep `targets` to `["nsis"]` for the first Windows installer. We can move back
to `"all"` after we have signed release builds and any other installer formats
are intentional.

## Rust Launcher Changes

Add `tauri-plugin-shell` and initialize it in the Tauri builder.

For packaged execution, resolve the backend through:

```rust
app.shell().sidecar("yth-backend")
```

The shell plugin command can be converted into `std::process::Command`, so the
existing stdin/stdout collection helper can stay largely intact.

Introduce one launch abstraction:

```text
BackendProcessTarget
  DevPython { python_executable, workspace_root }
  PackagedSidecar { app_handle, command_name }
```

Runtime selection:

1. If `YTH_PYTHON` or `YTH_WORKSPACE_ROOT` is set, use the existing dev Python
   path. This keeps local debugging explicit.
2. Otherwise, use the Tauri sidecar.

For sidecar mode:

- pass the backend command name as the first argument
- preserve `YTH_REFRESH_DATABASE_PATH`
- preserve `OPENAI_ADMIN_KEY` only for billing sync
- avoid setting current dir to the repository root
- map spawn/stdout/parse failures to the same redacted UI-facing errors used
  today

The current pure process helpers should remain testable. Add sidecar-specific
tests around command construction and subcommand mapping; keep end-to-end
sidecar execution as a smoke test because it depends on PyInstaller output.

## Release Command

Target command after implementation:

```powershell
cd apps\desktop
conda run -n tokenviz cmd /c "set PATH=%USERPROFILE%\.cargo\bin;%PATH% && npm run tauri -- build"
```

Expected outputs:

```text
apps/desktop/src-tauri/target/release/your-token-helper.exe
apps/desktop/src-tauri/target/release/bundle/nsis/*.exe
```

## Verification Plan

### Unit and contract tests

- `pytest backend/tests`
- `npm run test:commands`
- Rust tests for process command mapping

### Sidecar smoke tests

Build the sidecar, then run it directly:

```powershell
yth-backend-x86_64-pc-windows-msvc.exe load_storage_summary
yth-backend-x86_64-pc-windows-msvc.exe refresh_sources_manual
```

Feed the same JSON used by current command tests. Confirm stdout matches the
existing response unions.

### Packaged app smoke tests

Install the NSIS build on a Windows machine where `python` is not available on
`PATH`.

Verify:

- app starts without `YTH_PYTHON`
- saved aggregate load does not require repository files
- manual refresh works with explicit fixture roots or real user-selected roots
- API billing sync uses only the protected credential path and does not expose
  plaintext keys
- UI responses still do not show source roots, filenames, prompt text, response
  text, raw provider payloads, or local database paths

## Risks and Mitigations

- PyInstaller cold start: measure startup summary readback and manual refresh.
  If it is too slow, consider a sidecar daemon later.
- Antivirus flags: keep builds signed before broader distribution.
- Hidden imports: backend is mostly standard library, but the dispatcher smoke
  test should catch missing imports.
- Platform drift: generate the target-triple suffix in the build script rather
  than hard-coding Windows x64 in config.
- Error leakage: keep stderr fixed and continue parsing only structured stdout
  as the UI-facing contract.

## Implementation Order

1. Add `backend/sidecar_cli.py` plus Python tests proving it dispatches to the
   existing four command IO functions.
2. Add the PyInstaller build script and generated-output ignores.
3. Add Tauri `externalBin`, enable bundling, and add `tauri-plugin-shell`.
4. Refactor Rust backend process launching to select dev Python or packaged
   sidecar.
5. Run command tests, backend tests, Rust tests, sidecar smoke, then full Tauri
   build.

## References

- Tauri v2 sidecars: https://v2.tauri.app/develop/sidecar/
- Tauri v2 config reference: https://v2.tauri.app/reference/config/
- PyInstaller usage: https://pyinstaller.org/en/stable/usage.html
