# Installation

## HACS

This repository is structured for HACS as a custom integration. Release
artifacts contain the `opendtu` integration files in the archive layout expected
by HACS.

1. Add this repository as a custom repository in HACS.
2. Install the OpenDTU integration.
3. Restart Home Assistant.
4. Add OpenDTU from **Settings > Devices & services**.
5. Enter the local OpenDTU host, IP address, or URL.

## Manual Installation

Copy `custom_components/opendtu` into your Home Assistant
`custom_components` directory and restart Home Assistant.

The integration domain is `opendtu`.
