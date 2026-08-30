"""Config and options flow for Climate Brain."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_ADD_ANOTHER,
    CONF_AWAY_COOL,
    CONF_AWAY_HEAT,
    CONF_BOOST_COOL,
    CONF_BOOST_HEAT,
    CONF_COMFORT_COOL,
    CONF_COMFORT_HEAT,
    CONF_DAY_START,
    CONF_HOME_HVAC,
    CONF_INDEPENDENT_ZONES,
    CONF_MORNING_Z1,
    CONF_MORNING_Z2,
    CONF_NIGHT_START,
    CONF_OCCUPANCY,
    CONF_OUTDOOR,
    CONF_PEOPLE,
    CONF_PERSON_DIR,
    CONF_PERSON_ETA,
    CONF_PERSON_NAME,
    CONF_PERSON_TRACKER,
    CONF_SKIP,
    CONF_TESLA_DISTANCE,
    CONF_TESLA_LOCATION,
    CONF_TESLA_NAME,
    CONF_TESLA_ROUTE,
    CONF_TESLA_TTA,
    CONF_TESLAS,
    CONF_VACATION_COOL,
    CONF_VACATION_HEAT,
    CONF_ZONES,
    DEFAULT_AWAY_COOL,
    DEFAULT_AWAY_HEAT,
    DEFAULT_BOOST_COOL,
    DEFAULT_BOOST_HEAT,
    DEFAULT_COMFORT_COOL,
    DEFAULT_COMFORT_HEAT,
    DEFAULT_DAY_START,
    DEFAULT_HOME_HVAC,
    DEFAULT_MORNING_Z1,
    DEFAULT_MORNING_Z2,
    DEFAULT_NIGHT_START,
    DEFAULT_VACATION_COOL,
    DEFAULT_VACATION_HEAT,
    DOMAIN,
    HVAC_OPTIONS,
    UNIQUE_ID,
)


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    return [str(v) for v in value if v]


def _user_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    d = defaults or {}
    zones_key = (
        vol.Required(CONF_ZONES, default=d[CONF_ZONES])
        if d.get(CONF_ZONES)
        else vol.Required(CONF_ZONES)
    )
    occ_key = (
        vol.Required(CONF_OCCUPANCY, default=d[CONF_OCCUPANCY])
        if d.get(CONF_OCCUPANCY)
        else vol.Required(CONF_OCCUPANCY)
    )
    out_key = (
        vol.Required(CONF_OUTDOOR, default=d[CONF_OUTDOOR])
        if d.get(CONF_OUTDOOR)
        else vol.Required(CONF_OUTDOOR)
    )
    return vol.Schema(
        {
            zones_key: selector.EntitySelector(
                selector.EntitySelectorConfig(domain="climate", multiple=True)
            ),
            occ_key: selector.EntitySelector(
                selector.EntitySelectorConfig(domain="binary_sensor")
            ),
            out_key: selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "weather"])
            ),
            vol.Optional(
                CONF_INDEPENDENT_ZONES,
                default=d.get(CONF_INDEPENDENT_ZONES, True),
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_HOME_HVAC, default=d.get(CONF_HOME_HVAC, DEFAULT_HOME_HVAC)
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=HVAC_OPTIONS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        }
    )


def _travel_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Optional(CONF_SKIP, default=False): selector.BooleanSelector(),
            vol.Optional(CONF_PERSON_NAME, default=""): selector.TextSelector(),
            vol.Optional(CONF_PERSON_DIR): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_PERSON_ETA): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_PERSON_TRACKER): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="device_tracker")
            ),
            vol.Optional(CONF_ADD_ANOTHER, default=False): selector.BooleanSelector(),
        }
    )


def _tesla_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Optional(CONF_SKIP, default=False): selector.BooleanSelector(),
            vol.Optional(CONF_TESLA_NAME, default=""): selector.TextSelector(),
            vol.Optional(CONF_TESLA_LOCATION): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="device_tracker")
            ),
            vol.Optional(CONF_TESLA_ROUTE): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["device_tracker", "sensor"])
            ),
            vol.Optional(CONF_TESLA_TTA): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_TESLA_DISTANCE): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_ADD_ANOTHER, default=False): selector.BooleanSelector(),
        }
    )


def _temp_selector() -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=50,
            max=90,
            step=0.5,
            unit_of_measurement="°F",
            mode=selector.NumberSelectorMode.BOX,
        )
    )


def _clocks_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    d = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_NIGHT_START, default=d.get(CONF_NIGHT_START, DEFAULT_NIGHT_START)
            ): selector.TimeSelector(),
            vol.Required(
                CONF_MORNING_Z2, default=d.get(CONF_MORNING_Z2, DEFAULT_MORNING_Z2)
            ): selector.TimeSelector(),
            vol.Required(
                CONF_MORNING_Z1, default=d.get(CONF_MORNING_Z1, DEFAULT_MORNING_Z1)
            ): selector.TimeSelector(),
            vol.Required(
                CONF_DAY_START, default=d.get(CONF_DAY_START, DEFAULT_DAY_START)
            ): selector.TimeSelector(),
            vol.Required(
                CONF_COMFORT_HEAT,
                default=d.get(CONF_COMFORT_HEAT, DEFAULT_COMFORT_HEAT),
            ): _temp_selector(),
            vol.Required(
                CONF_COMFORT_COOL,
                default=d.get(CONF_COMFORT_COOL, DEFAULT_COMFORT_COOL),
            ): _temp_selector(),
            vol.Required(
                CONF_AWAY_HEAT, default=d.get(CONF_AWAY_HEAT, DEFAULT_AWAY_HEAT)
            ): _temp_selector(),
            vol.Required(
                CONF_AWAY_COOL, default=d.get(CONF_AWAY_COOL, DEFAULT_AWAY_COOL)
            ): _temp_selector(),
            vol.Required(
                CONF_BOOST_HEAT, default=d.get(CONF_BOOST_HEAT, DEFAULT_BOOST_HEAT)
            ): _temp_selector(),
            vol.Required(
                CONF_BOOST_COOL, default=d.get(CONF_BOOST_COOL, DEFAULT_BOOST_COOL)
            ): _temp_selector(),
            vol.Required(
                CONF_VACATION_HEAT,
                default=d.get(CONF_VACATION_HEAT, DEFAULT_VACATION_HEAT),
            ): _temp_selector(),
            vol.Required(
                CONF_VACATION_COOL,
                default=d.get(CONF_VACATION_COOL, DEFAULT_VACATION_COOL),
            ): _temp_selector(),
        }
    )


class _FlowMixin:
    """Shared steps for config and options."""

    _data: dict[str, Any]
    _people: list[dict[str, Any]]
    _teslas: list[dict[str, Any]]
    _keep_people: bool
    _keep_teslas: bool
    _is_options: bool

    def _init_collectors(self) -> None:
        if getattr(self, "_data", None) is None:
            self._data = {}
            self._people = []
            self._teslas = []
            self._keep_people = False
            self._keep_teslas = False

    async def _step_user(self, user_input: dict[str, Any] | None) -> FlowResult:
        self._init_collectors()
        errors: dict[str, str] = {}
        if user_input is not None:
            zones = _as_list(user_input.get(CONF_ZONES))
            if not 1 <= len(zones) <= 8:
                errors[CONF_ZONES] = "zone_count"
            else:
                self._data[CONF_ZONES] = zones
                self._data[CONF_OCCUPANCY] = user_input[CONF_OCCUPANCY]
                self._data[CONF_OUTDOOR] = user_input[CONF_OUTDOOR]
                self._data[CONF_INDEPENDENT_ZONES] = bool(
                    user_input.get(CONF_INDEPENDENT_ZONES, True)
                )
                mode = str(user_input.get(CONF_HOME_HVAC) or DEFAULT_HOME_HVAC)
                if mode not in HVAC_OPTIONS:
                    mode = DEFAULT_HOME_HVAC
                self._data[CONF_HOME_HVAC] = mode
                return await self.async_step_travel()
        defaults = dict(self._data)
        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(defaults),
            errors=errors,
        )

    async def _step_travel(self, user_input: dict[str, Any] | None) -> FlowResult:
        self._init_collectors()
        if user_input is not None:
            if user_input.get(CONF_SKIP):
                self._keep_people = True
                return await self.async_step_tesla()
            name = (user_input.get(CONF_PERSON_NAME) or "").strip()
            direction = user_input.get(CONF_PERSON_DIR) or ""
            eta = user_input.get(CONF_PERSON_ETA) or ""
            tracker = user_input.get(CONF_PERSON_TRACKER) or ""
            if direction and eta:
                self._people.append(
                    {
                        CONF_PERSON_NAME: name or "person",
                        CONF_PERSON_DIR: direction,
                        CONF_PERSON_ETA: eta,
                        CONF_PERSON_TRACKER: tracker,
                    }
                )
                if user_input.get(CONF_ADD_ANOTHER):
                    return await self.async_step_travel()
            return await self.async_step_tesla()
        return self.async_show_form(step_id="travel", data_schema=_travel_schema())

    async def _step_tesla(self, user_input: dict[str, Any] | None) -> FlowResult:
        self._init_collectors()
        if user_input is not None:
            if user_input.get(CONF_SKIP):
                self._keep_teslas = True
                return await self.async_step_clocks()
            name = (user_input.get(CONF_TESLA_NAME) or "").strip()
            loc = user_input.get(CONF_TESLA_LOCATION) or ""
            route = user_input.get(CONF_TESLA_ROUTE) or ""
            tta = user_input.get(CONF_TESLA_TTA) or ""
            dist = user_input.get(CONF_TESLA_DISTANCE) or ""
            if loc or route or tta:
                self._teslas.append(
                    {
                        CONF_TESLA_NAME: name or "car",
                        CONF_TESLA_LOCATION: loc,
                        CONF_TESLA_ROUTE: route,
                        CONF_TESLA_TTA: tta,
                        CONF_TESLA_DISTANCE: dist,
                    }
                )
                if user_input.get(CONF_ADD_ANOTHER):
                    return await self.async_step_tesla()
            return await self.async_step_clocks()
        return self.async_show_form(step_id="tesla", data_schema=_tesla_schema())

    async def _step_clocks(self, user_input: dict[str, Any] | None) -> FlowResult:
        self._init_collectors()
        if user_input is not None:
            self._data.update(user_input)
            if not (self._is_options and self._keep_people):
                self._data[CONF_PEOPLE] = list(self._people)
            if not (self._is_options and self._keep_teslas):
                self._data[CONF_TESLAS] = list(self._teslas)
            return self._finish()
        return self.async_show_form(
            step_id="clocks", data_schema=_clocks_schema(self._data)
        )

    def _finish(self) -> FlowResult:
        raise NotImplementedError


class ClimateBrainConfigFlow(_FlowMixin, config_entries.ConfigFlow, domain=DOMAIN):
    """Single-instance config flow."""

    VERSION = 1
    _is_options = False

    def __init__(self) -> None:
        self._data = {}
        self._people = []
        self._teslas = []
        self._keep_people = False
        self._keep_teslas = False

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        await self.async_set_unique_id(UNIQUE_ID)
        self._abort_if_unique_id_configured()
        return await self._step_user(user_input)

    async def async_step_travel(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        return await self._step_travel(user_input)

    async def async_step_tesla(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        return await self._step_tesla(user_input)

    async def async_step_clocks(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        return await self._step_clocks(user_input)

    def _finish(self) -> FlowResult:
        self._data.setdefault(CONF_PEOPLE, list(self._people))
        self._data.setdefault(CONF_TESLAS, list(self._teslas))
        return self.async_create_entry(title="Climate Brain", data=self._data)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return ClimateBrainOptionsFlow(config_entry)


class ClimateBrainOptionsFlow(_FlowMixin, config_entries.OptionsFlow):
    """Change the same data later."""

    _is_options = True

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry
        src = {**config_entry.data, **(config_entry.options or {})}
        self._data = dict(src)
        self._people = []
        self._teslas = []
        self._keep_people = False
        self._keep_teslas = False

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        return await self._step_user(user_input)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        return await self._step_user(user_input)

    async def async_step_travel(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        return await self._step_travel(user_input)

    async def async_step_tesla(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        return await self._step_tesla(user_input)

    async def async_step_clocks(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        return await self._step_clocks(user_input)

    def _finish(self) -> FlowResult:
        src = {**self._entry.data, **(self._entry.options or {})}
        if self._keep_people:
            self._data[CONF_PEOPLE] = list(src.get(CONF_PEOPLE) or [])
        if self._keep_teslas:
            self._data[CONF_TESLAS] = list(src.get(CONF_TESLAS) or [])
        return self.async_create_entry(title="Climate Brain", data=self._data)
