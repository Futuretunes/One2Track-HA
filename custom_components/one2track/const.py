"""Constants for the One2Track GPS integration."""

DOMAIN = "one2track"

CONF_ACCOUNT_ID = "account_id"

BASE_URL = "https://www.one2trackgps.com"
LOGIN_PATH = "/auth/users/sign_in"

DEFAULT_UPDATE_INTERVAL = 60  # seconds

# Command codes
CMD_REFRESH_LOCATION = "0039"
CMD_FIND_DEVICE = "1015"
CMD_REMOTE_SHUTDOWN = "0048"
CMD_SET_SOS_NUMBER = "0001"
CMD_FACTORY_RESET = "0011"
CMD_SET_ALARMS = "0057"
CMD_CHANGE_PASSWORD = "0067"
CMD_GPS_INTERVAL_UP = "0077"
CMD_GPS_INTERVAL_MOVE = "0078"
CMD_STEP_COUNTER_MOVE = "0079"
CMD_WHITELIST_1 = "0080"
CMD_WHITELIST_2 = "0081"
CMD_STEP_COUNTER_UP = "0082"
CMD_INTERCOM = "0084"
CMD_LANGUAGE_TIMEZONE = "0124"
CMD_QUIET_TIMES = "1107"
CMD_PROFILE_MODE = "1116"
CMD_PHONEBOOK = "1315"

# GPS interval command codes (any of these)
CMD_GPS_INTERVALS = {CMD_GPS_INTERVAL_UP, CMD_GPS_INTERVAL_MOVE}

# Step counter command codes (any of these)
CMD_STEP_COUNTERS = {CMD_STEP_COUNTER_MOVE, CMD_STEP_COUNTER_UP}

# GPS interval values
GPS_INTERVAL_OPTIONS = {
    "10": "10 seconds",
    "300": "5 minutes",
    "600": "10 minutes",
}

# Known device model IDs to names
DEVICE_MODELS = {
    27: "Connect MOVE",
    77: "Connect UP",
}

# Stale location threshold in minutes
STALE_LOCATION_MINUTES = 30
