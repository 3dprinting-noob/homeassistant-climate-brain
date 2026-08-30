# Climate Brain

Home Assistant **package** for communicating HVAC zones (Trane Link / Nexia-style `heat_cool` climates). One writer. Never a second brain. Never `auto`.

Temperature vocabulary (Comfort / Eco / Boost / Away) is **inspired by [Versatile Thermostat](https://github.com/jmcollin78/versatile_thermostat)**. Climate Brain writes communicating HVAC climates directly — VTherm is not installed.

**Attributes:** GrokAI.

This repo is a **generator**. You type your entities. It stamps Climate Brain **v1.3.3** plus Lovelace cards. It does not contain anyone’s household YAML.

**Wizard:** [open it](https://3dprinting-noob.github.io/homeassistant-climate-brain/) or serve `docs/index.html`.

| Docs | |
| --- | --- |
| [Prerequisites](PREREQUISITES.md) | HA, occupancy, optional travel |
| [Install](INSTALL.md) | Generate → package → restart |
| [Changelog](CHANGELOG.md) | 0.1.0 generator / 1.3.3 package |

Not a HACS *integration* yet (no `custom_components/`). Install is paste-the-YAML.

## What it does

Clock: night 22:30 · zone 2 morning 05:15 · zone 1 morning 05:45 · day 06:15.

- Occupancy debounce, 15-minute empty confirm. Unknown occupancy never Away.
- Occupied / night / late hold = `heat_cool` dual setpoints.
- Empty / vacation / Boost / precool = latched heat **or** cool + one temperature.
- 1–8 zones, one brain. Comfort / away / Boost / vacation are house-wide. Night sliders are per zone.
- Optional arrival precool from direction + ETA. Tesla is travel only, never occupancy.
- Vacation helper. Dashboard can hide the button if you do not want it.

## Other controllers

Delete other thermostat controllers completely before install. Climate Brain will fight VTherm, Generic Thermostat, HVAC app schedules, and any automation still calling `climate.set_*` on those zones.

## Quick start

1. Read [PREREQUISITES.md](PREREQUISITES.md).
2. Follow [INSTALL.md](INSTALL.md).
3. Full Home Assistant restart.

## License

MIT
