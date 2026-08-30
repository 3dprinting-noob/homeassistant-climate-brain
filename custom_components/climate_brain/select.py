"""Selects owned by Climate Brain."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, HVAC_OPTIONS, LATCH_OPTIONS
from .coordinator import ClimateBrainCoordinator
from .entity import ClimateBrainEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: ClimateBrainCoordinator = hass.data[DOMAIN][entry.entry_id]
    n = coordinator.engine.n_zones
    async_add_entities(
        [
            HomeHvacSelect(coordinator),
            LatchSelect(coordinator),
            EditZoneSelect(coordinator, n),
        ]
    )


class HomeHvacSelect(ClimateBrainEntity, SelectEntity, RestoreEntity):
    def __init__(self, coordinator: ClimateBrainCoordinator) -> None:
        super().__init__(coordinator, "home_hvac")
        self._attr_name = "Occupied HVAC mode"
        self._attr_icon = "mdi:tune"
        self._attr_options = list(HVAC_OPTIONS)
        self._attr_current_option = coordinator.engine.home_hvac
        self.entity_id = f"select.{DOMAIN}_home_hvac"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last and last.state in HVAC_OPTIONS:
            self._attr_current_option = last.state

    @property
    def current_option(self) -> str | None:
        return self.coordinator.engine.home_hvac

    async def async_select_option(self, option: str) -> None:
        if option == "auto" or option not in HVAC_OPTIONS:
            option = "heat_cool"
        self.coordinator.engine.home_hvac = option
        self._attr_current_option = option
        self.async_write_ha_state()
        await self.coordinator.async_handle("home_hvac")


class LatchSelect(ClimateBrainEntity, SelectEntity, RestoreEntity):
    def __init__(self, coordinator: ClimateBrainCoordinator) -> None:
        super().__init__(coordinator, "latched_season")
        self._attr_name = "Latched season"
        self._attr_icon = "mdi:sun-snowflake"
        self._attr_options = list(LATCH_OPTIONS)
        self.entity_id = f"select.{DOMAIN}_latched_season"

    @property
    def current_option(self) -> str | None:
        latch = self.coordinator.engine.latch
        return latch if latch in LATCH_OPTIONS else "heat"

    async def async_select_option(self, option: str) -> None:
        if option not in LATCH_OPTIONS:
            return
        self.coordinator.engine.latch = option
        self.async_write_ha_state()
        await self.coordinator.async_handle("latch")


class EditZoneSelect(ClimateBrainEntity, SelectEntity):
    def __init__(self, coordinator: ClimateBrainCoordinator, n: int) -> None:
        super().__init__(coordinator, "edit_zone")
        self._attr_name = "Edit zone"
        self._attr_icon = "mdi:home-edit"
        self._attr_options = [str(i) for i in range(1, n + 1)]
        self.entity_id = f"select.{DOMAIN}_edit_zone"

    @property
    def current_option(self) -> str | None:
        return str(self.coordinator.engine.edit_zone)

    async def async_select_option(self, option: str) -> None:
        try:
            self.coordinator.engine.edit_zone = int(option)
        except ValueError:
            return
        self.async_write_ha_state()
        await self.coordinator.async_handle("load_zone")
