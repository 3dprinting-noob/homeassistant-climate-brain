# Changelog

## 0.1.0 — 2026-08-30

First public generator. Stamps Climate Brain **v1.3.3** YAML plus Lovelace cards.

- Wizard asks zone count (1–8), climate entities, occupancy, outdoor, optional humidity, optional travelers, home/away/night/Boost/vacation setpoints, vacation button on/off.
- Occupancy is any on/off `binary_sensor`. Not iOS-specific. Travel/ETA is optional Phase 2.
- Extra zones 3–8 share occupied/empty/Boost/vacation with zone 2 and have their own night sliders.
- Does not ship household YAML. Template uses placeholders only.
- 1.3.2 File notify is not offered.
