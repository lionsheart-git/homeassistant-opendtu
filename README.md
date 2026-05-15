# OpenDTU Home Assistant Integration

> [!CAUTION]
> I have done this project to get a better understanding of how to use coding agents. Most of the code in here
> was written by Codex. Take this into account when using the integration.

Custom Home Assistant integration for polling a local OpenDTU REST API.

The integration domain is `opendtu` and the custom component lives in
`custom_components/opendtu`.

## Development

Install the UV-managed development environment, then use:

```bash
scripts/setup
scripts/lint
uv run ty check custom_components/opendtu
scripts/develop
```

Documentation is built with MkDocs:

```bash
scripts/docs
```

The documentation source lives in `docs/` and the generated API reference is
driven by Python docstrings through mkdocstrings.

## Supported OpenDTU APIs

The integration currently polls these unauthenticated read-only endpoints:

- `/api/livedata/status`
- `/api/livedata/status?inv=<serial>`
- `/api/eventlog/status?inv=<serial>`
- `/api/limit/status`
- `/api/mqtt/status`
- `/api/network/status`
- `/api/ntp/status`
- `/api/power/status`
- `/api/system/status`

The DTU-level status endpoints are exposed on the `OpenDTU` device as
diagnostic sensors/binary sensors. Inverter-specific data is exposed on the
corresponding inverter device.

The integration does not currently cover `/api/prometheus/metrics`,
authenticated APIs, or POST APIs.
