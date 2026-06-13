# Local Source Discovery Fixtures

These fixtures are synthetic and contain no real prompts, responses, tool output, code snippets, or account identifiers.

They exist to smoke-test `experiments/probes/local_source_discovery.py` and `experiments/probes/usage_event_parser.py` without reading local user data.

The Gemini CLI fixture mirrors telemetry shape but deliberately omits `request_text` and `response_text`.
