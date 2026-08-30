# Prerequisites

## Home Assistant

- Home Assistant OS / Container / Supervised, recent 2024.10+ (2025/2026 is fine)
- `packages: !include_dir_named packages` available in `configuration.yaml`
- Ability to restart HA

## HVAC

- Communicating / Nexia-style zone climates that accept `heat_cool` dual setpoints (Trane Link is the tested family)
- One `climate.*` entity per zone (1–8)
- An outdoor temperature `sensor.*` in °F
- You are willing to let Climate Brain be the **only** writer on those climates

Not required: Versatile Thermostat, Tesla, CAN bus, iPhone.

## Occupancy (required)

A `binary_sensor` that is **on when people are home** and **off when the house is empty**. Climate Brain does not create this.

Works with: Android Companion, iOS / iCloud3, Person groups, BLE / ESPresence, alarm panel, or a template you already trust.

Do not OR cars (Tesla or otherwise) into occupancy.

If occupancy is `unknown`, the brain will not write Away.

## Travel / arrival precool (optional)

Only if you want Phase 2. Each traveler needs:

1. A direction entity whose state contains `toward` when heading home
2. A travel-time entity in minutes (or a parseable duration string)

Sources can be iCloud3, Android Companion travel sensors + a toward template, OwnTracks, GPSLogger, etc. If you skip travelers, occupancy still runs home / away / night / vacation.

## Dashboard

Stock Lovelace cards only. Mushroom is not required.

## Logging

Optional but useful:

```yaml
logger:
  default: warning
  logs:
    climate_brain: info
```
