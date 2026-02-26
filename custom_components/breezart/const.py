"""Constants for Breezart integration."""

DOMAIN = "breezart"
DEFAULT_NAME = "Breezart"

# Breezart TCP connection settings
DEFAULT_PORT = 1560
DEFAULT_TIMEOUT = 5
DEFAULT_SCAN_INTERVAL = 30

# Protocol delimiter
DELIMITER = "_"

# Request types (native Breezart TCP protocol)
REQ_GET_PROPERTIES = "VPr07"
REQ_GET_STATE = "VSt07"
REQ_GET_SENSORS = "VSens"
REQ_SET_POWER = "VWPwr"
REQ_SET_TEMP = "VWTmp"
REQ_SET_FAN_SPEED = "VWSpd"
REQ_SET_MODE = "VWFtr"

# Response types
RESP_STATE = "VSt07"
RESP_SENSORS = "VSens"
RESP_PROPERTIES = "VPr07"
RESP_OK = "OK"

# Error prefixes from Breezart device
ERROR_PREFIX = {
    "VEPas": "Wrong password",
    "VEFrm": "Wrong format of request",
    "VECd1": "Request of type 1 not found",
    "VECd2": "Request of type 2 not found",
    "VEDat": "Error in request data",
}

# Power states
POWER_ON = 1
POWER_OFF = 0

# Sensor value indicating "no data"
NO_DATA_VALUE = 0xFB07

# UnitState values
UNIT_STATE_MAP = {
    0: "Выключено",
    1: "Включено",
    2: "Выключение",
    3: "Включение",
}

# Mode values
MODE_MAP = {
    0: "Обогрев",
    1: "Охлаждение",
    2: "Авто-Обогрев",
    3: "Авто-Охлаждение",
    4: "Вентиляция",
    5: "Выключено",
}

# ModeSet values (requested/set mode)
MODE_SET_MAP = {
    1: "Обогрев",
    2: "Охлаждение",
    3: "Авто",
    4: "Вентиляция",
}

# ColorMsg / ColorInd
COLOR_MSG_MAP = {
    0: "Норма",
    1: "Предупреждение",
    2: "Ошибка",
}

COLOR_IND_MAP = {
    0: "Выключено",
    1: "Переходный процесс",
    2: "Включено",
}
