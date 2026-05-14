# Agent Notes

This repository is a Home Assistant custom integration for a local OpenDTU device.

- Integration domain: `opendtu`
- Integration package: `custom_components/opendtu`
- Local development entrypoint: `scripts/develop`
- Lint/format command: `scripts/lint`
- Devcontainer setup: rebuild the devcontainer, then run `scripts/setup` if dependencies need refreshing.
- In the devcontainer, Home Assistant is installed into the project `.venv` by `uv`; use `uv run hass` or `scripts/develop` instead of calling a global `hass` binary.
- Home Assistant is served on port `8123` by `scripts/develop`; the devcontainer forwards that port.
- The integration is intended to poll the local OpenDTU REST API, starting with `/api/livedata/status`.

Keep changes scoped to the Home Assistant integration unless the task explicitly asks for repository maintenance.
