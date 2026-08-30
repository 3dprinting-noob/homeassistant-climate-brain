# Changelog

## 0.1.14 — 2026-08-30

- Wizard page: removed HACS / Home Assistant integration steps. That page is the YAML package generator only.

## 0.1.13 / integration 1.5.0 — 2026-08-30

- HACS custom integration (`custom_components/climate_brain`, domain `climate_brain`, version 1.5.0). Add the GitHub repo as a custom repository, category Integration, then Settings → Devices & Services → Add Integration → Climate Brain.
- Config flow collects climate zones (1–8), occupancy, outdoor, independent zones, occupied HVAC mode, optional travelers, optional Tesla (no user_present), clocks, and default setpoints. Options flow edits the same data. Single instance.
- The integration is the sole writer to those `climate.*` zones. It does not create `climate.climate_brain*`. Engine is the 1.4.1 model (occupancy flicker, unknown never Away, Tesla travel-only, season latch, HVAC connection off stops writes).
- Native switch / number / select / sensor / button / datetime entities so HACS uninstall removes them. HVAC connection is a confirming tile (`Disconnect Climate Brain?` / `Trane / Nexia thermostat schedule`).
- Service `climate_brain.generate_dashboard` writes Lovelace YAML (built-in cards).
- Wizard kept for YAML 1.4.1 packages. “Two ways to install” box on the Pages site. Cache-bust `chaos.js` / template `?v=0.1.13`.
- Not in the default HACS store.

## 0.1.12 — 2026-08-30

- Chaos checker: HVAC enabled on the confirming tile no longer fails "raw enabled switch". The old check matched from the Brain card through the whole dashboard.

## 0.1.11 — 2026-08-30

- Wizard: after Generate / Download, install steps for `config/packages/climate_brain.yaml` and the `packages:` / `logger:` lines in `configuration.yaml`.

## 0.1.10 — 2026-08-30

- Wizard and docs copy: grammar pass, written so a 10th grader can follow it. HVAC logic unchanged.

## 0.1.9 / package 1.4.1 — 2026-08-30

- Tesla direction template: `toward` | `away` | `inhome`. Empty dest is not automatically away. Location home (driveway) is inhome. Route/dest matching home + TTA > 0 → toward. Nav dest not home → away. No usable nav uses falling/rising `distance()` to `zone.home` (0.08 km hysteresis).
- Optional route tracker field. Tesla people are not concatenated into occupancy.
- Tesla toward ETAs join family ETA (TTA, or km×60/45 when no nav).
- HVAC connection tile with confirmation. No raw enabled switch. No On/Off dash buttons. Trigger ids stay `hvac_on` / `hvac_off` (not YAML booleans). Disconnect: stop writes; thermostat schedule resumes; last setpoints stay.
- Chaos checker cache-bust (`chaos.js?v=0.1.9`). Flags Tesla-as-occupancy, empty dest auto-away, driveway not inhome, missing HVAC confirmation on the dashboard.

## 0.1.8 / package 1.3.4.1 — 2026-08-30

- HVAC On/Off trigger ids are `hvac_on` / `hvac_off` (unquoted YAML `id: on` / `id: off` became booleans, so dashboard buttons reloaded the zone editor instead of power_on/off).
- Chaos checker flags unquoted `id: on` / `id: off`.

## 0.1.7 / package 1.3.4 — 2026-08-30

- Each zone has its own comfort / away / Boost / night. Zones 3+ can still follow zone 2 if you uncheck independent.
- Outdoor can be a temperature sensor or a `weather.*` entity (uses the temperature attribute).
- Dashboard zone editor: pick zone, fields, Save overwrites that zone; one Defaults button.
- Occupied HVAC dropdown: heat / cool / heat-cool (never auto).
- HVAC control On / Off buttons. On clears leftover timers and evaluates like a restart; saved zone temps stay.

## 0.1.6 — 2026-08-30

- Top-of-form warning: remove other thermostats; full-responsibility disclaimer; Trane communicating heat pump test note; forced-air + HA heat/cool/heat-cool prereqs; removal steps.
- Download/copy asks two confirmations, then stamps `# CLIMATE_BRAIN_RISK_ACCEPTED` into the YAML.
- Optional Tesla travel/ETA (never occupancy): vehicles, destination, minutes-to-arrival, home match.

## 0.1.5 — 2026-08-30

- Chaos checker cache-bust (`chaos.js?v=0.1.5`). File-logger check only flags a real notify action, not the 1.3.3 changelog comment.

## 0.1.4 — 2026-08-30

- Chaos checker: PASS lines green, FAIL lines red (verdict matches).

## 0.1.3 — 2026-08-30

- Chaos checker: File notify check ignores comments (1.3.3 changelog mentioned notify.climate_brain_log).
- Season latch: outdoor 64 is heat (`<= season-1`), 65 dead, 66 cool.

## 0.1.2 — 2026-08-30

- Humidity removed from the wizard (it never drove setpoints; not floor-based).
- Entity fields start empty (zones, occupancy, outdoor, travel sensors). Each has a Use default button with a suggested name.
- Occupancy how-to: Climate Brain does not create the binary sensor; Helpers + Developer tools steps are on the form.

## 0.1.1 — 2026-08-30

- Install: delete other thermostat controllers completely (VTherm, Generic Thermostat, HVAC app Auto schedule, old climate automations).
- Credits: inspired by Versatile Thermostat for Comfort/Eco/Boost/Away; attributes include GrokAI.
- Wizard: sleep / morning Z2 / morning Z1 / day-start clocks are user fields (`input_datetime` initials).
- After Generate, a fussy chaos checker runs (YAML integrity, presence flicker vs leave, occupancy unknown never Away, travel toward/away + ETA +5 hysteresis, outdoor 64/65/66 latch). FAIL packages cannot download.

## 0.1.0 — 2026-08-30

First public generator. Stamps Climate Brain **v1.3.3** YAML plus Lovelace cards.

- Wizard asks zone count (1–8), climate entities, occupancy, outdoor, optional humidity, optional travelers, home/away/night/Boost/vacation setpoints, vacation button on/off.
- Occupancy is any on/off `binary_sensor`. Not iOS-specific. Travel/ETA is optional Phase 2.
- Extra zones 3–8 share occupied/empty/Boost/vacation with zone 2 and have their own night sliders.
- Does not ship household YAML. Template uses placeholders only.
- 1.3.2 File notify is not offered.
