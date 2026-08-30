"""Buttons owned by Climate Brain."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ClimateBrainCoordinator
from .entity import ClimateBrainEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: ClimateBrainCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            ClimateBrainButton(coordinator, "save_zone", "Save zone", "mdi:content-save"),
            ClimateBrainButton(
                coordinator, "zone_defaults", "Zone defaults", "mdi:restore"
            ),
        ]
    )


class ClimateBrainButton(ClimateBrainEntity, ButtonEntity):
    def __init__(
        self, coordinator: ClimateBrainCoordinator, key: str, name: str, icon: str
    ) -> None:
        super().__init__(coordinator, key)
        self._attr_name = name
        self._attr_icon = icon
        self.entity_id = f"button.{DOMAIN}_{key}"
        self._event = key

    async def async_press(self) -> None:
        await self.coordinator.async_button(self._event)
