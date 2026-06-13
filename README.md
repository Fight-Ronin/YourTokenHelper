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
- Cargo Tauri CLI.

After opening a new terminal, `cargo tauri --version` should report the installed Tauri CLI. In the current Codex shell, use `%USERPROFILE%\.cargo\bin` explicitly if Cargo is not yet on `PATH`.
