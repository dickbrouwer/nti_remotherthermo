from __future__ import annotations

from typing import Any

from homeassistant.const import Platform

DOMAIN = "nti_remotethermo"

BASE_URL = "https://www.nti.remotethermo.com"
REFRESH_PATH = "/R2/PlantMenu/Refresh"
SUBMIT_PATH = "/R2/PlantMenu/Submit"
COOKIE_NAME = ".AspNet.ApplicationCookie"

PLATFORMS = [Platform.SENSOR, Platform.NUMBER]

# Config entry data (set at initial setup)
CONF_CLIENT_ID = "client_id"
CONF_EMAIL = "email"
CONF_PASSWORD = "password"

LOGIN_PATH = "/R2/Account/Login"

# Options (editable after setup)
CONF_PARAM_IDS = "param_ids"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 300  # seconds
DEFAULT_PARAM_IDS = [
    "T8_3_0",
    "T8_3_1",
    "T8_3_2",
    "T8_3_4",
    "T8_3_5",
    "T8_2_8",
    "T8_4_0",
    "T8_7_8",
    "T8_7_9",
]


def normalize_param_ids(raw: Any) -> list[str]:
    """Parse a comma-separated string or list into a clean list of param IDs."""
    if raw is None:
        return []
    if isinstance(raw, str):
        return [p.strip() for p in raw.split(",") if p.strip()]
    if isinstance(raw, list):
        return [str(p).strip() for p in raw if str(p).strip()]
    return []
