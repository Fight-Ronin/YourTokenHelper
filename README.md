# YourTokenHelper

Lightweight desktop token usage viewer for a personal coding-agent workflow.

## Repository Structure

- `docs/`: product research, PR plans, source strategy, and interface notes.
- `experiments/probes/`: exploratory scripts used to validate source availability and parser contracts.
- `experiments/fixtures/`: synthetic, privacy-safe fixture data for probes and parser smoke tests.
- `backend/`: future formal backend implementation boundary.
- `apps/desktop/`: future desktop app implementation boundary.

The current code under `experiments/` is intentionally spike code. Backend implementation should graduate into `backend/` only after its contracts are stable enough for the desktop app to depend on.

## Development Environment

Use the dedicated conda environment declared in `environment.yml`:

```powershell
conda env create -f environment.yml
conda run -n tokenviz python -m pytest
```

For one-off scripts, prefer `conda run -n tokenviz ...` so automation and local runs use the same Python and Node toolchain.

Windows desktop prerequisites are installed on this machine for future Tauri work:

- stable MSVC Rust toolchain via rustup;
- Microsoft C++ Build Tools;
- Microsoft Edge WebView2 Runtime;
- Cargo, used by the local Tauri CLI.

Use the desktop npm script as the standard entrypoint; it temporarily prepends
`%USERPROFILE%\.cargo\bin` before calling the local Tauri CLI:

```powershell
cd apps\desktop
conda run --no-capture-output -n tokenviz npm run tauri -- dev
```
