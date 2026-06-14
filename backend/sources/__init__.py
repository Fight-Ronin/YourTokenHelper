"""Source adapter contracts and first-party source adapters."""

from backend.sources.adapters import (
    ClaudeCodeFixtureAdapter,
    CodexFixtureAdapter,
    ManualStatusAdapter,
)
from backend.sources.base import (
    SOURCE_STATUSES,
    SourceAdapter,
    SourceState,
    SyncResult,
    sync_source_adapter,
)
from backend.sources.commands import (
    PRIMARY_REFRESH_COMMAND_NAME,
    PrimaryRefreshCommandError,
    PrimaryRefreshCommandRequest,
    build_primary_refresh_command_payload,
    build_primary_refresh_command_payload_from_request,
    build_primary_refresh_command_response_from_json,
    build_primary_refresh_command_response_from_mapping,
    build_primary_refresh_command_response_json,
    primary_jsonl_candidates,
    primary_refresh_command_error_to_payload,
    primary_refresh_command_request_from_mapping,
)
from backend.sources.refresh_command_cli import run_primary_refresh_command_io
from backend.sources.discovery import (
    DiscoveredJsonlSource,
    JsonlSourceCandidate,
    discover_jsonl_source,
    discover_jsonl_sources,
    jsonl_adapter_for_candidate,
)
from backend.sources.jsonl_usage import (
    ClaudeCodeJsonlAdapter,
    CodexJsonlAdapter,
    read_usage_jsonl_events,
)
from backend.sources.registry import (
    PRIMARY_LOCAL_SOURCE_KINDS,
    build_primary_source_adapters,
    setup_status_adapter,
)
from backend.sources.refresh import (
    refresh_results_to_payload,
    refresh_source_adapters,
    refresh_sources_summary_payload,
    sync_result_to_payload,
)

__all__ = [
    "SOURCE_STATUSES",
    "ClaudeCodeFixtureAdapter",
    "ClaudeCodeJsonlAdapter",
    "CodexFixtureAdapter",
    "CodexJsonlAdapter",
    "DiscoveredJsonlSource",
    "JsonlSourceCandidate",
    "ManualStatusAdapter",
    "PRIMARY_LOCAL_SOURCE_KINDS",
    "PRIMARY_REFRESH_COMMAND_NAME",
    "PrimaryRefreshCommandError",
    "PrimaryRefreshCommandRequest",
    "SourceAdapter",
    "SourceState",
    "SyncResult",
    "build_primary_source_adapters",
    "build_primary_refresh_command_payload",
    "build_primary_refresh_command_payload_from_request",
    "build_primary_refresh_command_response_from_json",
    "build_primary_refresh_command_response_from_mapping",
    "build_primary_refresh_command_response_json",
    "discover_jsonl_source",
    "discover_jsonl_sources",
    "jsonl_adapter_for_candidate",
    "primary_jsonl_candidates",
    "primary_refresh_command_error_to_payload",
    "primary_refresh_command_request_from_mapping",
    "read_usage_jsonl_events",
    "refresh_results_to_payload",
    "refresh_source_adapters",
    "refresh_sources_summary_payload",
    "setup_status_adapter",
    "sync_result_to_payload",
    "sync_source_adapter",
    "run_primary_refresh_command_io",
]
