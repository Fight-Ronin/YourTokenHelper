# OpenAI Probe Fixtures

This directory holds sanitized sample responses for the PR 1 API spike.

Rules:

- Do not store real API keys.
- Do not store raw live API responses.
- Replace or hash `api_key_id`, `project_id`, `user_id`, organization IDs, and request IDs.
- Keep model names and aggregate token/cost numbers when they are useful for UI mocks.

`sample_probe_response.json` is synthetic. It exists so the probe script and future UI mock can run without network access.

`sample_admin_api_keys_response.json` is synthetic and follows the public Admin
API Keys list response shape. It intentionally contains fixture key names,
redacted values, owners, and raw key IDs so backend monitor tests can prove
those fields are not returned in UI/command payloads.
