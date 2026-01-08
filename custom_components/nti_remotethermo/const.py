DOMAIN = "nti_remotethermo"

BASE_URL = "https://www.nti.remotethermo.com"
REFRESH_PATH = "/R2/PlantMenu/Refresh"
COOKIE_NAME = ".AspNet.ApplicationCookie"

PLATFORMS = ["sensor"]

# Config entry data (set at initial setup)
CONF_CLIENT_ID = "client_id"
CONF_TOKEN = "token"

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
