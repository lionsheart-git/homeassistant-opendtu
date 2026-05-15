"""
Constants shared by OpenDTU integration modules.

The constants in this module define the Home Assistant integration domain,
attribution string, config option names, and supported polling interval bounds.
"""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "opendtu"
ATTRIBUTION = "Data provided by local OpenDTU REST API"

DEFAULT_SCAN_INTERVAL_SECONDS = 30
MIN_SCAN_INTERVAL_SECONDS = 5
MAX_SCAN_INTERVAL_SECONDS = 3600

CONF_DIAGNOSTIC_SCAN_INTERVAL = "diagnostic_scan_interval"
DEFAULT_DIAGNOSTIC_SCAN_INTERVAL_SECONDS = 300
MIN_DIAGNOSTIC_SCAN_INTERVAL_SECONDS = 30
MAX_DIAGNOSTIC_SCAN_INTERVAL_SECONDS = 86400
