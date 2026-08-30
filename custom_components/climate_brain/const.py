"""Climate Brain constants."""

from __future__ import annotations

DOMAIN = "climate_brain"
UNIQUE_ID = "climate_brain"
VERSION = "1.5.0"
LOGGER_NAME = "climate_brain"

PLATFORMS = [
    "switch",
    "number",
    "select",
    "sensor",
    "button",
    "datetime",
]

CONF_ZONES = "zones"
CONF_OCCUPANCY = "occupancy"
CONF_OUTDOOR = "outdoor"
CONF_INDEPENDENT_ZONES = "independent_zones"
CONF_HOME_HVAC = "home_hvac"
CONF_PEOPLE = "people"
CONF_TESLAS = "teslas"
CONF_PERSON_NAME = "name"
CONF_PERSON_DIR = "dir"
CONF_PERSON_ETA = "eta"
CONF_PERSON_TRACKER = "tracker"
CONF_TESLA_NAME = "name"
CONF_TESLA_LOCATION = "location"
CONF_TESLA_ROUTE = "route"
CONF_TESLA_TTA = "tta"
CONF_TESLA_DISTANCE = "distance"
CONF_COMFORT_HEAT = "comfort_heat"
CONF_COMFORT_COOL = "comfort_cool"
CONF_AWAY_HEAT = "away_heat"
CONF_AWAY_COOL = "away_cool"
CONF_BOOST_HEAT = "boost_heat"
CONF_BOOST_COOL = "boost_cool"
CONF_VACATION_HEAT = "vacation_heat"
CONF_VACATION_COOL = "vacation_cool"
CONF_NIGHT_START = "night_start"
CONF_MORNING_Z2 = "morning_z2"
CONF_MORNING_Z1 = "morning_z1"
CONF_DAY_START = "day_start"
CONF_ADD_ANOTHER = "add_another"
CONF_SKIP = "skip"

DEFAULT_COMFORT_HEAT = 71.0
DEFAULT_COMFORT_COOL = 74.0
DEFAULT_AWAY_HEAT = 65.0
DEFAULT_AWAY_COOL = 78.0
DEFAULT_BOOST_HEAT = 73.0
DEFAULT_BOOST_COOL = 70.0
DEFAULT_VACATION_HEAT = 55.0
DEFAULT_VACATION_COOL = 80.0
DEFAULT_NIGHT_START = "22:30:00"
DEFAULT_MORNING_Z2 = "05:15:00"
DEFAULT_MORNING_Z1 = "05:45:00"
DEFAULT_DAY_START = "06:15:00"
DEFAULT_HOME_HVAC = "heat_cool"
DEFAULT_DEBOUNCE_MIN = 3
DEFAULT_EMPTY_MIN = 15
DEFAULT_LOCKOUT_MIN = 10
DEFAULT_LATE_HOLD_MIN = 60
DEFAULT_BOOST_MIN = 30
DEFAULT_PRECOOL_SAFETY_MIN = 120
DEFAULT_VACATION_BOOST_MIN = 120
DEFAULT_WATCHDOG_SEC = 45

HVAC_OPTIONS = ["heat", "cool", "heat_cool"]
LATCH_OPTIONS = ["heat", "cool"]

DISCONNECT_TEXT = (
    "Disconnect Climate Brain? It will stop changing the thermostats. "
    "The HVAC keeps running on the Trane / Nexia thermostat schedule. "
    "The last temperatures stay until that schedule or a wall control changes them."
)

ATTR_CONFIRMATION = "confirmation"
ATTR_DISCONNECT_PROMPT = "disconnect_prompt"
ATTR_SCHEDULE_NOTE = "schedule_note"
