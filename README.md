# Climate Brain

A Home Assistant **integration** (and a YAML package generator) for communicating HVAC zones (Trane Link / Nexia-style heat and cool). One program writes the thermostats. Never a second brain. Never `auto`. Never a new `climate.climate_brain*` entity.

Names like Comfort, Eco, Boost, and Away are **inspired by [Versatile Thermostat](https://github.com/jmcollin78/versatile_thermostat)**. Climate Brain talks to the HVAC climates itself. It does not install VTherm. Versatile Thermostat is name inspiration only.

**Credit:** GrokAI.

This is **not** in the default HACS store. You add it as a custom repository.

| Docs | |
| --- | --- |
| [Prerequisites](PREREQUISITES.md) | What you need: Home Assistant, occupancy, optional travel |
| [Install](INSTALL.md) | HACS integration first, YAML wizard second |
| [Changelog](CHANGELOG.md) | Integration 1.5.0 / generator 0.1.13 / YAML package 1.4.1 |

## Two ways to install

**Recommended — HACS integration 1.5.0**

1. HACS → Integrations → three dots → Custom repositories.
2. Paste `https://github.com/3dprinting-noob/homeassistant-climate-brain`
3. Category: **Integration** → Add.
4. Download Climate Brain. Restart Home Assistant.
5. Settings → Devices & Services → Add Integration → Climate Brain. Pick your climate zones and occupancy sensor.

Climate Brain is then the sole writer to those `climate.*` zones.

**Or YAML package 1.4.1**

Open the [wizard](https://3dprinting-noob.github.io/homeassistant-climate-brain/) (or `docs/index.html`). It builds a YAML file for `config/packages/`. Same HVAC rules. You paste the file yourself.

## What it does

Default clock: night 10:30 p.m. · zone 2 morning 5:15 a.m. · zone 1 morning 5:45 a.m. · day 6:15 a.m.

- Occupancy waits a short time so a phone flicker does not look like you left. After 15 minutes empty, the house goes Away. If occupancy is unknown, it will not switch to Away. Occupancy is people/phones only. A Tesla is never occupancy.
- When people are home, at night, or in a late-arrival hold: heat and cool together (two temperatures).
- When empty, on vacation, in Boost, or in precool: one heat **or** one cool temperature. Never inverted dual Boost (a hot house cooling at 70, a cold house heating at 73). Never `hvac_mode` auto.
- Season latch ±1 around 65°F: cool at 66 and up, heat at 64 and down, 65 stays put.
- 1–8 zones, one brain. Each zone can have its own comfort, away, Boost, and night if Independent zones is on.
- Optional arrival precool from direction + minutes left. Precool only starts while occupancy is off. Occupancy on cancels it.
- Tesla is travel only. Location home → inhome. Navigation to home with minutes left → toward. Navigation elsewhere → away. No nav uses falling/rising distance to `zone.home` (about 80 meters). An empty destination is not automatically away.
- The HVAC connection tile asks before you disconnect (`Disconnect Climate Brain?` / `Trane / Nexia thermostat schedule`). Climate Brain stops changing the thermostats. Last temperatures stay. The thermostat schedule can run again. It does not call `climate.turn_off`.
- Vacation on uses vacation temperatures. Vacation off starts a Boost even if the house is empty.

## Other controllers

Delete other thermostat programs completely before you install. Climate Brain will fight VTherm, Generic Thermostat, HVAC app schedules, and any automation still calling `climate.set_*` on those zones.

## Quick start

1. Read [PREREQUISITES.md](PREREQUISITES.md).
2. Follow [INSTALL.md](INSTALL.md) (HACS first).
3. Do a full Home Assistant restart.

## License

MIT
