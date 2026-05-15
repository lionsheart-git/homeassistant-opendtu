# Configuration

The config flow asks for the local OpenDTU host. The host may be a DNS name, IP
address, or URL. The integration uses that value for the REST API and for the
OpenDTU device configuration URL.

## Options

OpenDTU exposes two polling options:

- **HA update interval** controls live production data polling. The default is
  30 seconds.
- **Diagnostic update interval** controls optional status, event, limit, MQTT,
  network, NTP, power, and system endpoints. The default is 300 seconds.

When a live update happens before diagnostics are due, the coordinator reuses
the most recent diagnostic payload so diagnostic entities keep their last known
state.

## Devices

The top-level OpenDTU device uses the network hostname reported by OpenDTU when
available. Inverter devices use stable serial-number based names such as
`Inverter 112184742793`.

Hardware identity that belongs on a device, such as MAC address, chip model,
chip revision, firmware version, inverter serial number, inverter model, and
inverter hardware version, is stored in Home Assistant device metadata.
