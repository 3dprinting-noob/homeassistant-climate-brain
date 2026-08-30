# Climate Brain

A Home Assistant **package** for communicating HVAC zones (Trane Link / Nexia-style heat and cool). One program writes the thermostats. Never a second brain. Never `auto`.

Names like Comfort, Eco, Boost, and Away are **inspired by [Versatile Thermostat](https://github.com/jmcollin78/versatile_thermostat)**. Climate Brain talks to the HVAC climates itself. It does not install VTherm.

**Credit:** GrokAI.

This repo is a **generator**. You type your Home Assistant entity IDs. It builds Climate Brain **v1.4.1** plus dashboard cards. It does not include anyone’s house YAML.

**Wizard:** [open it](https://3dprinting-noob.github.io/homeassistant-climate-brain/) or open `docs/index.html`.

| Docs | |
| --- | --- |
| [Prerequisites](PREREQUISITES.md) | What you need: Home Assistant, occupancy, optional travel |
| [Install](INSTALL.md) | Generate → paste the package → restart |
| [Changelog](CHANGELOG.md) | 0.1.10 generator / 1.4.1 package |

This is not a HACS *integration* yet (no `custom_components/` folder). You paste YAML.

## What it does

Default clock: night 10:30 p.m. · zone 2 morning 5:15 a.m. · zone 1 morning 5:45 a.m. · day 6:15 a.m.

- Occupancy waits a short time so a phone flicker does not look like you left. After 15 minutes empty, the house goes Away. If occupancy is unknown, it will not switch to Away.
- When people are home, at night, or in a late-arrival hold: heat and cool together (two temperatures).
- When empty, on vacation, in Boost, or in precool: one heat **or** one cool temperature.
- 1–8 zones, one brain. Each zone can have its own comfort, away, Boost, and night if Independent zones is on.
- Optional arrival precool from direction + minutes left. Tesla is travel only, never occupancy. An empty Tesla destination is not automatically away. A car in the driveway is inhome.
- The HVAC connection tile asks before you disconnect. Climate Brain stops changing the thermostats. The HVAC keeps running on the thermostat schedule. The last temperatures stay.
- Vacation helper. You can hide the dashboard button if you do not want it.

## Other controllers

Delete other thermostat programs completely before you install. Climate Brain will fight VTherm, Generic Thermostat, HVAC app schedules, and any automation still calling `climate.set_*` on those zones.

## Quick start

1. Read [PREREQUISITES.md](PREREQUISITES.md).
2. Follow [INSTALL.md](INSTALL.md).
3. Do a full Home Assistant restart.

## License

MIT
