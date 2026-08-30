"""Number entities owned by Climate Brain."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    DEFAULT_AWAY_COOL,
    DEFAULT_AWAY_HEAT,
    DEFAULT_BOOST_COOL,
    DEFAULT_BOOST_HEAT,
    DEFAULT_BOOST_MIN,
    DEFAULT_COMFORT_COOL,
    DEFAULT_COMFORT_HEAT,
    DEFAULT_DEBOUNCE_MIN,
    DEFAULT_EMPTY_MIN,
    DEFAULT_LATE_HOLD_MIN,
    DEFAULT_LOCKOUT_MIN,
    DEFAULT_VACATION_COOL,
    DEFAULT_VACATION_HEAT,
    DOMAIN,
)
from .coordinator import ClimateBrainCoordinator
from .entity import ClimateBrainEntity

# key, name, min, max, step, default, unit, icon, mode
HOUSE = (
    ("comfort_heat", "Comfort heat", 50, 90, 0.5, DEFAULT_COMFORT_HEAT, "°F", "mdi:thermometer", NumberMode.BOX),
    ("comfort_cool", "Comfort cool", 50, 90, 0.5, DEFAULT_COMFORT_COOL, "°F", "mdi:thermometer", NumberMode.BOX),
    ("away_heat", "Away heat", 50, 90, 0.5, DEFAULT_AWAY_HEAT, "°F", "mdi:thermometer", NumberMode.BOX),
    ("away_cool", "Away cool", 50, 90, 0.5, DEFAULT_AWAY_COOL, "°F", "mdi:thermometer", NumberMode.BOX),
    ("boost_heat", "Boost heat", 50, 90, 0.5, DEFAULT_BOOST_HEAT, "°F", "mdi:thermometer-chevron-up", NumberMode.BOX),
    ("boost_cool", "Boost cool", 50, 90, 0.5, DEFAULT_BOOST_COOL, "°F", "mdi:thermometer-chevron-down", NumberMode.BOX),
    ("vacation_heat", "Vacation heat", 50, 90, 0.5, DEFAULT_VACATION_HEAT, "°F", "mdi:airplane", NumberMode.SLIDER),
    ("vacation_cool", "Vacation cool", 50, 90, 0.5, DEFAULT_VACATION_COOL, "°F", "mdi:airplane", NumberMode.SLIDER),
    ("debounce_min", "Away debounce", 1, 15, 1, DEFAULT_DEBOUNCE_MIN, "min", "mdi:timer-sand", NumberMode.BOX),
    ("empty_min", "Real-empty confirm", 5, 60, 1, DEFAULT_EMPTY_MIN, "min", "mdi:timer-sand", NumberMode.BOX),
    ("lockout_min", "Arrival lockout", 5, 30, 5, DEFAULT_LOCKOUT_MIN, "min", "mdi:lock-clock", NumberMode.BOX),
    ("late_hold_min", "Late arrival hold", 10, 120, 5, DEFAULT_LATE_HOLD_MIN, "min", "mdi:timer", NumberMode.BOX),
    ("boost_min", "Morning Boost minutes", 10, 45, 5, DEFAULT_BOOST_MIN, "min", "mdi:timer", NumberMode.BOX),
)
EDIT = (
    ("edit_comfort_heat", "Edit comfort heat", 50, 90, 0.5, DEFAULT_COMFORT_HEAT),
    ("edit_comfort_cool", "Edit comfort cool", 50, 90, 0.5, DEFAULT_COMFORT_COOL),
    ("edit_away_heat", "Edit away heat", 50, 90, 0.5, DEFAULT_AWAY_HEAT),
    ("edit_away_cool", "Edit away cool", 50, 90, 0.5, DEFAULT_AWAY_COOL),
    ("edit_boost_heat", "Edit Boost heat", 50, 90, 0.5, DEFAULT_BOOST_HEAT),
    ("edit_boost_cool", "Edit Boost cool", 50, 90, 0.5, DEFAULT_BOOST_COOL),
    ("edit_night_heat", "Edit night heat", 50, 90, 0.5, 64.0),
    ("edit_night_cool", "Edit night cool", 50, 90, 0.5, 76.0),
)
ZONE_KINDS = (
    ("comfort_heat", "comfort heat", DEFAULT_COMFORT_HEAT),
    ("comfort_cool", "comfort cool", DEFAULT_COMFORT_COOL),
    ("away_heat", "away heat", DEFAULT_AWAY_HEAT),
    ("away_cool", "away cool", DEFAULT_AWAY_COOL),
    ("boost_heat", "Boost heat", DEFAULT_BOOST_HEAT),
    ("boost_cool", "Boost cool", DEFAULT_BOOST_COOL),
    ("night_heat", "night heat", None),
    ("night_cool", "night cool", None),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: ClimateBrainCoordinator = hass.data[DOMAIN][entry.entry_id]
    ents: list[NumberEntity] = []
    for row in HOUSE:
        ents.append(ClimateBrainNumber(coordinator, *row))
    for key, name, mn, mx, step, default in EDIT:
        ents.append(
            ClimateBrainNumber(
                coordinator,
                key,
                name,
                mn,
                mx,
                step,
                default,
                "°F",
                "mdi:thermometer",
                NumberMode.BOX,
            )
        )
    n = coordinator.engine.n_zones
    for i in range(1, n + 1):
        for kind, label, default in ZONE_KINDS:
            if kind == "night_heat":
                default = 64.0 if i == 1 else 65.0
            elif kind == "night_cool":
                default = 76.0 if i == 1 else 72.0
            ents.append(
                ClimateBrainNumber(
                    coordinator,
                    f"z{i}_{kind}",
                    f"Zone {i} {label}",
                    50,
                    90,
                    0.5,
                    float(default),
                    "°F",
                    "mdi:thermometer",
                    NumberMode.BOX,
                )
            )
    async_add_entities(ents)


class ClimateBrainNumber(ClimateBrainEntity, NumberEntity, RestoreEntity):
    def __init__(
        self,
        coordinator: ClimateBrainCoordinator,
        key: str,
        name: str,
        minimum: float,
        maximum: float,
        step: float,
        default: float,
        unit: str,
        icon: str,
        mode: NumberMode,
    ) -> None:
        super().__init__(coordinator, key)
        self._attr_name = name
        self._attr_icon = icon
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._attr_mode = mode
        cfg_val = coordinator.cfg().get(key)
        try:
            self._attr_native_value = float(cfg_val) if cfg_val is not None else float(default)
        except (TypeError, ValueError):
            self._attr_native_value = float(default)
        self.entity_id = f"number.{DOMAIN}_{key}"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None:
            try:
                self._attr_native_value = float(last.state)
            except (TypeError, ValueError):
                pass

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = float(value)
        self.async_write_ha_state()
