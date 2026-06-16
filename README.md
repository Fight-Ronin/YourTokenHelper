# YourTokenHelper

Lightweight desktop token usage viewer for a personal coding-agent workflow.

## Download

- [YourTokenHelper v1 Windows x64 installer](releases/v1/YourTokenHelper-v1-x64-setup.exe)

## Repository Structure

- `releases/v1/`: V1 Windows installer for download.
- `backend/`: backend contracts, source adapters, and local storage.
- `apps/desktop/`: Tauri + React desktop app.

Main is the V1 release branch. Development docs, tests, and exploratory spike
materials live on `dev`.

## Build From Source

Use the dedicated conda environment declared in `environment.yml`:

```powershell
conda env create -f environment.yml
```

For one-off scripts, prefer `conda run -n tokenviz ...` so automation and local
runs use the same Python and Node toolchain.

Windows desktop prerequisites used by the Tauri build:

- stable MSVC Rust toolchain via rustup;
- Microsoft C++ Build Tools;
- Microsoft Edge WebView2 Runtime;
- Cargo, used by the local Tauri CLI.

Use the desktop npm script as the standard entrypoint; it temporarily prepends
`%USERPROFILE%\.cargo\bin` before calling the local Tauri CLI:

```powershell
cd apps\desktop
conda run --no-capture-output -n tokenviz npm run tauri -- build
```
