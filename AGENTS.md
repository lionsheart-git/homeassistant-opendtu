# Agent Notes

This repository is a Home Assistant custom integration for a local OpenDTU device.

- Integration domain: `opendtu`
- Integration package: `custom_components/opendtu`
- Local development entrypoint: `scripts/develop`
- Lint/format command: `scripts/lint`
- Devcontainer setup: rebuild the devcontainer, then run `scripts/setup` if dependencies need refreshing.
- In the devcontainer, Home Assistant is installed into the project `.venv` by `uv`; use `uv run hass` or `scripts/develop` instead of calling a global `hass` binary.
- Home Assistant is served on port `8123` by `scripts/develop`; the devcontainer forwards that port.
- The integration polls unauthenticated OpenDTU REST API endpoints only:
  `/api/livedata/status`, `/api/livedata/status?inv=<serial>`,
  `/api/eventlog/status?inv=<serial>`, `/api/limit/status`,
  `/api/mqtt/status`, `/api/network/status`, `/api/ntp/status`,
  `/api/power/status`, and `/api/system/status`.
- `/api/prometheus/metrics`, authenticated APIs, and POST APIs are intentionally
  out of scope for now.
- DTU-level endpoint data belongs on the `OpenDTU` device. Inverter-specific
  data belongs on each inverter device.

Keep changes scoped to the Home Assistant integration unless the task explicitly asks for repository maintenance.
