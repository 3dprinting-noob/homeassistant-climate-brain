"""Switches owned by Climate Brain."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    ATTR_CONFIRMATION,
    ATTR_DISCONNECT_PROMPT,
    ATTR_SCHEDULE_NOTE,
    DISCONNECT_TEXT,
    DOMAIN,
)
from .coordinator import ClimateBrainCoordinator
from .entity import ClimateBrainEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: ClimateBrainCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            HvacConnectionSwitch(coordinator),
            ClimateBrainSwitch(coordinator, "vacation", "Vacation", False, "mdi:airplane"),
            ClimateBrainSwitch(
                coordinator, "phase2", "Arrival precool", True, "mdi:car-clock"
            ),
        ]
    )


class ClimateBrainSwitch(ClimateBrainEntity, SwitchEntity, RestoreEntity):
    def __init__(
        self,
        coordinator: ClimateBrainCoordinator,
        key: str,
        name: str,
        default: bool,
        icon: str,
    ) -> None:
        super().__init__(coordinator, key)
        self._attr_name = name
        self._attr_icon = icon
        self._attr_is_on = default
        self.entity_id = f"switch.{DOMAIN}_{key}"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None:
            self._attr_is_on = last.state == "on"

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._attr_is_on = False
        self.async_write_ha_state()


class HvacConnectionSwitch(ClimateBrainSwitch):
    """HVAC connection. Off stops writes; never climate.turn_off."""

    def __init__(self, coordinator: ClimateBrainCoordinator) -> None:
        super().__init__(
            coordinator, "enabled", "HVAC connection", True, "mdi:thermostat"
        )
        self._attr_translation_key = "enabled"

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        return {
            ATTR_CONFIRMATION: DISCONNECT_TEXT,
            ATTR_DISCONNECT_PROMPT: "Disconnect Climate Brain?",
            ATTR_SCHEDULE_NOTE: "Trane / Nexia thermostat schedule",
        }

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._attr_is_on = False
        self.async_write_ha_state()
        await self.coordinator.async_handle("hvac_off")

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._attr_is_on = True
        self.async_write_ha_state()
        await self.coordinator.async_handle("hvac_on")
