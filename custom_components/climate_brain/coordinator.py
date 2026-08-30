"""Home Assistant coordinator — maps HA state to the pure engine."""
from __future__ import annotations

import logging
import re
from collections.abc import Callable
from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_change,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_DAY_START,
    CONF_HOME_HVAC,
    CONF_INDEPENDENT_ZONES,
    CONF_MORNING_Z1,
    CONF_MORNING_Z2,
    CONF_NIGHT_START,
    CONF_OCCUPANCY,
    CONF_OUTDOOR,
    CONF_PEOPLE,
    CONF_TESLAS,
    CONF_ZONES,
    DEFAULT_AWAY_COOL,
    DEFAULT_AWAY_HEAT,
    DEFAULT_BOOST_COOL,
    DEFAULT_BOOST_HEAT,
    DEFAULT_BOOST_MIN,
    DEFAULT_COMFORT_COOL,
    DEFAULT_COMFORT_HEAT,
    DEFAULT_DAY_START,
    DEFAULT_DEBOUNCE_MIN,
    DEFAULT_EMPTY_MIN,
    DEFAULT_HOME_HVAC,
    DEFAULT_LATE_HOLD_MIN,
    DEFAULT_LOCKOUT_MIN,
    DEFAULT_MORNING_Z1,
    DEFAULT_MORNING_Z2,
    DEFAULT_NIGHT_START,
    DEFAULT_PRECOOL_SAFETY_MIN,
    DEFAULT_VACATION_BOOST_MIN,
    DEFAULT_VACATION_COOL,
    DEFAULT_VACATION_HEAT,
    DEFAULT_WATCHDOG_SEC,
    DOMAIN,
    LOGGER_NAME,
)
from . import engine

_LOGGER = logging.getLogger(LOGGER_NAME)

SIGNAL = "climate_brain_update"
UNAVAIL = frozenset({STATE_UNAVAILABLE, STATE_UNKNOWN, "none", "", "None"})

TIMER_SPEC = {
    "away_debounce": ("away_debounce_done", "debounce"),
    "empty_confirm": ("empty_confirm_done", "empty"),
    "late_arrival": ("late_arrival_done", "late"),
    "morning_boost": ("morning_boost_done", "boost"),
    "precool_safety": ("precool_safety", "precool"),
    "arrival_lockout": ("arrival_lockout_done", "lockout"),
    "vacation_boost": ("vacation_boost_done", "vacation_boost"),
    "writing_watch": ("writing_watch_done", "watchdog"),
}


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (name or "car").lower()).strip("_")
    return s or "car"


def _parse_hm(raw: str | None, default: str) -> int:
    text = (raw or default or "00:00:00").strip()
    parts = text.split(":")
    try:
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
    except (TypeError, ValueError):
        parts = default.split(":")
        h, m = int(parts[0]), int(parts[1])
    return h * 60 + m


class ClimateBrainCoordinator(DataUpdateCoordinator[engine.State]):
    """Event-driven hub. No time_pattern polling."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=None)
        self.entry = entry
        self.engine = engine.State()
        self.data = self.engine
        self._unsubs: list[Callable[[], None]] = []
        self._clock_unsubs: list[Callable[[], None]] = []
        self._timers: dict[str, Callable[[], None]] = {}
        self._applying = False
        self._started = False

    def cfg(self) -> dict[str, Any]:
        return {**self.entry.data, **(self.entry.options or {})}

    @property
    def zones(self) -> list[str]:
        z = self.cfg().get(CONF_ZONES) or []
        if isinstance(z, str):
            return [z]
        return list(z)[:8]

    def entity_id_for(self, platform: str, key: str) -> str:
        return f"{platform}.{DOMAIN}_{key}"

    async def async_setup(self) -> None:
        self._seed_engine()
        self.async_set_updated_data(self.engine)

    async def async_start(self) -> None:
        if self._started:
            return
        self._started = True
        self._listen()
        self._bind_clocks()
        await self.async_handle("ha_start_6h")

    async def async_unload(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        self._unbind_clocks()
        self._cancel_all_timers()

    def _seed_engine(self) -> None:
        cfg = self.cfg()
        zones = self.zones
        st = self.engine
        st.n_zones = max(1, len(zones) or 1)
        engine.ensure_zones(st)
        for i, eid in enumerate(zones):
            z = engine.zone_at(st, i)
            z.entity_id = eid
        st.independent_zones = bool(cfg.get(CONF_INDEPENDENT_ZONES, True))
        mode = str(cfg.get(CONF_HOME_HVAC) or DEFAULT_HOME_HVAC)
        st.home_hvac = mode if mode in ("heat", "cool", "heat_cool") else "heat_cool"
        st.comfort_heat = float(cfg.get("comfort_heat", DEFAULT_COMFORT_HEAT))
        st.comfort_cool = float(cfg.get("comfort_cool", DEFAULT_COMFORT_COOL))
        st.away_heat = float(cfg.get("away_heat", DEFAULT_AWAY_HEAT))
        st.away_cool = float(cfg.get("away_cool", DEFAULT_AWAY_COOL))
        st.boost_heat = float(cfg.get("boost_heat", DEFAULT_BOOST_HEAT))
        st.boost_cool = float(cfg.get("boost_cool", DEFAULT_BOOST_COOL))
        st.vacation_heat = float(cfg.get("vacation_heat", DEFAULT_VACATION_HEAT))
        st.vacation_cool = float(cfg.get("vacation_cool", DEFAULT_VACATION_COOL))
        st.z1_comfort_heat = st.comfort_heat
        st.z1_comfort_cool = st.comfort_cool
        st.z1_away_heat = st.away_heat
        st.z1_away_cool = st.away_cool
        st.z1_boost_heat = st.boost_heat
        st.z1_boost_cool = st.boost_cool
        st.z2_comfort_heat = st.comfort_heat
        st.z2_comfort_cool = st.comfort_cool
        st.z2_away_heat = st.away_heat
        st.z2_away_cool = st.away_cool
        st.z2_boost_heat = st.boost_heat
        st.z2_boost_cool = st.boost_cool
        st.night_hm = _parse_hm(cfg.get(CONF_NIGHT_START), DEFAULT_NIGHT_START)
        st.z2_hm = _parse_hm(cfg.get(CONF_MORNING_Z2), DEFAULT_MORNING_Z2)
        st.z1_hm = _parse_hm(cfg.get(CONF_MORNING_Z1), DEFAULT_MORNING_Z1)
        st.day_hm = _parse_hm(cfg.get(CONF_DAY_START), DEFAULT_DAY_START)
        teslas_cfg = cfg.get(CONF_TESLAS) or []
        cars: list[engine.TeslaCar] = []
        for spec in teslas_cfg:
            name = spec.get("name") or "car"
            cars.append(engine.TeslaCar(name=name, slug=slugify(name)))
        st.teslas = cars or None
        st.phase2 = bool((cfg.get(CONF_PEOPLE) or []) or teslas_cfg)

    def _listen(self) -> None:
        cfg = self.cfg()
        watched: list[str] = []
        watched.append(cfg[CONF_OCCUPANCY])
        watched.append(cfg[CONF_OUTDOOR])
        watched.extend(self.zones)
        for p in cfg.get(CONF_PEOPLE) or []:
            for key in ("dir", "eta", "tracker"):
                if p.get(key):
                    watched.append(p[key])
        for c in cfg.get(CONF_TESLAS) or []:
            for key in ("location", "route", "tta", "distance"):
                if c.get(key):
                    watched.append(c[key])
        own = [
            self.entity_id_for("switch", "enabled"),
            self.entity_id_for("switch", "vacation"),
            self.entity_id_for("switch", "phase2"),
            self.entity_id_for("select", "home_hvac"),
            self.entity_id_for("select", "latched_season"),
            self.entity_id_for("select", "edit_zone"),
            self.entity_id_for("datetime", "night_start"),
            self.entity_id_for("datetime", "morning_z2"),
            self.entity_id_for("datetime", "morning_z1"),
            self.entity_id_for("datetime", "day_start"),
        ]
        for z in range(1, self.engine.n_zones + 1):
            for kind in (
                "comfort_heat",
                "comfort_cool",
                "away_heat",
                "away_cool",
                "boost_heat",
                "boost_cool",
                "night_heat",
                "night_cool",
            ):
                own.append(self.entity_id_for("number", f"z{z}_{kind}"))
        for key in (
            "comfort_heat",
            "comfort_cool",
            "away_heat",
            "away_cool",
            "boost_heat",
            "boost_cool",
            "vacation_heat",
            "vacation_cool",
            "debounce_min",
            "empty_min",
            "lockout_min",
            "late_hold_min",
            "boost_min",
        ):
            own.append(self.entity_id_for("number", key))
        watched.extend(own)
        watched = list(dict.fromkeys(e for e in watched if e))

        self._unsubs.append(
            async_track_state_change_event(self.hass, watched, self._on_state)
        )

    def _unbind_clocks(self) -> None:
        for unsub in self._clock_unsubs:
            unsub()
        self._clock_unsubs.clear()

    def _bind_clocks(self) -> None:
        self._unbind_clocks()
        st = self.engine
        mapping = {
            "night_start": st.night_hm,
            "morning_z2": st.z2_hm,
            "morning_z1": st.z1_hm,
            "day_start": st.day_hm,
        }
        for event, hm in mapping.items():
            hour, minute = divmod(int(hm) % 1440, 60)

            def _make(ev: str) -> Callable:
                @callback
                def _cb(now: datetime) -> None:
                    self.hass.async_create_task(self.async_handle(ev))

                return _cb

            self._clock_unsubs.append(
                async_track_time_change(
                    self.hass, _make(event), hour=hour, minute=minute, second=0
                )
            )

    @callback
    def _on_state(self, event: Any) -> None:
        if self._applying:
            return
        entity_id = ""
        new_state: State | None = None
        old_state: State | None = None
        try:
            entity_id = event.data.get("entity_id") or ""
            new_state = event.data.get("new_state")
            old_state = event.data.get("old_state")
        except Exception:  # noqa: BLE001
            return
        self.hass.async_create_task(self._route_state(entity_id, old_state, new_state))

    async def _route_state(
        self, entity_id: str, old: State | None, new: State | None
    ) -> None:
        cfg = self.cfg()
        new_s = new.state if new else None
        old_s = old.state if old else None
        if entity_id == cfg.get(CONF_OCCUPANCY):
            if new_s == "off":
                await self.async_handle("occupancy_off")
            elif new_s == "on":
                await self.async_handle("occupancy_on")
            else:
                await self.async_handle("occupancy_unknown")
            return
        if entity_id == self.entity_id_for("switch", "enabled"):
            if new_s == "off":
                await self.async_handle("hvac_off")
            elif new_s == "on":
                await self.async_handle("hvac_on")
            return
        if entity_id == self.entity_id_for("switch", "vacation"):
            if new_s == "on":
                await self.async_handle("vacation_on")
            elif new_s == "off":
                await self.async_handle("vacation_off")
            return
        if entity_id == self.entity_id_for("select", "home_hvac"):
            await self.async_handle("home_hvac")
            return
        if entity_id == self.entity_id_for("select", "latched_season"):
            await self.async_handle("latch")
            return
        if entity_id == self.entity_id_for("select", "edit_zone"):
            await self.async_handle("load_zone")
            return
        if entity_id.startswith(f"datetime.{DOMAIN}_"):
            self._pull_clocks()
            self._bind_clocks()
            await self.async_handle("evaluate")
            return
        if entity_id == cfg.get(CONF_OUTDOOR):
            self._pull_outdoor()
            o = self.engine.outdoor
            if o is not None and o >= engine.SEASON + 1:
                await self.async_handle("outdoor_summer")
            elif o is not None and o <= engine.SEASON - 1:
                await self.async_handle("outdoor_winter")
            else:
                await self.async_handle("evaluate")
            return
        if entity_id in self.zones:
            if self._applying:
                return
            self._pull_climates()
            return
        travel_ids = set()
        for p in cfg.get(CONF_PEOPLE) or []:
            travel_ids.update(x for x in (p.get("dir"), p.get("eta"), p.get("tracker")) if x)
        for c in cfg.get(CONF_TESLAS) or []:
            travel_ids.update(
                x
                for x in (c.get("location"), c.get("route"), c.get("tta"), c.get("distance"))
                if x
            )
        if entity_id in travel_ids:
            await self.async_handle("travel")
            return
        if entity_id.startswith(f"number.{DOMAIN}_"):
            if "night_" in entity_id:
                await self.async_handle("night_slider")
            else:
                await self.async_handle("setpoints")
            return
        if entity_id.startswith(f"switch.{DOMAIN}_"):
            await self.async_handle("evaluate")

    def _state_str(self, entity_id: str | None) -> str:
        if not entity_id:
            return ""
        st = self.hass.states.get(entity_id)
        if st is None:
            return ""
        return str(st.state)

    def _num_entity(self, key: str, default: float) -> float:
        st = self.hass.states.get(self.entity_id_for("number", key))
        if st is None or st.state in UNAVAIL:
            return default
        try:
            return float(st.state)
        except (TypeError, ValueError):
            return default

    def _switch_on(self, key: str, default: bool) -> bool:
        st = self.hass.states.get(self.entity_id_for("switch", key))
        if st is None:
            return default
        return st.state == "on"

    def _select(self, key: str, default: str) -> str:
        st = self.hass.states.get(self.entity_id_for("select", key))
        if st is None or st.state in UNAVAIL:
            return default
        return str(st.state)

    def _pull_outdoor(self) -> None:
        eid = self.cfg().get(CONF_OUTDOOR)
        st = self.hass.states.get(eid) if eid else None
        if st is None or st.state in UNAVAIL:
            self.engine.outdoor = None
            return
        if eid.startswith("weather.") or st.domain == "weather":
            val = st.attributes.get("temperature")
        else:
            val = st.state
        try:
            self.engine.outdoor = float(val)
        except (TypeError, ValueError):
            self.engine.outdoor = None

    def _pull_climates(self) -> None:
        for i, eid in enumerate(self.zones):
            z = engine.zone_at(self.engine, i)
            z.entity_id = eid
            st = self.hass.states.get(eid)
            if st is None or st.state in UNAVAIL:
                z.available = False
                continue
            z.available = True
            z.hvac = str(st.state or "off").lower()
            cur = st.attributes.get("current_temperature")
            try:
                z.current = float(cur)
            except (TypeError, ValueError):
                pass
            temp = st.attributes.get("temperature")
            lo = st.attributes.get("target_temp_low")
            hi = st.attributes.get("target_temp_high")
            try:
                z.temperature = float(temp) if temp is not None else None
            except (TypeError, ValueError):
                z.temperature = None
            try:
                z.target_low = float(lo) if lo is not None else None
            except (TypeError, ValueError):
                z.target_low = None
            try:
                z.target_high = float(hi) if hi is not None else None
            except (TypeError, ValueError):
                z.target_high = None

    def _pull_clocks(self) -> None:
        def hm_of(key: str, default: str) -> int:
            st = self.hass.states.get(self.entity_id_for("datetime", key))
            if st is None or st.state in UNAVAIL:
                return _parse_hm(self.cfg().get(key), default)
            return _parse_hm(st.state, default)

        self.engine.night_hm = hm_of("night_start", DEFAULT_NIGHT_START)
        self.engine.z2_hm = hm_of("morning_z2", DEFAULT_MORNING_Z2)
        self.engine.z1_hm = hm_of("morning_z1", DEFAULT_MORNING_Z1)
        self.engine.day_hm = hm_of("day_start", DEFAULT_DAY_START)

    def _pull_setpoints(self) -> None:
        st = self.engine
        st.comfort_heat = self._num_entity("comfort_heat", st.comfort_heat)
        st.comfort_cool = self._num_entity("comfort_cool", st.comfort_cool)
        st.away_heat = self._num_entity("away_heat", st.away_heat)
        st.away_cool = self._num_entity("away_cool", st.away_cool)
        st.boost_heat = self._num_entity("boost_heat", st.boost_heat)
        st.boost_cool = self._num_entity("boost_cool", st.boost_cool)
        st.vacation_heat = self._num_entity("vacation_heat", st.vacation_heat)
        st.vacation_cool = self._num_entity("vacation_cool", st.vacation_cool)
        st.debounce_sec = self._num_entity("debounce_min", DEFAULT_DEBOUNCE_MIN) * 60
        st.empty_need_sec = self._num_entity("empty_min", DEFAULT_EMPTY_MIN) * 60
        n = st.n_zones
        for i in range(n):
            prefix = f"z{i + 1}_"
            if i == 0:
                st.z1_comfort_heat = self._num_entity(prefix + "comfort_heat", st.z1_comfort_heat)
                st.z1_comfort_cool = self._num_entity(prefix + "comfort_cool", st.z1_comfort_cool)
                st.z1_away_heat = self._num_entity(prefix + "away_heat", st.z1_away_heat)
                st.z1_away_cool = self._num_entity(prefix + "away_cool", st.z1_away_cool)
                st.z1_boost_heat = self._num_entity(prefix + "boost_heat", st.z1_boost_heat)
                st.z1_boost_cool = self._num_entity(prefix + "boost_cool", st.z1_boost_cool)
                st.night_z1_heat = self._num_entity(prefix + "night_heat", st.night_z1_heat)
                st.night_z1_cool = self._num_entity(prefix + "night_cool", st.night_z1_cool)
            elif i == 1:
                st.z2_comfort_heat = self._num_entity(prefix + "comfort_heat", st.z2_comfort_heat)
                st.z2_comfort_cool = self._num_entity(prefix + "comfort_cool", st.z2_comfort_cool)
                st.z2_away_heat = self._num_entity(prefix + "away_heat", st.z2_away_heat)
                st.z2_away_cool = self._num_entity(prefix + "away_cool", st.z2_away_cool)
                st.z2_boost_heat = self._num_entity(prefix + "boost_heat", st.z2_boost_heat)
                st.z2_boost_cool = self._num_entity(prefix + "boost_cool", st.z2_boost_cool)
                st.night_z2_heat = self._num_entity(prefix + "night_heat", st.night_z2_heat)
                st.night_z2_cool = self._num_entity(prefix + "night_cool", st.night_z2_cool)
            else:
                z = engine.zone_at(st, i)
                z.comfort_heat = self._num_entity(prefix + "comfort_heat", z.comfort_heat)
                z.comfort_cool = self._num_entity(prefix + "comfort_cool", z.comfort_cool)
                z.away_heat = self._num_entity(prefix + "away_heat", z.away_heat)
                z.away_cool = self._num_entity(prefix + "away_cool", z.away_cool)
                z.boost_heat = self._num_entity(prefix + "boost_heat", z.boost_heat)
                z.boost_cool = self._num_entity(prefix + "boost_cool", z.boost_cool)
                z.night_heat = self._num_entity(prefix + "night_heat", z.night_heat)
                z.night_cool = self._num_entity(prefix + "night_cool", z.night_cool)
        st.edit_comfort_heat = self._num_entity("edit_comfort_heat", st.edit_comfort_heat)
        st.edit_comfort_cool = self._num_entity("edit_comfort_cool", st.edit_comfort_cool)
        st.edit_away_heat = self._num_entity("edit_away_heat", st.edit_away_heat)
        st.edit_away_cool = self._num_entity("edit_away_cool", st.edit_away_cool)
        st.edit_boost_heat = self._num_entity("edit_boost_heat", st.edit_boost_heat)
        st.edit_boost_cool = self._num_entity("edit_boost_cool", st.edit_boost_cool)
        st.edit_night_heat = self._num_entity("edit_night_heat", st.edit_night_heat)
        st.edit_night_cool = self._num_entity("edit_night_cool", st.edit_night_cool)
        ez = self._select("edit_zone", "1")
        try:
            st.edit_zone = int(str(ez).replace("Zone ", "").strip() or "1")
        except ValueError:
            st.edit_zone = 1

    def _pull_occupancy(self) -> None:
        raw = self._state_str(self.cfg().get(CONF_OCCUPANCY))
        if raw in ("on", "off"):
            self.engine.occupancy = raw
        elif raw in UNAVAIL:
            self.engine.occupancy = "unknown"

    def _distance_to_home(self, tracker: str | None) -> float | None:
        if not tracker:
            return None
        zone = self.hass.states.get("zone.home")
        tr = self.hass.states.get(tracker)
        if zone is None or tr is None:
            return None
        try:
            from homeassistant.util.location import distance as ha_distance

            meters = ha_distance(
                zone.attributes.get("latitude"),
                zone.attributes.get("longitude"),
                tr.attributes.get("latitude"),
                tr.attributes.get("longitude"),
            )
            if meters is None:
                return None
            return float(meters) / 1000.0
        except Exception:  # noqa: BLE001
            return None

    def _pull_travel(self) -> None:
        cfg = self.cfg()
        phones = []
        for p in cfg.get(CONF_PEOPLE) or []:
            phones.append((self._state_str(p.get("dir")), self._state_str(p.get("eta"))))
        self.engine.phones = phones or None
        self.engine.phase2 = self._switch_on("phase2", bool(phones or cfg.get(CONF_TESLAS)))
        home_ok = self.hass.states.get("zone.home") is not None
        existing = {c.slug or slugify(c.name): c for c in (self.engine.teslas or [])}
        cars: list[engine.TeslaCar] = []
        for spec in cfg.get(CONF_TESLAS) or []:
            name = spec.get("name") or "car"
            slug = slugify(name)
            car = existing.get(slug) or engine.TeslaCar(name=name, slug=slug)
            car.name = name
            car.slug = slug
            car.loc = self._state_str(spec.get("location")) or "not_home"
            car.route = self._state_str(spec.get("route")) or "unknown"
            tta = self._state_str(spec.get("tta"))
            car.tta = tta if tta else "unknown"
            dist_ent = spec.get("distance")
            if dist_ent:
                raw = self._state_str(dist_ent)
                try:
                    car.dist_km = float(raw) if raw not in UNAVAIL else None
                except (TypeError, ValueError):
                    car.dist_km = None
            else:
                car.dist_km = self._distance_to_home(spec.get("location"))
            car.nav_distance_ok = home_ok
            # user_present is never read from HA
            cars.append(car)
        self.engine.teslas = cars or None

    def _pull_helpers(self, skip: set[str] | None = None) -> None:
        skip = skip or set()
        now = dt_util.now()
        self.engine.hm = now.hour * 60 + now.minute
        if "enabled" not in skip:
            self.engine.enabled = self._switch_on("enabled", True)
        if "vacation" not in skip:
            self.engine.vacation = self._switch_on("vacation", False)
        mode = self._select("home_hvac", self.engine.home_hvac)
        if mode in ("heat", "cool", "heat_cool"):
            self.engine.home_hvac = mode
        if "latch" not in skip:
            latch = self._select("latched_season", self.engine.latch)
            if latch in ("heat", "cool"):
                self.engine.latch = latch
        if "occupancy" not in skip:
            self._pull_occupancy()
        self._pull_outdoor()
        self._pull_climates()
        self._pull_clocks()
        self._pull_setpoints()
        self._pull_travel()

    def _timer_seconds(self, kind: str) -> float:
        if kind == "debounce":
            return self._num_entity("debounce_min", DEFAULT_DEBOUNCE_MIN) * 60
        if kind == "empty":
            return self._num_entity("empty_min", DEFAULT_EMPTY_MIN) * 60
        if kind == "lockout":
            return self._num_entity("lockout_min", DEFAULT_LOCKOUT_MIN) * 60
        if kind == "late":
            return self._num_entity("late_hold_min", DEFAULT_LATE_HOLD_MIN) * 60
        if kind == "boost":
            return self._num_entity("boost_min", DEFAULT_BOOST_MIN) * 60
        if kind == "precool":
            return DEFAULT_PRECOOL_SAFETY_MIN * 60
        if kind == "vacation_boost":
            return DEFAULT_VACATION_BOOST_MIN * 60
        if kind == "watchdog":
            return float(DEFAULT_WATCHDOG_SEC)
        return 60.0

    def _cancel_timer(self, name: str) -> None:
        unsub = self._timers.pop(name, None)
        if unsub:
            unsub()

    def _cancel_all_timers(self) -> None:
        for name in list(self._timers):
            self._cancel_timer(name)

    def _start_timer(self, name: str, seconds: float, event: str) -> None:
        self._cancel_timer(name)

        @callback
        def _cb(_now: datetime) -> None:
            self._timers.pop(name, None)
            self.hass.async_create_task(self.async_handle(event))

        self._timers[name] = async_call_later(self.hass, seconds, _cb)

    def _sync_timers(self) -> None:
        flags = self.engine.timers
        for name, (event, kind) in TIMER_SPEC.items():
            active = bool(getattr(flags, name, False))
            running = name in self._timers
            if active and not running:
                self._start_timer(name, self._timer_seconds(kind), event)
            elif not active and running:
                self._cancel_timer(name)
        if not self.engine.enabled:
            self._cancel_all_timers()

    async def _apply_writes(self) -> None:
        recs = list(self.engine.write_recs)
        if not recs:
            return
        self._applying = True
        try:
            for rec in recs:
                which = rec.get("zone") or "z1"
                try:
                    idx = int(str(which)[1:]) - 1
                except (TypeError, ValueError):
                    idx = 0
                zones = self.zones
                if idx < 0 or idx >= len(zones):
                    continue
                eid = zones[idx]
                mode = rec.get("hvac")
                if mode == "auto":
                    continue
                if mode in ("heat", "cool", "heat_cool", "off"):
                    await self.hass.services.async_call(
                        "climate",
                        "set_hvac_mode",
                        {"entity_id": eid, "hvac_mode": mode},
                        blocking=True,
                    )
                if rec.get("used_dual") and rec.get("low") is not None:
                    await self.hass.services.async_call(
                        "climate",
                        "set_temperature",
                        {
                            "entity_id": eid,
                            "hvac_mode": "heat_cool",
                            "target_temp_low": rec["low"],
                            "target_temp_high": rec["high"],
                        },
                        blocking=True,
                    )
                elif rec.get("used_temperature") and rec.get("temperature") is not None:
                    data = {
                        "entity_id": eid,
                        "temperature": rec["temperature"],
                    }
                    if mode in ("heat", "cool"):
                        data["hvac_mode"] = mode
                    await self.hass.services.async_call(
                        "climate",
                        "set_temperature",
                        data,
                        blocking=True,
                    )
        finally:
            self._applying = False

    async def async_handle(self, event: str) -> None:
        if event not in ("hvac_on", "enabled_on", "evaluate") and not self.engine.enabled:
            if event in ("hvac_off", "enabled_off"):
                pass
            elif event != "evaluate":
                # still allow power_off path; other events ignored by engine
                pass
        skip: set[str] = set()
        if event in ("occupancy_on", "occupancy_off", "occupancy_unknown"):
            skip.add("occupancy")
        if event in ("vacation_on", "vacation_off"):
            skip.add("vacation")
        if event in ("hvac_on", "hvac_off", "enabled_on", "enabled_off"):
            skip.add("enabled")
        if event == "latch":
            skip.add("latch")
        self._pull_helpers(skip=skip)
        if event == "latch":
            latch = self._select("latched_season", self.engine.latch)
            if latch in ("heat", "cool"):
                self.engine.latch = latch
        self.engine.write_recs = []
        self.engine.brain_temps = []
        engine.handle(self.engine, event)
        chain = 0
        while self.engine.queued:
            chain += 1
            if chain > engine.LOOP_LIMIT:
                break
            nxt = self.engine.queued.pop(0)
            engine.handle(self.engine, nxt)
        if engine.boost_reached_template(self.engine):
            engine.handle(self.engine, "vacation_boost_reached")
        self._sync_timers()
        if self.engine.enabled:
            await self._apply_writes()
        _LOGGER.info("%s", self.engine.status)
        self.async_set_updated_data(self.engine)
        async_dispatcher_send(self.hass, SIGNAL)

    async def async_button(self, event: str) -> None:
        await self.async_handle(event)
