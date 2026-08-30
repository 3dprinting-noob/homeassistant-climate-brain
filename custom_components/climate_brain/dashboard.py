"""Lovelace dashboard YAML (built-in cards only)."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_OCCUPANCY, CONF_PEOPLE, CONF_TESLAS, CONF_ZONES, DISCONNECT_TEXT, DOMAIN
from .coordinator import ClimateBrainCoordinator, slugify


def _indent(lines: list[str], n: int = 6) -> str:
    pad = " " * n
    return "\n".join(pad + line for line in lines)


def build_dashboard_yaml(
    hass: HomeAssistant, entry: ConfigEntry, coordinator: ClimateBrainCoordinator
) -> str:
    cfg = coordinator.cfg()
    zones = list(cfg.get(CONF_ZONES) or [])
    occupancy = cfg.get(CONF_OCCUPANCY) or ""
    people = list(cfg.get(CONF_PEOPLE) or [])
    teslas = list(cfg.get(CONF_TESLAS) or [])
    n = max(1, len(zones))
    travel_on = bool(people or teslas)

    zone_cards = []
    for z in zones:
        zone_cards.append(_indent(["- type: thermostat", f"  entity: {z}"]))

    brain = [
        "- type: entities",
        "  title: Brain",
        "  show_header_toggle: false",
        "  entities:",
        f"    - {occupancy}",
    ]
    if travel_on:
        brain.append(f"    - switch.{DOMAIN}_phase2")
    brain.extend(
        [
            f"    - switch.{DOMAIN}_vacation",
            f"    - number.{DOMAIN}_vacation_heat",
            f"    - number.{DOMAIN}_vacation_cool",
            f"    - sensor.{DOMAIN}_period",
            f"    - sensor.{DOMAIN}_status",
            f"    - select.{DOMAIN}_latched_season",
            f"    - datetime.{DOMAIN}_night_start",
            f"    - datetime.{DOMAIN}_morning_z2",
            f"    - datetime.{DOMAIN}_morning_z1",
            f"    - datetime.{DOMAIN}_day_start",
        ]
    )

    setp = [
        "- type: entities",
        "  title: Setpoints",
        "  show_header_toggle: false",
        "  entities:",
        f"    - number.{DOMAIN}_comfort_heat",
        f"    - number.{DOMAIN}_comfort_cool",
        f"    - number.{DOMAIN}_away_heat",
        f"    - number.{DOMAIN}_away_cool",
        f"    - number.{DOMAIN}_boost_heat",
        f"    - number.{DOMAIN}_boost_cool",
    ]
    for i in range(1, n + 1):
        setp.append(f"    - number.{DOMAIN}_z{i}_night_heat")
        setp.append(f"    - number.{DOMAIN}_z{i}_night_cool")

    travel_block = ""
    if people or teslas:
        ents = [
            "- type: entities",
            "  title: Travel",
            "  show_header_toggle: false",
            "  entities:",
        ]
        for p in people:
            ents.append("    - type: section")
            ents.append(f"      label: {p.get('name') or 'Person'}")
            if p.get("dir"):
                ents.append(f"    - {p['dir']}")
            if p.get("eta"):
                ents.append(f"    - {p['eta']}")
            if p.get("tracker"):
                ents.append(f"    - {p['tracker']}")
        for c in teslas:
            name = c.get("name") or "car"
            ents.append("    - type: section")
            ents.append(f"      label: Tesla {name}")
            if c.get("location"):
                ents.append(f"    - {c['location']}")
            if c.get("route"):
                ents.append(f"    - {c['route']}")
            if c.get("tta"):
                ents.append(f"    - {c['tta']}")
            if c.get("distance"):
                ents.append(f"    - {c['distance']}")
            ents.append(f"    - sensor.{DOMAIN}_tesla_{slugify(name)}_direction")
        travel_block = "\n" + _indent(ents)

    editor = [
        "- type: entities",
        "  title: Zone editor — pick a zone, change the numbers, Save overwrites that zone",
        "  show_header_toggle: false",
        "  entities:",
        f"    - select.{DOMAIN}_edit_zone",
        f"    - number.{DOMAIN}_edit_comfort_heat",
        f"    - number.{DOMAIN}_edit_comfort_cool",
        f"    - number.{DOMAIN}_edit_away_heat",
        f"    - number.{DOMAIN}_edit_away_cool",
        f"    - number.{DOMAIN}_edit_boost_heat",
        f"    - number.{DOMAIN}_edit_boost_cool",
        f"    - number.{DOMAIN}_edit_night_heat",
        f"    - number.{DOMAIN}_edit_night_cool",
        f"    - button.{DOMAIN}_save_zone",
        f"    - button.{DOMAIN}_zone_defaults",
    ]
    power = [
        "- type: entities",
        "  title: Occupied HVAC / control",
        "  show_header_toggle: false",
        "  entities:",
        f"    - select.{DOMAIN}_home_hvac",
    ]
    # Confirming TILE is the disconnect UI — do not put enabled on the Brain list.
    quoted = DISCONNECT_TEXT.replace('"', '\\"')
    tile = [
        "- type: tile",
        f"  entity: switch.{DOMAIN}_enabled",
        "  name: Climate Brain HVAC",
        "  icon: mdi:thermostat",
        "  tap_action:",
        "    action: toggle",
        "    confirmation:",
        f'      text: "{quoted}"',
    ]
    return f"""# Climate Brain 1.5.0 dashboard — paste this as a Lovelace dashboard (raw editor).
# Built-in cards only. Occupancy is your sensor; Climate Brain does not create it.
# Tesla is travel only. The HVAC tile asks before you disconnect.
# Do not put the HVAC connection switch on a generic Brain list — use this tile.
# Call the climate_brain.generate_dashboard service to rewrite this file.

title: Climate
views:
  - title: Climate
    path: climate
    cards:
{chr(10).join(zone_cards)}
{_indent(brain)}
{_indent(setp)}{travel_block}
{_indent(editor)}
{_indent(power)}
{_indent(tile)}
"""
