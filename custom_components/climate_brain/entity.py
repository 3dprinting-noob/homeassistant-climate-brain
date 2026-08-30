"""Shared entity helpers."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, VERSION
from .coordinator import ClimateBrainCoordinator


class ClimateBrainEntity(CoordinatorEntity[ClimateBrainCoordinator]):
    """Base entity attached to the Climate Brain device."""

    _attr_has_entity_name = True
    _attr_attribution = "GrokAI"

    def __init__(self, coordinator: ClimateBrainCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{DOMAIN}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name="Climate Brain",
            manufacturer="Climate Brain",
            model="HVAC hub",
            sw_version=VERSION,
        )
