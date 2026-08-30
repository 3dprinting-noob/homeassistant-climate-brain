"""Sensors owned by Climate Brain."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_TESLAS, DOMAIN
from .coordinator import ClimateBrainCoordinator, slugify
from .entity import ClimateBrainEntity
from . import engine


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: ClimateBrainCoordinator = hass.data[DOMAIN][entry.entry_id]
    ents: list[SensorEntity] = [
        PeriodSensor(coordinator),
        StatusSensor(coordinator),
    ]
    for spec in coordinator.cfg().get(CONF_TESLAS) or []:
        name = spec.get("name") or "car"
        ents.append(TeslaDirectionSensor(coordinator, name))
    async_add_entities(ents)


class PeriodSensor(ClimateBrainEntity, SensorEntity):
    def __init__(self, coordinator: ClimateBrainCoordinator) -> None:
        super().__init__(coordinator, "period")
        self._attr_name = "Period"
        self._attr_icon = "mdi:clock-outline"
        self.entity_id = f"sensor.{DOMAIN}_period"

    @property
    def native_value(self) -> str:
        return engine.period_of(self.coordinator.engine)


class StatusSensor(ClimateBrainEntity, SensorEntity):
    def __init__(self, coordinator: ClimateBrainCoordinator) -> None:
        super().__init__(coordinator, "status")
        self._attr_name = "Status"
        self._attr_icon = "mdi:information-outline"
        self.entity_id = f"sensor.{DOMAIN}_status"

    @property
    def native_value(self) -> str:
        return (self.coordinator.engine.status or "idle")[:255]


class TeslaDirectionSensor(ClimateBrainEntity, SensorEntity):
    def __init__(self, coordinator: ClimateBrainCoordinator, name: str) -> None:
        slug = slugify(name)
        super().__init__(coordinator, f"tesla_{slug}_direction")
        self._slug = slug
        self._attr_name = f"Tesla {name} direction"
        self._attr_icon = "mdi:navigation-variant"
        self.entity_id = f"sensor.{DOMAIN}_tesla_{slug}_direction"

    @property
    def native_value(self) -> str:
        for car in self.coordinator.engine.teslas or []:
            if (car.slug or slugify(car.name)) == self._slug:
                d = engine.tesla_direction(car)
                return d if d in ("toward", "away", "inhome") else "away"
        return "away"
