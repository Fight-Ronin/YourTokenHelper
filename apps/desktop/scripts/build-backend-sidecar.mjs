import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptPath = fileURLToPath(import.meta.url);
const scriptDir = path.dirname(scriptPath);
const desktopRoot = path.resolve(scriptDir, "..");
const repoRoot = path.resolve(desktopRoot, "..", "..");
const srcTauriRoot = path.join(desktopRoot, "src-tauri");
const entryPath = path.join(repoRoot, "backend", "sidecar_cli.py");
const binariesDir = path.join(srcTauriRoot, "binaries");
const pyinstallerWorkDir = path.join(srcTauriRoot, "target", "pyinstaller-build");
const pyinstallerSpecDir = path.join(srcTauriRoot, "target", "pyinstaller-spec");

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: options.cwd ?? repoRoot,
    env: options.env ?? process.env,
    stdio: options.stdio ?? "pipe",
    encoding: "utf8",
    shell: process.platform === "win32",
  });

  if (result.status !== 0) {
    const stderr = result.stderr?.trim();
    const stdout = result.stdout?.trim();
    const details = stderr || stdout || `${command} exited with ${result.status}`;
    throw new Error(details);
  }

  return typeof result.stdout === "string" ? result.stdout.trim() : "";
}

function hostTriple() {
  return run(rustcCommand(), ["--print", "host-tuple"]);
}

function rustcCommand() {
  if (process.env.RUSTC) {
    return process.env.RUSTC;
  }

  if (process.platform === "win32" && process.env.USERPROFILE) {
    const userRustc = path.join(process.env.USERPROFILE, ".cargo", "bin", "rustc.exe");
    if (existsSync(userRustc)) {
      return userRustc;
    }
  }

  return "rustc";
}

function buildSidecar() {
  if (!existsSync(entryPath)) {
    throw new Error(`backend sidecar entry not found: ${entryPath}`);
  }

  mkdirSync(binariesDir, { recursive: true });
  mkdirSync(pyinstallerWorkDir, { recursive: true });
  mkdirSync(pyinstallerSpecDir, { recursive: true });

  const targetTriple = hostTriple();
  const outputName = `yth-backend-${targetTriple}`;
  run(
    "pyinstaller",
    [
      "--onefile",
      "--clean",
      "--name",
      outputName,
      "--distpath",
      binariesDir,
      "--workpath",
      pyinstallerWorkDir,
      "--specpath",
      pyinstallerSpecDir,
      entryPath,
    ],
    {
      env: {
        ...process.env,
        PYTHONPATH: repoRoot,
      },
      stdio: "inherit",
    },
  );

  const executableName = process.platform === "win32" ? `${outputName}.exe` : outputName;
  console.log(path.join(binariesDir, executableName));
}

try {
  buildSidecar();
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
}
