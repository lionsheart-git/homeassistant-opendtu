"""Constants for opendtu."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "opendtu"
ATTRIBUTION = "Data provided by local OpenDTU REST API"

DEFAULT_SCAN_INTERVAL_SECONDS = 30
MIN_SCAN_INTERVAL_SECONDS = 5
MAX_SCAN_INTERVAL_SECONDS = 3600
