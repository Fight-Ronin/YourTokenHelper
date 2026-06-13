#!/usr/bin/env python3
"""Discover local coding-tool usage sources without storing transcript content."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any


SOURCE_KINDS = (
    "codex",
    "claude_code",
    "cursor",
    "gemini_cli",
    "github_copilot",
    "openai_api_cost",
)
JSON_SUFFIXES = {".json", ".jsonl", ".ndjson"}
SQLITE_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".vscdb"}
MAX_JSON_DEPTH = 8
MODEL_HINTS = ("model",)
TIME_HINTS = ("time", "timestamp", "created", "updated", "date")
SESSION_HINTS = ("session", "conversation", "thread", "workspace", "project")
SKIP_DIR_NAMES = {
    ".cache",
    ".git",
    "__pycache__",
    "cache",
    "Cache",
    "Code Cache",
    "GPUCache",
    "node_modules",
    "packages",
    "plugins",
    "skills",
}
SKIP_KEY_SUBSTRINGS = (
    "access_token",
    "accesstoken",
    "refresh_token",
    "refreshtoken",
    "id_token",
    "idtoken",
    "oauth",
    "auth",
    "captcha",
    "credential",
    "password",
    "private",
    "secret",
    "schema",
    "node_modules",
    "modelcontextprotocol",
    "electron-persisted-atom-state",
)
USAGE_TOKEN_KEY_SUBSTRINGS = (
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "cached_tokens",
    "cached_input_tokens",
    "cache_read_input_tokens",
    "cache_creation_input_tokens",
    "reasoning_tokens",
    "reasoning_output_tokens",
    "tokens_used",
    "totaltokens",
    "total_tokens",
    "token_usage",
    "total_token_usage",
    "last_token_usage",
    "usage_credits",
    "credits",
    "cost",
    "token_count",
)
USAGE_PARENT_KEYS = {
    "usage",
    "message.usage",
    "response.usage",
    "payload.info.last_token_usage",
    "payload.info.total_token_usage",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Discover local coding-tool usage source capability."
    )
    parser.add_argument(
        "--fixture-root",
        help="Use synthetic fixture directories instead of OS-specific local paths.",
    )
    parser.add_argument(
        "--output",
        help="Write redacted discovery report JSON to this path. Defaults to stdout.",
    )
    parser.add_argument(
        "--include-paths",
        action="store_true",
        help="Include full local paths in the report. Use only with ignored local output.",
    )
    parser.add_argument(
        "--max-files-per-source",
        type=int,
        default=500,
        help="Maximum candidate files to inspect per source.",
    )
    parser.add_argument(
        "--max-json-lines-per-file",
        type=int,
        default=20,
        help="Maximum JSONL lines to inspect per file.",
    )
    parser.add_argument(
        "--max-json-bytes",
        type=int,
        default=2_000_000,
        help="Maximum size of non-JSONL JSON files to inspect.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(args)
    write_report(report, args.output)


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    home = Path.home()
    env = env_paths()
    source_reports = []
    for source_kind in SOURCE_KINDS:
        source_reports.append(discover_source(source_kind, home, env, args))
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "host": {
            "os": platform.system(),
            "release": platform.release(),
            "python": platform.python_version(),
        },
        "privacy": {
            "stores_prompt_content": False,
            "stores_response_content": False,
            "stores_tool_output": False,
            "path_mode": "full" if args.include_paths else "redacted",
        },
        "sources": source_reports,
        "next_recommendation": recommend_next_source(source_reports),
    }


def env_paths() -> dict[str, Path | None]:
    return {
        "APPDATA": Path(os.environ["APPDATA"]) if os.environ.get("APPDATA") else None,
        "LOCALAPPDATA": Path(os.environ["LOCALAPPDATA"])
        if os.environ.get("LOCALAPPDATA")
        else None,
        "XDG_CONFIG_HOME": Path(os.environ["XDG_CONFIG_HOME"])
        if os.environ.get("XDG_CONFIG_HOME")
        else None,
    }


def discover_source(
    source_kind: str,
    home: Path,
    env: dict[str, Path | None],
    args: argparse.Namespace,
) -> dict[str, Any]:
    if source_kind == "openai_api_cost":
        return discover_api_cost_source()

    candidates = (
        fixture_candidates(source_kind, args.fixture_root)
        if args.fixture_root
        else os_candidates(source_kind, home, env)
    )
    scan_candidates = prune_nested_existing_roots(candidates)
    candidate_reports = []
    permission_denied = False
    for candidate in scan_candidates:
        candidate_reports.append(scan_candidate(source_kind, candidate, args))
        permission_denied = permission_denied or candidate_reports[-1]["status"] == "permission-denied"

    existing_reports = [item for item in candidate_reports if item["exists"]]
    token_key_count = sum(len(item["token_keys"]) for item in existing_reports)
    model_key_count = sum(len(item["model_keys"]) for item in existing_reports)
    time_key_count = sum(len(item["time_keys"]) for item in existing_reports)
    sqlite_table_count = sum(len(item["sqlite_tables"]) for item in existing_reports)
    candidate_file_count = sum(item["candidate_file_count"] for item in existing_reports)

    if not existing_reports:
        status = "not-found"
    elif permission_denied and candidate_file_count == 0:
        status = "permission-denied"
    elif token_key_count and (model_key_count or time_key_count):
        status = "ready"
    elif token_key_count or sqlite_table_count or candidate_file_count:
        status = "needs-parser"
    else:
        status = "manual-only"

    return {
        "source_kind": source_kind,
        "status": status,
        "candidate_roots": [format_path(item["path"], args.include_paths, home) for item in candidate_reports],
        "existing_root_count": len(existing_reports),
        "candidate_file_count": candidate_file_count,
        "file_extensions": sorted(
            {ext for item in existing_reports for ext in item["file_extensions"]}
        ),
        "token_keys": sorted({key for item in existing_reports for key in item["token_keys"]}),
        "model_keys": sorted({key for item in existing_reports for key in item["model_keys"]}),
        "time_keys": sorted({key for item in existing_reports for key in item["time_keys"]}),
        "session_keys": sorted({key for item in existing_reports for key in item["session_keys"]}),
        "sqlite_tables": sorted({key for item in existing_reports for key in item["sqlite_tables"]}),
        "notes": source_notes(source_kind, status),
    }


def discover_api_cost_source() -> dict[str, Any]:
    has_api_key = env_var_present("OPENAI_API_KEY")
    has_admin_key = env_var_present("OPENAI_ADMIN_KEY")
    return {
        "source_kind": "openai_api_cost",
        "status": "secondary-source",
        "candidate_roots": [],
        "existing_root_count": 0,
        "candidate_file_count": 0,
        "file_extensions": [],
        "token_keys": [],
        "model_keys": [],
        "time_keys": [],
        "session_keys": [],
        "sqlite_tables": [],
        "safe_env_presence": {
            "OPENAI_API_KEY": has_api_key,
            "OPENAI_ADMIN_KEY": has_admin_key,
        },
        "notes": [
            "API cost source is secondary and requires official API access.",
            "Do not use this source as the default personal coding-tool path.",
        ],
    }


def fixture_candidates(source_kind: str, fixture_root: str) -> list[Path]:
    root = Path(fixture_root)
    return {
        "codex": [root / "codex"],
        "claude_code": [root / "claude_code"],
        "cursor": [root / "cursor"],
        "gemini_cli": [root / "gemini_cli"],
        "github_copilot": [root / "github_copilot"],
    }.get(source_kind, [])


def os_candidates(source_kind: str, home: Path, env: dict[str, Path | None]) -> list[Path]:
    appdata = env.get("APPDATA")
    localappdata = env.get("LOCALAPPDATA")
    xdg_config = env.get("XDG_CONFIG_HOME") or (home / ".config")
    if source_kind == "codex":
        return compact_paths(
            [
                home / ".codex" / "sessions",
                home / ".codex",
                appdata / "Codex" if appdata else None,
                appdata / "OpenAI" / "Codex" if appdata else None,
                localappdata / "Codex" if localappdata else None,
                home / "Library" / "Application Support" / "Codex",
                xdg_config / "codex",
            ]
        )
    if source_kind == "claude_code":
        return compact_paths(
            [
                home / ".claude" / "projects",
                home / ".claude",
                xdg_config / "claude" / "projects",
                xdg_config / "claude",
                appdata / "Claude" if appdata else None,
                appdata / "Claude Code" if appdata else None,
                home / "Library" / "Application Support" / "Claude",
                home / "Library" / "Application Support" / "Claude Code",
            ]
        )
    if source_kind == "cursor":
        return compact_paths(
            [
                appdata / "Cursor" / "User" / "globalStorage" if appdata else None,
                appdata / "Cursor" / "User" / "workspaceStorage" if appdata else None,
                appdata / "Cursor" / "User" / "History" if appdata else None,
                localappdata / "Cursor" if localappdata else None,
                home / "Library" / "Application Support" / "Cursor" / "User" / "globalStorage",
                home / "Library" / "Application Support" / "Cursor" / "User" / "workspaceStorage",
                xdg_config / "Cursor" / "User" / "globalStorage",
                xdg_config / "Cursor" / "User" / "workspaceStorage",
            ]
        )
    if source_kind == "gemini_cli":
        return compact_paths(
            [
                Path.cwd() / ".gemini",
                home / ".gemini",
                xdg_config / "gemini",
                appdata / "Gemini CLI" if appdata else None,
                localappdata / "Gemini CLI" if localappdata else None,
            ]
        )
    if source_kind == "github_copilot":
        return compact_paths(
            [
                appdata / "Code" / "User" / "globalStorage" / "github.copilot"
                if appdata
                else None,
                appdata / "Code" / "User" / "globalStorage" / "github.copilot-chat"
                if appdata
                else None,
                appdata / "Cursor" / "User" / "globalStorage" / "github.copilot"
                if appdata
                else None,
                appdata / "Cursor" / "User" / "globalStorage" / "github.copilot-chat"
                if appdata
                else None,
                home
                / "Library"
                / "Application Support"
                / "Code"
                / "User"
                / "globalStorage"
                / "github.copilot",
                home
                / "Library"
                / "Application Support"
                / "Code"
                / "User"
                / "globalStorage"
                / "github.copilot-chat",
                xdg_config / "Code" / "User" / "globalStorage" / "github.copilot",
                xdg_config / "Code" / "User" / "globalStorage" / "github.copilot-chat",
            ]
        )
    return []


def compact_paths(paths: list[Path | None]) -> list[Path]:
    seen = set()
    result = []
    for path in paths:
        if path is None:
            continue
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result


def prune_nested_existing_roots(paths: list[Path]) -> list[Path]:
    existing: list[Path] = []
    missing: list[Path] = []
    for path in paths:
        if path.exists():
            existing.append(path)
        else:
            missing.append(path)

    pruned: list[Path] = []
    resolved_existing = [(path, safe_resolve(path)) for path in existing]
    for path, resolved in resolved_existing:
        has_existing_parent = any(
            other_resolved != resolved and is_relative_to(resolved, other_resolved)
            for _other_path, other_resolved in resolved_existing
        )
        if not has_existing_parent:
            pruned.append(path)
    return pruned + missing


def safe_resolve(path: Path) -> Path:
    try:
        return path.resolve()
    except OSError:
        return path.absolute()


def is_relative_to(path: Path, possible_parent: Path) -> bool:
    try:
        path.relative_to(possible_parent)
        return True
    except ValueError:
        return False


def scan_candidate(source_kind: str, path: Path, args: argparse.Namespace) -> dict[str, Any]:
    report = {
        "source_kind": source_kind,
        "path": path,
        "exists": path.exists(),
        "status": "not-found",
        "candidate_file_count": 0,
        "file_extensions": [],
        "token_keys": [],
        "model_keys": [],
        "time_keys": [],
        "session_keys": [],
        "sqlite_tables": [],
    }
    if not report["exists"]:
        return report
    try:
        files = candidate_files(path, args.max_files_per_source)
    except PermissionError:
        report["status"] = "permission-denied"
        return report

    key_counter: Counter[str] = Counter()
    sqlite_tables: set[str] = set()
    extensions: set[str] = set()
    for file_path in files:
        extensions.add(file_path.suffix.lower())
        try:
            if is_json_record_file(file_path):
                key_counter.update(
                    sample_json_keys(
                        file_path,
                        args.max_json_lines_per_file,
                        args.max_json_bytes,
                    )
                )
            elif file_path.suffix.lower() in SQLITE_SUFFIXES:
                tables, columns = sample_sqlite_schema(file_path)
                sqlite_tables.update(tables)
                key_counter.update(columns)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, sqlite3.Error):
            continue

    report["status"] = "scanned"
    report["candidate_file_count"] = len(files)
    report["file_extensions"] = sorted(extensions)
    report["token_keys"] = usage_token_keys(key_counter)
    report["model_keys"] = model_keys(key_counter)
    report["time_keys"] = matching_keys(key_counter, TIME_HINTS)
    report["session_keys"] = matching_keys(key_counter, SESSION_HINTS)
    report["sqlite_tables"] = sorted(sqlite_tables)[:100]
    return report


def candidate_files(root: Path, max_files: int) -> list[Path]:
    if root.is_file():
        return [root] if is_candidate_file(root) else []
    files: list[Path] = []
    for current_root, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIR_NAMES]
        for filename in filenames:
            path = Path(current_root) / filename
            if is_candidate_file(path):
                files.append(path)
                if len(files) >= max_files:
                    return files
    return files


def is_candidate_file(path: Path) -> bool:
    suffix = path.suffix.lower()
    if suffix in JSON_SUFFIXES or suffix in SQLITE_SUFFIXES:
        return True
    return path.name in {"state.vscdb", "state.vscdb.backup", "telemetry.log"}


def is_json_record_file(path: Path) -> bool:
    return path.suffix.lower() in JSON_SUFFIXES or path.name == "telemetry.log"


def sample_json_keys(path: Path, max_lines: int, max_json_bytes: int) -> Counter[str]:
    counter: Counter[str] = Counter()
    if path.suffix.lower() in {".jsonl", ".ndjson"} or path.name == "telemetry.log":
        with path.open("r", encoding="utf-8") as handle:
            for index, line in enumerate(handle):
                if index >= max_lines:
                    break
                line = line.strip()
                if not line:
                    continue
                value = json.loads(line)
                collect_keys(value, counter)
        return counter

    if path.stat().st_size > max_json_bytes:
        return counter
    value = json.loads(path.read_text(encoding="utf-8"))
    collect_keys(value, counter)
    return counter


def sample_sqlite_schema(path: Path) -> tuple[set[str], Counter[str]]:
    tables: set[str] = set()
    columns: Counter[str] = Counter()
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        for (table_name,) in rows:
            tables.add(table_name)
            try:
                for column in connection.execute(f"PRAGMA table_info({quote_identifier(table_name)})"):
                    columns[str(column[1])] += 1
            except sqlite3.Error:
                continue
    finally:
        connection.close()
    return tables, columns


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def collect_keys(
    value: Any,
    counter: Counter[str],
    prefix: str = "",
    depth: int = 0,
) -> None:
    if depth > MAX_JSON_DEPTH:
        return
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            dotted = f"{prefix}.{key_text}" if prefix else key_text
            counter[dotted] += 1
            collect_keys(item, counter, dotted, depth + 1)
    elif isinstance(value, list):
        for item in value[:10]:
            collect_keys(item, counter, prefix, depth + 1)


def matching_keys(counter: Counter[str], hints: tuple[str, ...]) -> list[str]:
    matches = []
    for key, _count in counter.most_common():
        if should_skip_key(key):
            continue
        lowered = key.lower()
        if any(hint in lowered for hint in hints):
            matches.append(key)
        if len(matches) >= 50:
            break
    return sorted(matches)


def usage_token_keys(counter: Counter[str]) -> list[str]:
    matches = []
    for key, _count in counter.most_common():
        if should_skip_key(key):
            continue
        lowered = key.lower()
        compact = lowered.replace("_", "").replace("-", "")
        if "time_to_first_token" in lowered or "token_budget" in lowered:
            continue
        if (
            lowered in USAGE_PARENT_KEYS
            or lowered.endswith(".usage")
            or any(hint in lowered for hint in USAGE_TOKEN_KEY_SUBSTRINGS)
            or "totaltokens" in compact
        ):
            matches.append(key)
        if len(matches) >= 50:
            break
    return sorted(matches)


def model_keys(counter: Counter[str]) -> list[str]:
    matches = []
    for key, _count in counter.most_common():
        if should_skip_key(key):
            continue
        lowered = key.lower()
        compact = lowered.replace("_", "").replace("-", "")
        last_segment = lowered.rsplit(".", 1)[-1]
        if last_segment == "model" or compact.endswith("defaultmodel"):
            matches.append(key)
        if len(matches) >= 30:
            break
    return sorted(matches)


def should_skip_key(key: str) -> bool:
    lowered = key.lower()
    compact = lowered.replace("_", "").replace("-", "")
    return any(skip in lowered or skip in compact for skip in SKIP_KEY_SUBSTRINGS)


def env_var_present(name: str) -> bool:
    if os.environ.get(name):
        return True
    pattern = re.compile(rf"^\s*{re.escape(name)}\s*=")
    for path in (Path(".env.local"), Path(".env")):
        if not path.exists():
            continue
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if pattern.match(line):
                    return True
        except OSError:
            continue
    return False


def format_path(path: Path, include_paths: bool, home: Path) -> str:
    if include_paths:
        return str(path)
    try:
        relative = path.relative_to(home)
        return "~/" + relative.as_posix()
    except ValueError:
        digest = hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:12]
        return f"redacted_path_{digest}"


def source_notes(source_kind: str, status: str) -> list[str]:
    notes = []
    if source_kind == "cursor":
        notes.append("Cursor is expected to need extra validation; local usage shape is not assumed.")
    if source_kind == "gemini_cli":
        notes.append("Gemini CLI telemetry can include prompt/response text; parsers must whitelist aggregate fields only.")
    if source_kind == "github_copilot":
        notes.append("GitHub Copilot personal local token access is not assumed; official metrics are org/enterprise/report oriented.")
    if status == "ready":
        notes.append("Usage-like keys were found; next step is fixture-driven parser tests.")
    elif status == "needs-parser":
        notes.append("Candidate data exists, but parser readiness needs source-specific inspection.")
    elif status == "manual-only":
        notes.append("Source exists but usage-bearing fields were not observed.")
    elif status == "not-found":
        notes.append("No likely local data directory was found.")
    return notes


def recommend_next_source(source_reports: list[dict[str, Any]]) -> str:
    ready = [item["source_kind"] for item in source_reports if item["status"] == "ready"]
    if ready:
        return f"Start parser fixtures for: {', '.join(ready)}."
    needs_parser = [
        item["source_kind"] for item in source_reports if item["status"] == "needs-parser"
    ]
    if needs_parser:
        return f"Inspect source-specific shape for: {', '.join(needs_parser)}."
    return "No local parser target is ready yet; use sample data and manual allowance setup."


def write_report(report: dict[str, Any], output: str | None) -> None:
    encoded = json.dumps(report, indent=2, sort_keys=True)
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(encoded + "\n", encoding="utf-8")
        print(f"Wrote redacted local source report to {path}")
    else:
        print(encoded)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
