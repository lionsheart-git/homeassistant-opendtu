"""Naming helpers for OpenDTU entities."""

from __future__ import annotations

DTU_STATUS_LABELS = {
    "mqtt": "MQTT",
    "network": "Network",
    "ntp": "NTP",
    "power": "Power",
    "system": "System",
}

LABEL_PARTS = {
    "ac": "AC",
    "ca": "CA",
    "cpu": "CPU",
    "dc": "DC",
    "dhcp": "DHCP",
    "dns": "DNS",
    "dtu": "DTU",
    "ip": "IP",
    "ipv4": "IPv4",
    "ipv6": "IPv6",
    "led": "LED",
    "mqtt": "MQTT",
    "ntp": "NTP",
    "ram": "RAM",
    "rssi": "RSSI",
    "ssl": "SSL",
    "tls": "TLS",
    "url": "URL",
    "wifi": "Wi-Fi",
}

IGNORED_DTU_STATUS_PATHS = {
    ("network", "hostname"),
    ("network", "network_hostname"),
    ("network", "ap_hostname"),
    ("network", "host_name"),
    ("network", "mac"),
    ("network", "mac_address"),
    ("network", "wifi_mac"),
    ("network", "sta_mac"),
    ("system", "chipmodel"),
    ("system", "chip_model"),
    ("system", "chip"),
    ("system", "chiprevision"),
    ("system", "chip_revision"),
    ("system", "dtu_serial"),
    ("system", "dtu_serial_number"),
    ("system", "firmware_version"),
    ("system", "git_hash"),
    ("system", "pioenv"),
    ("system", "pio_environment"),
    ("system", "serial"),
    ("system", "serial_number"),
    ("system", "sw_version"),
    ("system", "task_details"),
    ("system", "tasks"),
    ("system", "version"),
}


def should_skip_dtu_status_path(endpoint: str, path: tuple[str, ...]) -> bool:
    """Return whether a DTU status path is too internal for HA entities."""
    normalized_path = tuple(part.casefold().replace("-", "_") for part in path)
    return any(
        endpoint.casefold() == ignored_endpoint
        and normalized_path[: len(ignored_path)] == tuple(ignored_path)
        for ignored_endpoint, *ignored_path in IGNORED_DTU_STATUS_PATHS
    ) or any(
        endpoint.casefold() == ignored_endpoint and ignored_path_part in normalized_path
        for ignored_endpoint, ignored_path_part in IGNORED_DTU_STATUS_PATHS
        if ignored_path_part in {"task_details", "tasks"}
    )


def format_dtu_status_name(endpoint: str, path: tuple[str, ...]) -> str:
    """Return a Home Assistant friendly DTU status entity name."""
    endpoint_label = DTU_STATUS_LABELS.get(endpoint, format_label_part(endpoint))
    path_label = " ".join(
        format_label_part(part) for part in _get_dtu_status_label_parts(endpoint, path)
    )
    if not path_label:
        return endpoint_label
    return f"{endpoint_label} {path_label}"


def format_label_part(value: str) -> str:
    """Return a human readable label part."""
    normalized = value.casefold()
    if normalized in LABEL_PARTS:
        return LABEL_PARTS[normalized]
    return value[:1].upper() + value[1:].lower()


def _get_dtu_status_label_parts(
    endpoint: str,
    path: tuple[str, ...],
) -> tuple[str, ...]:
    """Return path label parts without repeated endpoint prefixes."""
    endpoint_key = endpoint.casefold().replace("-", "_")
    label_parts: list[str] = []

    for raw_part in path:
        part = raw_part.casefold().replace("-", "_")
        if endpoint_key == "power" and part.isdecimal():
            label_parts.extend(("inverter", raw_part))
            continue

        split_parts = tuple(part for part in part.split("_") if part)
        if split_parts and split_parts[0] == endpoint_key:
            label_parts.extend(split_parts[1:])
            continue

        label_parts.extend(split_parts)

    return tuple(label_parts)
