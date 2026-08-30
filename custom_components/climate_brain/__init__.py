"""Climate Brain Home Assistant integration — sole writer for climate.* zones."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, LOGGER_NAME, PLATFORMS
from .coordinator import ClimateBrainCoordinator
from .dashboard import build_dashboard_yaml

try:
    CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
except AttributeError:
    # Home Assistant < 2024.1
    CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN) if hasattr(cv, "empty_config_schema") else {}

_LOGGER = logging.getLogger(LOGGER_NAME)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    coordinator = ClimateBrainCoordinator(hass, entry)
    await coordinator.async_setup()
    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await coordinator.async_start()

    async def _generate(call: ServiceCall) -> None:
        yaml_text = build_dashboard_yaml(hass, entry, coordinator)
        path = Path(hass.config.path("climate_brain_dashboard.yaml"))

        def _write() -> None:
            path.write_text(yaml_text, encoding="utf-8")

        await hass.async_add_executor_job(_write)
        _LOGGER.info("Wrote %s", path)

    if not hass.services.has_service(DOMAIN, "generate_dashboard"):
        hass.services.async_register(DOMAIN, "generate_dashboard", _generate)

    entry.async_on_unload(entry.add_update_listener(_reload))
    return True


async def _reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator: ClimateBrainCoordinator | None = hass.data.get(DOMAIN, {}).pop(
        entry.entry_id, None
    )
    if coordinator:
        await coordinator.async_unload()
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and not hass.data.get(DOMAIN):
        hass.services.async_remove(DOMAIN, "generate_dashboard")
    return unload_ok
