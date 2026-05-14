# OpenDTU Home Assistant Integration

> [!CAUTION]
> I have done this project to get a better understanding of how to use coding agents. Most of the code in here
> was written by Codex. This project should not be seen as a production integration for the OpenDTU.

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

The first implemented API endpoint target is `/api/livedata/status`, which will
be used for OpenDTU status and production sensors.
