# Prerequisites

## Home Assistant

- Home Assistant OS, Container, or Supervised, about 2024.10 or newer (2025/2026 is fine)
- You can restart Home Assistant
- HACS (for the recommended integration). The YAML wizard still needs `packages: !include_dir_named packages` in `configuration.yaml`

## HVAC

- Communicating / Nexia-style zone climates that accept heat and cool together (`heat_cool`). Trane Link is the tested family.
- One `climate.*` entity per zone (1–8)
- An outdoor temperature `sensor.*` in °F
- You are willing to let Climate Brain be the **only** program that writes those climates

Not required: Versatile Thermostat, Tesla, CAN bus, or an iPhone.

## Occupancy (required)

Climate Brain does **not** create occupancy. You make a Home Assistant `binary_sensor` that is **on when people are home** and **off when the house is empty**, then paste its entity ID into the HACS setup screen or the YAML wizard.

How to make one:

1. Settings → Devices & services → Helpers → Create helper.
2. **Group** → Binary sensor group if you already have on/off presence sensors. Or **Template** → Binary sensor.
3. Name it `Home occupancy`. The entity ID is usually `binary_sensor.home_occupancy`.
4. Template example using People: `{{ is_state('person.you','home') or is_state('person.partner','home') }}`
5. Developer tools → States: check that it flips when you leave and arrive.

Do not add cars (Tesla or otherwise) to occupancy. Tesla location, route, and “user present” are never occupancy. If occupancy is `unknown`, the brain will not switch to Away.

## Travel / start heating or cooling before you arrive (optional)

Only if you want arrival precool. Each traveler needs:

1. A direction sensor whose state includes `toward` when they are heading home
2. A travel-time sensor in minutes (or a duration string like `1 hour 15 min`)

Sources can be iCloud3, Android Companion travel sensors, OwnTracks, GPSLogger, Teslemetry (travel and arrival time only), and similar. An empty Tesla destination is not automatically away. A car in the driveway is inhome. If you skip travelers, occupancy still runs home, away, night, and vacation.

## Dashboard

Built-in Lovelace cards only. Mushroom is not required. HACS users: call the \`climate_brain.generate_dashboard\` service. The HVAC connection belongs on the confirming tile, not a generic Brain list.

## Logging

Optional but useful:

```yaml
logger:
  default: warning
  logs:
    climate_brain: info
```

## Credits

- Temperature names inspired by [Versatile Thermostat](https://github.com/jmcollin78/versatile_thermostat).
- Credit: GrokAI.
