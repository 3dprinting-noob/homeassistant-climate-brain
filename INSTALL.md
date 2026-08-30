# Install

Climate Brain is the **only** writer allowed on the climates you enter. It will fight anything else that still sets those thermostats.

## Delete other thermostat controllers first

Do this **before** you paste the package. Disable is not enough if they still run on restart.

Remove or delete completely:

- Versatile Thermostat instances on those zones (`climate.home_thermostat*`, VTherm helpers, VTherm presence)
- Other HA climate automations / scripts / Node-RED flows that call `climate.set_temperature`, `climate.set_hvac_mode`, `climate.set_preset_mode`, or `versatile_thermostat.*`
- Generic Thermostat / Dual Smart Thermostat / Better Thermostat wrapping the same equipment
- The HVAC’s own app schedule (Trane Home / Nexia **Auto** schedule, 62/82, weekly programs)
- Old arrival / ETA / night-Eco packages that write the same `climate.*` entities

Leave the climate entities themselves. Delete the *controllers*, not the Trane / Nexia zones.

If two writers remain, the house oscillates.

## 1. Generate

Open the [wizard](https://3dprinting-noob.github.io/homeassistant-climate-brain/) (or `docs/index.html`). Fill zones, occupancy, outdoor, temps, sleep/morning clocks, optional travel, optional vacation button.

Click **Generate**. The chaos checker must report **INSTALL OK**. Do not download a FAIL package.

## 2. Home Assistant packages

Save as `config/packages/climate_brain.yaml`.

```yaml
homeassistant:
  packages: !include_dir_named packages

logger:
  default: warning
  logs:
    climate_brain: info
```

## 3. Occupied mode

Occupied HVAC is `heat_cool`. Never `auto`.

## 4. Restart

Full Home Assistant restart. YAML reload is not enough.

## 5. Dashboard

Paste `climate_brain_dashboard.yaml` as a Lovelace dashboard (raw editor).

## 6. Confirm

- `input_boolean.climate_brain_enabled` is on
- Logs: Settings → System → Logs, logger `climate_brain`
- Package automations cannot be edited in the UI. Do not click Migrate.

## Uninstall

1. Turn off `input_boolean.climate_brain_enabled`. Wait ~5 seconds.
2. Delete `config/packages/climate_brain.yaml`.
3. Full restart.
4. Purge leftover `climate_brain*` entities.
