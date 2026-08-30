# Install

Climate Brain must be the **only** program changing the climates you enter. If something else still sets those thermostats, they will fight.

## Delete other thermostat controllers first

Do this **before** you paste the package. Turning things off is not enough if they start again after a restart.

Remove or delete completely:

- Versatile Thermostat on those zones (`climate.home_thermostat*`, VTherm helpers, VTherm presence)
- Other Home Assistant automations, scripts, or Node-RED flows that call `climate.set_temperature`, `climate.set_hvac_mode`, `climate.set_preset_mode`, or `versatile_thermostat.*`
- Generic Thermostat, Dual Smart Thermostat, or Better Thermostat wrapping the same equipment
- The HVAC app’s own schedule (Trane Home / Nexia **Auto** schedule, 62/82, weekly programs)
- Old arrival / travel / night packages that write the same `climate.*` entities

Keep the climate entities themselves. Delete the extra *controllers*, not the Trane / Nexia zones.

If two programs both write, the house will bounce between temperatures.

## 1. Generate

Open the [wizard](https://3dprinting-noob.github.io/homeassistant-climate-brain/) (or `docs/index.html`). Entity fields start empty. Paste your Home Assistant IDs, or tap **Use default** if you already created helpers with those names. Occupancy is a binary sensor you create in Helpers first (see [PREREQUISITES.md](PREREQUISITES.md)). Then fill temperatures, sleep/morning times, optional travel, and the optional vacation button.

Click **Generate**. The checker must say **INSTALL OK**. Do not download a file that says FAIL.

## 2. Home Assistant packages

Save the file as `config/packages/climate_brain.yaml`.

```yaml
homeassistant:
  packages: !include_dir_named packages

logger:
  default: warning
  logs:
    climate_brain: info
```

## 3. Occupied mode

When people are home, HVAC mode is `heat_cool`. Never `auto`.

## 4. Restart

Do a full Home Assistant restart. Reloading YAML is not enough.

## 5. Dashboard

Paste `climate_brain_dashboard.yaml` as a Lovelace dashboard (raw editor).

## 6. Confirm

- The Climate Brain HVAC connection tile is on
- Logs: Settings → System → Logs, logger `climate_brain`
- Package automations cannot be edited in the UI. Do not click Migrate.

## Uninstall

1. Turn off `input_boolean.climate_brain_enabled`. Wait about 5 seconds.
2. Delete `config/packages/climate_brain.yaml`.
3. Full restart.
4. Remove leftover `climate_brain*` entities.
