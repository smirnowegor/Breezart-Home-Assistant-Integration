"""Constants for Breezart integration."""

DOMAIN = "breezart"
DEFAULT_NAME = "Breezart"

# Breezart TCP connection settings
DEFAULT_PORT = 1560
DEFAULT_TIMEOUT = 5
DEFAULT_UNIT_ID = 1
DEFAULT_SCAN_INTERVAL = 30

# Register addresses (based on breezart-client/homebridge-breezart)
REG_STATUS = 11
REG_CURRENT_TEMP = 13
REG_FAN_SPEED_CURRENT = 17
REG_WATER_TEMP = 62
REG_OUTDOOR_TEMP = 60

REG_FAN_SPEED_SET = 0
REG_TARGET_TEMP = 1
REG_POWER = 3
REG_PASSWORD = 100

# Status codes
STATUS_MAP = {
    0: "Выключено",
    1: "Работа",
    2: "Ожидание",
    3: "Разогрев",
    4: "Охлаждение",
    5: "Вентиляция",
}
