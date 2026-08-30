# Install

Climate Brain must be the **only** program changing the climates you enter. If something else still sets those thermostats, they will fight.

## Delete other thermostat controllers first

Do this **before** you add the integration or paste a YAML package. Turning things off is not enough if they start again after a restart.

Remove or delete completely:

- Versatile Thermostat on those zones (`climate.home_thermostat*`, VTherm helpers, VTherm presence)
- Other Home Assistant automations, scripts, or Node-RED flows that call `climate.set_temperature`, `climate.set_hvac_mode`, `climate.set_preset_mode`, or `versatile_thermostat.*`
- Generic Thermostat, Dual Smart Thermostat, or Better Thermostat wrapping the same equipment
- The HVAC app’s own schedule (Trane Home / Nexia **Auto** schedule, 62/82, weekly programs)
- Old arrival / travel / night packages that write the same `climate.*` entities

Keep the climate entities themselves. Delete the extra *controllers*, not the Trane / Nexia zones.

If two programs both write, the house will bounce between temperatures.

## A. Recommended: HACS integration (1.5.0)

Climate Brain is **not** in the default HACS store. Add it as a custom repository.

1. In Home Assistant open **HACS**.
2. Go to **Integrations**.
3. Open the three dots → **Custom repositories**.
4. Paste `https://github.com/3dprinting-noob/homeassistant-climate-brain`
5. Category: **Integration** → **Add**.
6. Find **Climate Brain** and download / install it.
7. **Restart Home Assistant**.
8. Settings → Devices & Services → **Add Integration** → **Climate Brain**.
9. Pick 1–8 `climate.*` zones, your occupancy `binary_sensor`, and outdoor temperature. Occupied HVAC mode is heat, cool, or heat_cool (never auto). Travelers and Tesla are optional.
10. Restart again if Home Assistant asks.

Then Settings → Devices & Services → Climate Brain → Configure to change the same data later.

Call the service `climate_brain.generate_dashboard` to write `climate_brain_dashboard.yaml` in the Home Assistant config folder. Paste that file in a Lovelace raw editor. The HVAC connection is a **tile** that asks `Disconnect Climate Brain?` and mentions the `Trane / Nexia thermostat schedule`. Do not put that switch on a generic Brain list without the confirmation.

### Uninstall (HACS)

1. Turn off **HVAC connection** (the confirming tile). Wait a few seconds. Last setpoints stay. Climate Brain does not turn the HVAC off.
2. Delete the integration (Settings → Devices & Services).
3. Remove it from HACS.
4. Restart Home Assistant. Owned switches, numbers, sensors, and buttons go away with the integration.

## B. YAML package (1.4.1) — stay on the wizard

Use this if you do not want HACS.

### 1. Generate

Open the [wizard](https://3dprinting-noob.github.io/homeassistant-climate-brain/) (or `docs/index.html`). Entity fields start empty. Paste your Home Assistant IDs, or tap **Use default** if you already created helpers with those names. Occupancy is a binary sensor you create in Helpers first (see [PREREQUISITES.md](PREREQUISITES.md)). Then fill temperatures, sleep/morning times, optional travel, and the optional vacation button.

Click **Generate**. The checker must say **INSTALL OK**. Do not download a file that says FAIL.

### 2. Home Assistant packages

Save the file as `config/packages/climate_brain.yaml`.

```yaml
homeassistant:
  packages: !include_dir_named packages

logger:
  default: warning
  logs:
    climate_brain: info
```

### 3. Occupied mode

When people are home, HVAC mode is `heat_cool`. Never `auto`.

### 4. Restart

Do a full Home Assistant restart. Reloading YAML is not enough.

### 5. Dashboard

Paste `climate_brain_dashboard.yaml` as a Lovelace dashboard (raw editor).

### 6. Confirm

- The Climate Brain HVAC connection tile is on
- Logs: Settings → System → Logs, logger `climate_brain`
- Package automations cannot be edited in the UI. Do not click Migrate.

### Uninstall (YAML)

1. Turn off `input_boolean.climate_brain_enabled`. Wait about 5 seconds.
2. Delete `config/packages/climate_brain.yaml`.
3. Full restart.
4. Remove leftover `climate_brain*` helpers.

## Occupied HVAC

When people are home, HVAC mode is heat, cool, or heat_cool. Never `auto`.
