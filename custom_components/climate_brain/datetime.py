"""Clock datetime entities."""
from __future__ import annotations

from datetime import datetime, time

from homeassistant.components.datetime import DateTimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .const import (
    CONF_DAY_START,
    CONF_MORNING_Z1,
    CONF_MORNING_Z2,
    CONF_NIGHT_START,
    DEFAULT_DAY_START,
    DEFAULT_MORNING_Z1,
    DEFAULT_MORNING_Z2,
    DEFAULT_NIGHT_START,
    DOMAIN,
)
from .coordinator import ClimateBrainCoordinator
from .entity import ClimateBrainEntity

CLOCKS = (
    ("night_start", "Night start", CONF_NIGHT_START, DEFAULT_NIGHT_START, "mdi:weather-night"),
    ("morning_z2", "Morning zone 2", CONF_MORNING_Z2, DEFAULT_MORNING_Z2, "mdi:weather-sunset-up"),
    ("morning_z1", "Morning zone 1", CONF_MORNING_Z1, DEFAULT_MORNING_Z1, "mdi:weather-sunset-up"),
    ("day_start", "Day start", CONF_DAY_START, DEFAULT_DAY_START, "mdi:weather-sunny"),
)


def _parse_time(raw: str) -> time:
    parts = (raw or "00:00:00").split(":")
    try:
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        s = int(float(parts[2])) if len(parts) > 2 else 0
    except (TypeError, ValueError):
        h, m, s = 0, 0, 0
    return time(h % 24, m % 60, s % 60)


def _combine(t: time) -> datetime:
    now = dt_util.now()
    return now.replace(hour=t.hour, minute=t.minute, second=t.second, microsecond=0)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: ClimateBrainCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [ClockDateTime(coordinator, *row) for row in CLOCKS]
    )


class ClockDateTime(ClimateBrainEntity, DateTimeEntity, RestoreEntity):
    def __init__(
        self,
        coordinator: ClimateBrainCoordinator,
        key: str,
        name: str,
        cfg_key: str,
        default: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator, key)
        self._attr_name = name
        self._attr_icon = icon
        self.entity_id = f"datetime.{DOMAIN}_{key}"
        raw = coordinator.cfg().get(cfg_key) or default
        self._attr_native_value = _combine(_parse_time(str(raw)))

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last and last.state not in ("unknown", "unavailable"):
            parsed = dt_util.parse_datetime(last.state)
            if parsed is not None:
                self._attr_native_value = dt_util.as_local(parsed)

    async def async_set_value(self, value: datetime) -> None:
        if value.tzinfo is None:
            value = value.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        self._attr_native_value = dt_util.as_local(value)
        self.async_write_ha_state()
