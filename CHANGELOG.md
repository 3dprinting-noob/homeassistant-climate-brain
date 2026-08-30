# Changelog

## 0.1.1 — 2026-08-30

- Install: delete other thermostat controllers completely (VTherm, Generic Thermostat, HVAC app Auto schedule, old climate automations).
- Credits: inspired by Versatile Thermostat for Comfort/Eco/Boost/Away; attributes include GrokAI.
- Wizard: sleep / morning Z2 / morning Z1 / day-start clocks are user fields (`input_datetime` initials).
- After Generate, a fussy chaos checker runs (YAML integrity, presence flicker vs leave, occupancy unknown never Away, travel toward/away + ETA +5 hysteresis, outdoor 64/65/66 latch). FAIL packages cannot download.

# Changelog

## 0.1.0 — 2026-08-30

First public generator. Stamps Climate Brain **v1.3.3** YAML plus Lovelace cards.

- Wizard asks zone count (1–8), climate entities, occupancy, outdoor, optional humidity, optional travelers, home/away/night/Boost/vacation setpoints, vacation button on/off.
- Occupancy is any on/off `binary_sensor`. Not iOS-specific. Travel/ETA is optional Phase 2.
- Extra zones 3–8 share occupied/empty/Boost/vacation with zone 2 and have their own night sliders.
- Does not ship household YAML. Template uses placeholders only.
- 1.3.2 File notify is not offered.
