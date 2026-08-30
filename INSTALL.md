# Install

## 1. Generate

Open the [wizard](https://3dprinting-noob.github.io/homeassistant-climate-brain/) (or `docs/index.html` from this repo). Fill:

- How many zones (1–8)
- Each zone’s `climate.*` entity
- Occupancy `binary_sensor` (people home only)
- Outdoor temperature sensor
- Optional humidity
- Optional travelers (direction + travel minutes)
- Comfort / away / night / Boost / vacation temperatures
- Whether to show a Vacation button

Download `climate_brain.yaml` and `climate_brain_dashboard.yaml`.

## 2. Home Assistant packages

Save the package as `config/packages/climate_brain.yaml`.

In `configuration.yaml`:

```yaml
homeassistant:
  packages: !include_dir_named packages

logger:
  default: warning
  logs:
    climate_brain: info
```

## 3. Only one writer

Disable any other automation that calls `climate.set_temperature` / `climate.set_hvac_mode` on those zones. If you used Versatile Thermostat, disable it. Cancel the thermostat’s own Auto schedule (wide 62/82 bands).

Occupied HVAC mode in the package is `heat_cool`. Never `auto`.

## 4. Restart

Full Home Assistant restart. YAML reload is not enough.

## 5. Dashboard

Paste `climate_brain_dashboard.yaml` as a new Lovelace dashboard (raw editor), or copy the cards into an existing view.

## 6. Confirm

- `input_boolean.climate_brain_enabled` is on
- Logs: Settings → System → Logs, logger `climate_brain` (File Editor hides `*.log`)
- Package automations cannot be edited in the UI. Do not click Migrate.

## Uninstall

1. Turn off `input_boolean.climate_brain_enabled`. Wait ~5 seconds.
2. Delete `config/packages/climate_brain.yaml`.
3. Full restart.
4. Purge leftover `climate_brain*` entities in Settings → Devices & Services → Entities.
