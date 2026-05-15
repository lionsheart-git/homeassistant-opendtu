# Architecture

## Modules

- `api.py` contains the asynchronous OpenDTU REST client.
- `coordinator.py` owns the Home Assistant data update cadence.
- `entity.py` contains shared device metadata and naming helpers.
- `sensor.py` creates total, inverter, measurement, and diagnostic sensors.
- `binary_sensor.py` creates hint, inverter status, and diagnostic binary
  sensors.
- `config_flow.py` contains the UI setup and options flows.
- `naming.py` contains shared friendly-name and diagnostic filtering rules.

## Data Flow

The coordinator calls `OpenDtuApiClient.async_get_data()`. The client always
fetches `/api/livedata/status` and inverter live details. When diagnostics are
due, it also fetches optional DTU status endpoints, inverter event logs, and
limit status.

Entity descriptions are generated from the first successful coordinator payload.
Static descriptions cover core values, while dynamic descriptions are generated
from OpenDTU measurement and status payloads.

## Device Hierarchy

The integration creates:

- one OpenDTU device;
- one inverter device for each inverter reported by OpenDTU.

Inverter devices are linked to the OpenDTU device through Home Assistant
`via_device` metadata.
