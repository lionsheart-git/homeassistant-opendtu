# OpenDTU Home Assistant Integration

This project is a Home Assistant custom integration for local OpenDTU devices.
It polls the OpenDTU REST API and exposes production, energy, inverter, and
diagnostic data as Home Assistant devices and entities.

The integration creates one OpenDTU device and one device for each inverter.
OpenDTU-level totals and diagnostics stay on the OpenDTU device. Inverter
measurements, event summaries, limit data, and status values stay on the
corresponding inverter device.

## Highlights

- Local polling through the OpenDTU REST API.
- Stable inverter devices based on serial numbers.
- OpenDTU device naming from the network hostname when available.
- Fast live-data polling with a separate, slower diagnostic polling interval.
- Diagnostic entities disabled by default when they are useful mainly for
  troubleshooting.
- HACS package generation and validation.

## API Scope

The integration currently covers unauthenticated read-only endpoints. It does
not implement authenticated endpoints, POST endpoints, or
`/api/prometheus/metrics`.
