"""Climate Brain 1.5.0 pure engine — no Home Assistant imports.

Port of the battle-tested 1.4.1 in-memory model (evaluate, write_zone,
router, Tesla direction, occupancy, vacation, HVAC on/off). Generalized
from 2 zones to 1–8. Occupancy is people/phones only; Tesla is never occupancy.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

NIGHT_HM = 22 * 60 + 30
Z2_HM = 5 * 60 + 15
Z1_HM = 5 * 60 + 45
DAY_HM = 6 * 60 + 15
SEASON = 65.0
FORBIDDEN_TEMPS = {50.0, 62.0}
UNAVAIL = frozenset({"unavailable", "unknown", "none", ""})
OCC_NOT_READY = "occupancy not ready — no Away guess"
LOOP_LIMIT = 8
ROUTER_MAX = 20

TIME_EVENTS = frozenset({"morning_z2", "morning_z1", "day_start", "night_start"})
CLOCK_HM = {
    "night_start": NIGHT_HM,
    "morning_z2": Z2_HM,
    "morning_z1": Z1_HM,
    "day_start": DAY_HM,
}

TIMES = [
    ("00:00", 0), ("02:00", 2 * 60), ("05:14", 5 * 60 + 14),
    ("05:15", 5 * 60 + 15), ("05:44", 5 * 60 + 44), ("05:45", 5 * 60 + 45),
    ("06:14", 6 * 60 + 14), ("06:15", 6 * 60 + 15), ("07:07", 7 * 60 + 7),
    ("10:00", 10 * 60), ("14:00", 14 * 60), ("22:29", 22 * 60 + 29),
    ("22:30", 22 * 60 + 30), ("22:50", 22 * 60 + 50), ("23:50", 23 * 60 + 50),
]

def hm_label(hm: int) -> str:
    return f"{hm // 60:02d}:{hm % 60:02d}"


def clock_bounds(st: "State | None" = None) -> tuple[int, int, int, int]:
    if st is None:
        return NIGHT_HM, Z2_HM, Z1_HM, DAY_HM
    return int(st.night_hm), int(st.z2_hm), int(st.z1_hm), int(st.day_hm)


def clock_period(hm: int, st: "State | None" = None) -> str:
    night, z2, z1, day = clock_bounds(st)
    if hm >= night or hm < z2:
        return "night"
    if hm < z1:
        return "morning_z2"
    if hm < day:
        return "morning_z1"
    return "day"


def in_night(hm: int, st: "State | None" = None) -> bool:
    night, z2, _, _ = clock_bounds(st)
    return hm >= night or hm < z2


HYST_KM = 0.08
TESLA_KMH = 45.0


def toward_dir(dir_raw: str) -> bool:
    d = str(dir_raw or "").lower()
    return ("toward" in d) and ("inhome" not in d) and ("instat" not in d)


@dataclass
class TeslaCar:
    name: str = "car"
    loc: str = "not_home"
    route: str = "unknown"
    tta: Any = "unknown"
    dist_km: float | None = None
    last_km: float = 0.0
    direction: str = "away"
    user_present: bool = False
    nav_distance_ok: bool = True
    slug: str = ""


def tesla_direction(car: TeslaCar) -> str:
    loc = str(car.loc or "").lower()
    route = str(car.route or "").lower()
    tta = parse_eta(str(car.tta))
    prev = car.direction if car.direction in ("toward", "away", "inhome") else "away"
    loc_home = loc in ("home", "zone.home")
    route_home = route in ("home", "zone.home")
    if loc_home:
        return "inhome"
    if route_home and tta > 0:
        return "toward"
    if tta <= 0 and not route_home:
        if not car.nav_distance_ok or car.dist_km is None:
            return prev
        delta = float(car.dist_km) - float(car.last_km)
        if delta <= -HYST_KM:
            return "toward"
        if delta >= HYST_KM:
            return "away"
        return prev
    return "away"


def tesla_eta_min(car: TeslaCar) -> int:
    if tesla_direction(car) != "toward":
        return 0
    tta = parse_eta(str(car.tta))
    if tta > 0:
        return tta
    dist = float(car.dist_km) if car.dist_km is not None else 0.0
    return max(1, int(round(dist * 60.0 / TESLA_KMH)))


def refresh_teslas(st: "State") -> None:
    if not st.teslas:
        return
    for car in st.teslas:
        car.direction = tesla_direction(car)
        if car.dist_km is not None:
            car.last_km = float(car.dist_km)


def parse_eta(raw: str) -> int:
    raw = str(raw or "").lower().strip()
    if raw in UNAVAIL:
        return 0
    if ":" in raw:
        pp = raw.split(":")
        hp = re.findall(r"\d+", pp[0])
        mp = re.findall(r"\d+", pp[1]) if len(pp) > 1 else []
        return (int(hp[0]) if hp else 0) * 60 + (int(mp[0]) if mp else 0)
    hm = re.findall(r"(\d+)\s*(?:h|hr|hrs|hour|hours)", raw)
    mm = re.findall(r"(\d+)\s*(?:m|min|mins|minute|minutes)", raw)
    if hm or mm:
        return (int(hm[0]) if hm else 0) * 60 + (int(mm[0]) if mm else 0)
    nums = re.findall(r"\d+", raw)
    return int(nums[0]) if nums else 0


def eta_of(kind: str) -> int:
    if kind in ("toward_1h15", "toward_01:15"):
        return 75
    if kind.startswith("toward_"):
        rest = kind[7:]
        if rest.isdigit():
            return int(rest)
    return 9999


def toward_of(kind: str) -> bool:
    return toward_dir(kind)


@dataclass
class Zone:
    hvac: str = "off"
    current: float = 70.0
    temperature: float | None = None
    target_low: float | None = None
    target_high: float | None = None
    available: bool = True
    entity_id: str = ""
    comfort_heat: float = 71.0
    comfort_cool: float = 74.0
    away_heat: float = 65.0
    away_cool: float = 78.0
    boost_heat: float = 73.0
    boost_cool: float = 70.0
    night_heat: float = 65.0
    night_cool: float = 72.0


@dataclass
class Timers:
    away_debounce: bool = False
    empty_confirm: bool = False
    late_arrival: bool = False
    morning_boost: bool = False
    precool_safety: bool = False
    arrival_lockout: bool = False
    vacation_boost: bool = False
    writing_watch: bool = False


@dataclass
class State:
    hm: int = 12 * 60
    occupancy: str = "on"
    occupancy_from: str = "on"
    vacation: bool = False
    timers: Timers = field(default_factory=Timers)
    outdoor: float | None = 70.0
    latch: str = "heat"
    z1: Zone = field(default_factory=lambda: Zone(night_heat=64.0, night_cool=76.0))
    z2: Zone = field(default_factory=lambda: Zone(current=72.0, night_heat=65.0, night_cool=72.0))
    extra_zones: list = field(default_factory=list)
    n_zones: int = 2
    independent_zones: bool = True
    night_hm: int = NIGHT_HM
    z2_hm: int = Z2_HM
    z1_hm: int = Z1_HM
    day_hm: int = DAY_HM
    debounce_sec: float = 3 * 60
    empty_need_sec: float = 15 * 60
    enabled: bool = True
    phase2: bool = True
    writing: bool = False
    last_write_age: float = 99999.0
    last_write_valid: bool = True
    was_empty_15m: bool = False
    empty_since_sec: float = 99999.0
    lockout_bool: bool = False
    vacation_start_temp: float = 72.0
    precool_start_temp: float = 72.0
    precool_started_valid: bool = False
    time_triggers_bound: bool = True
    travel_kind: str = "none"
    travel_raw: str | None = None
    phones: list | None = None
    status: str = "idle"
    last_period: str | None = None
    last_reason: str = ""
    brain_temps: list = field(default_factory=list)
    write_recs: list = field(default_factory=list)
    last_z1: dict | None = None
    last_z2: dict | None = None
    mb_started_this: bool = False
    eval_this: int = 0
    eval_total: int = 0
    writes_this: int = 0
    stopped: str | None = None
    missed_time: list = field(default_factory=list)
    trigger_seq: list = field(default_factory=list)
    period_seq: list = field(default_factory=list)
    write_seq: list = field(default_factory=list)
    eval_seq: list = field(default_factory=list)
    queued: list = field(default_factory=list)
    writing_leaked: bool = False
    boost_starts: int = 0
    precool_starts: int = 0
    evaluate_skipped: bool = False
    hang_after_writing: bool = False
    write_error: bool = False
    watchdog_active: bool = False
    precool_illegal: bool = False
    climate_set_count: int = 0
    home_hvac: str = "heat_cool"
    # per-zone helpers (evaluate WRITES these)
    z1_comfort_heat: float = 71.0
    z1_comfort_cool: float = 74.0
    z1_away_heat: float = 65.0
    z1_away_cool: float = 78.0
    z1_boost_heat: float = 73.0
    z1_boost_cool: float = 70.0
    z2_comfort_heat: float = 71.0
    z2_comfort_cool: float = 74.0
    z2_away_heat: float = 65.0
    z2_away_cool: float = 78.0
    z2_boost_heat: float = 73.0
    z2_boost_cool: float = 70.0
    night_z1_heat: float = 64.0
    night_z1_cool: float = 76.0
    night_z2_heat: float = 65.0
    night_z2_cool: float = 72.0
    # house-wide snapshot (Defaults only — travel/vb band, NOT evaluate writes)
    comfort_heat: float = 71.0
    comfort_cool: float = 74.0
    boost_heat: float = 73.0
    boost_cool: float = 70.0
    away_heat: float = 65.0
    away_cool: float = 78.0
    vacation_heat: float = 55.0
    vacation_cool: float = 80.0
    edit_zone: int = 1
    edit_comfort_heat: float = 71.0
    edit_comfort_cool: float = 74.0
    edit_away_heat: float = 65.0
    edit_away_cool: float = 78.0
    edit_boost_heat: float = 73.0
    edit_boost_cool: float = 70.0
    edit_night_heat: float = 64.0
    edit_night_cool: float = 76.0
    teslas: list | None = None
    tesla_user_present: bool = False
    occupancy_source: str = "binary_sensor"


@dataclass
class Finding:
    fid: str
    scenario: str
    expected: str
    actual: str
    loop: bool = False
    stuck: bool = False
    severity: str = "warn"
    sequence: list | None = None


def occupied(st: State) -> bool:
    return st.occupancy == "on"


def ensure_zones(st: State) -> None:
    n = max(1, min(8, int(st.n_zones or 1)))
    st.n_zones = n
    while len(st.extra_zones) < max(0, n - 2):
        st.extra_zones.append(Zone(current=72.0))


def zone_at(st: State, idx: int) -> Zone:
    ensure_zones(st)
    if idx <= 0:
        return st.z1
    if idx == 1:
        return st.z2
    return st.extra_zones[idx - 2]


def iter_zones(st: State) -> list[Zone]:
    ensure_zones(st)
    out = [st.z1]
    if st.n_zones >= 2:
        out.append(st.z2)
    for i in range(2, st.n_zones):
        out.append(st.extra_zones[i - 2])
    return out


def zone_sp(st: State, idx: int, kind: str) -> tuple[float, float]:
    """kind is comfort|away|boost|night. Zones 3+ copy zone 2 when independent is off."""
    src_idx = idx
    if (not st.independent_zones) and idx >= 2:
        src_idx = 1 if st.n_zones >= 2 else 0
    if src_idx == 0:
        mapping = {
            "comfort": (st.z1_comfort_heat, st.z1_comfort_cool),
            "away": (st.z1_away_heat, st.z1_away_cool),
            "boost": (st.z1_boost_heat, st.z1_boost_cool),
            "night": (st.night_z1_heat, st.night_z1_cool),
        }
        return mapping[kind]
    if src_idx == 1:
        mapping = {
            "comfort": (st.z2_comfort_heat, st.z2_comfort_cool),
            "away": (st.z2_away_heat, st.z2_away_cool),
            "boost": (st.z2_boost_heat, st.z2_boost_cool),
            "night": (st.night_z2_heat, st.night_z2_cool),
        }
        return mapping[kind]
    z = zone_at(st, src_idx)
    mapping = {
        "comfort": (z.comfort_heat, z.comfort_cool),
        "away": (z.away_heat, z.away_cool),
        "boost": (z.boost_heat, z.boost_cool),
        "night": (z.night_heat, z.night_cool),
    }
    return mapping[kind]


def outdoor_ready(st: State) -> bool:
    return st.outdoor is not None


def latch_of(st: State) -> str:
    return (st.latch or "").lower()


def empty_hvac_of(st: State) -> str:
    """Evaluate uses the season latch only — never outdoor>=65."""
    return latch_of(st)


def pull_hvac_of(st: State) -> str:
    e = empty_hvac_of(st)
    return e if e in ("heat", "cool") else ""


def occ_hvac_of(st: State) -> str:
    m = (st.home_hvac or "").lower()
    return m if m in ("heat", "cool", "heat_cool") else "heat_cool"


def period_of(st: State) -> str:
    occ = occupied(st)
    debounce = st.timers.away_debounce
    precool_on = st.timers.precool_safety
    if st.vacation:
        return "vacation"
    if st.timers.vacation_boost:
        return "vacation_boost"
    if precool_on and not (occ or debounce):
        return "precool"
    if not (occ or debounce):
        return "empty"
    if st.timers.late_arrival:
        return "late_hold"
    return clock_period(st.hm, st)


def desired_of(st: State) -> dict[str, Any]:
    """Mirror YAML evaluate variables: period / zN_hvac / zN_*_sp / kind."""
    period = period_of(st)
    empty_hvac = empty_hvac_of(st)
    pull = pull_hvac_of(st)
    boost_on = st.timers.morning_boost
    occ_hvac = occ_hvac_of(st)

    if period in ("empty", "vacation"):
        z1_hvac = empty_hvac
    elif period in ("vacation_boost", "precool"):
        z1_hvac = pull
    elif period in ("morning_z1", "day") and boost_on and pull in ("heat", "cool"):
        z1_hvac = pull
    else:
        z1_hvac = occ_hvac

    if period in ("empty", "vacation"):
        z2_hvac = empty_hvac
    elif period in ("vacation_boost", "precool"):
        z2_hvac = pull
    elif (period in ("morning_z2", "morning_z1", "day")
          and pull in ("heat", "cool") and boost_on):
        z2_hvac = pull
    else:
        z2_hvac = occ_hvac

    if period in ("night", "morning_z2"):
        z1_heat_sp, z1_cool_sp = st.night_z1_heat, st.night_z1_cool
    elif (period in ("vacation_boost", "precool")
          or (period in ("morning_z1", "day") and boost_on and pull in ("heat", "cool"))):
        z1_heat_sp, z1_cool_sp = st.z1_boost_heat, st.z1_boost_cool
    elif period == "vacation":
        z1_heat_sp, z1_cool_sp = st.vacation_heat, st.vacation_cool
    elif period == "empty":
        z1_heat_sp, z1_cool_sp = st.z1_away_heat, st.z1_away_cool
    else:
        z1_heat_sp, z1_cool_sp = st.z1_comfort_heat, st.z1_comfort_cool

    if period == "night":
        z2_heat_sp, z2_cool_sp = st.night_z2_heat, st.night_z2_cool
    elif period == "morning_z2":
        if boost_on and pull in ("heat", "cool"):
            z2_heat_sp, z2_cool_sp = st.z2_boost_heat, st.z2_boost_cool
        else:
            z2_heat_sp, z2_cool_sp = st.z2_comfort_heat, st.z2_comfort_cool
    elif (period in ("vacation_boost", "precool")
          or (period in ("morning_z1", "day") and boost_on and pull in ("heat", "cool"))):
        z2_heat_sp, z2_cool_sp = st.z2_boost_heat, st.z2_boost_cool
    elif period == "vacation":
        z2_heat_sp, z2_cool_sp = st.vacation_heat, st.vacation_cool
    elif period == "empty":
        z2_heat_sp, z2_cool_sp = st.z2_away_heat, st.z2_away_cool
    else:
        z2_heat_sp, z2_cool_sp = st.z2_comfort_heat, st.z2_comfort_cool

    z1_single = z1_cool_sp if z1_hvac == "cool" else z1_heat_sp
    z2_single = z2_cool_sp if z2_hvac == "cool" else z2_heat_sp
    z1_kind = "single" if z1_hvac in ("heat", "cool") else "dual"
    z2_kind = "single" if z2_hvac in ("heat", "cool") else "dual"
    desired_presence = "off" if period in ("empty", "vacation") else "on"
    d = {
        "period": period, "empty_hvac": empty_hvac, "pull_hvac": pull,
        "occ_hvac": occ_hvac, "z1_hvac": z1_hvac, "z2_hvac": z2_hvac,
        "z1_kind": z1_kind, "z2_kind": z2_kind,
        "z1_heat_sp": z1_heat_sp, "z1_cool_sp": z1_cool_sp,
        "z2_heat_sp": z2_heat_sp, "z2_cool_sp": z2_cool_sp,
        "z1_single": z1_single, "z2_single": z2_single,
        "desired_presence": desired_presence, "clock": clock_period(st.hm, st),
        "boost_on": boost_on,
        "extra": [],
    }
    extras = []
    for idx in range(2, max(2, int(st.n_zones or 2))):
        hvac = z2_hvac
        if period == "night":
            heat_sp, cool_sp = zone_sp(st, idx, "night")
        elif period == "morning_z2":
            if boost_on and pull in ("heat", "cool"):
                heat_sp, cool_sp = zone_sp(st, idx, "boost")
            else:
                heat_sp, cool_sp = zone_sp(st, idx, "comfort")
        elif (period in ("vacation_boost", "precool")
              or (period in ("morning_z1", "day") and boost_on and pull in ("heat", "cool"))):
            heat_sp, cool_sp = zone_sp(st, idx, "boost")
        elif period == "vacation":
            heat_sp, cool_sp = st.vacation_heat, st.vacation_cool
        elif period == "empty":
            heat_sp, cool_sp = zone_sp(st, idx, "away")
        else:
            heat_sp, cool_sp = zone_sp(st, idx, "comfort")
        single = cool_sp if hvac == "cool" else heat_sp
        kind = "single" if hvac in ("heat", "cool") else "dual"
        extras.append({
            "hvac": hvac, "kind": kind, "heat_sp": heat_sp, "cool_sp": cool_sp,
            "single": single, "which": f"z{idx + 1}",
        })
    d["extra"] = extras
    return d


def snapshot_write(d: dict) -> str:
    z1t = d["z1_single"] if d["z1_kind"] == "single" else f"{d['z1_heat_sp']}/{d['z1_cool_sp']}"
    z2t = d["z2_single"] if d["z2_kind"] == "single" else f"{d['z2_heat_sp']}/{d['z2_cool_sp']}"
    return f"{d['period']}/z1={d['z1_hvac']}:{d['z1_kind']}:{z1t}/z2={d['z2_hvac']}:{d['z2_kind']}:{z2t}"


def write_zone(st: State, which: str, hvac_mode: str, kind: str,
               temperature: float, target_low: float, target_high: float) -> bool:
    if which == "z1":
        z = st.z1
    elif which == "z2":
        z = st.z2
    elif isinstance(which, str) and which.startswith("z") and which[1:].isdigit():
        z = zone_at(st, int(which[1:]) - 1)
    else:
        z = st.z2
    if not z.available or st.write_error:
        return False
    raw_hvac = (hvac_mode or "").lower()
    want_hvac = "heat_cool" if raw_hvac in ("auto", "heat_cool") else raw_hvac
    want_kind = (kind or "none").lower()
    raw_lo = float(target_low)
    raw_hi = float(target_high)
    want_lo = raw_lo
    want_hi = raw_hi if raw_lo < raw_hi else raw_lo + 3
    want_temp = float(temperature)
    if want_temp in FORBIDDEN_TEMPS or want_lo in FORBIDDEN_TEMPS or want_hi in FORBIDDEN_TEMPS:
        return False
    cur_hvac = (z.hvac or "").lower()
    same_hvac = cur_hvac == want_hvac
    if want_hvac in ("heat", "cool") or want_kind == "single":
        t = z.temperature
        same_temps = t is not None and abs(t - want_temp) <= 0.4
    else:
        lo, hi = z.target_low, z.target_high
        same_temps = (
            lo is not None and hi is not None
            and abs(lo - want_lo) <= 0.4 and abs(hi - want_hi) <= 0.4
        )
    if same_hvac and same_temps:
        return False
    if want_hvac not in ("heat", "cool", "heat_cool", "off"):
        return False
    rec: dict[str, Any] = {
        "zone": which, "hvac": want_hvac, "kind": want_kind,
        "temperature": None, "low": None, "high": None,
        "used_temperature": False, "used_dual": False,
        "clamped": want_hi != raw_hi,
    }
    if not same_hvac:
        z.hvac = want_hvac
    if want_hvac in ("heat", "cool") or want_kind == "single":
        if (not same_hvac) or (not same_temps):
            z.temperature = want_temp
            rec["kind"] = "single"
            rec["temperature"] = want_temp
            rec["used_temperature"] = True
            st.brain_temps.append(want_temp)
            st.climate_set_count += 1
    if want_hvac == "heat_cool" and want_kind != "single":
        if (not same_hvac) or (not same_temps):
            z.target_low = want_lo
            z.target_high = want_hi
            rec["kind"] = "dual"
            rec["low"] = want_lo
            rec["high"] = want_hi
            rec["used_dual"] = True
            st.brain_temps.extend([want_lo, want_hi])
            st.climate_set_count += 1
    st.write_recs.append(rec)
    if which == "z1":
        st.last_z1 = rec
    elif which == "z2":
        st.last_z2 = rec
    return True


def evaluate(st: State, reason: str) -> None:
    st.eval_this += 1
    st.eval_total += 1
    if not st.enabled:
        st.status = "disabled"
        st.stopped = "disabled"
        st.evaluate_skipped = True
        return
    if (st.occupancy not in ("on", "off")
            and not st.vacation
            and not st.timers.vacation_boost):
        st.status = OCC_NOT_READY
        st.stopped = "occupancy_not_ready"
        st.evaluate_skipped = True
        return
    d = desired_of(st)
    st.last_period = d["period"]
    st.last_reason = reason
    st.period_seq.append(d["period"])
    st.eval_seq.append(snapshot_write(d))

    if d["period"] in ("empty", "vacation", "precool", "vacation_boost"):
        if not outdoor_ready(st):
            st.stopped = "outdoor_unknown"
            st.evaluate_skipped = True
            st.status = "outdoor unknown — will not guess Cool/Heat"
            if st.writing:
                st.writing_leaked = True
            return
        if empty_hvac_of(st) not in ("heat", "cool"):
            st.stopped = "latch_not_ready"
            st.evaluate_skipped = True
            st.status = "season latch not ready — will not guess Cool/Heat"
            if st.writing:
                st.writing_leaked = True
            return

    st.writing = True
    st.timers.writing_watch = True
    st.watchdog_active = True
    st.last_write_age = 0.0
    st.last_write_valid = True
    if st.hang_after_writing:
        st.stopped = "evaluate_hung"
        return
    c1 = write_zone(st, "z1", d["z1_hvac"], d["z1_kind"],
                    d["z1_single"], d["z1_heat_sp"], d["z1_cool_sp"])
    c2 = False
    if st.n_zones >= 2:
        c2 = write_zone(st, "z2", d["z2_hvac"], d["z2_kind"],
                        d["z2_single"], d["z2_heat_sp"], d["z2_cool_sp"])
    cx = False
    for extra in d.get("extra") or []:
        if write_zone(st, extra["which"], extra["hvac"], extra["kind"],
                      extra["single"], extra["heat_sp"], extra["cool_sp"]):
            cx = True
    if c1 or c2 or cx:
        st.writes_this += 1
        st.write_seq.append(snapshot_write(d))
    if st.n_zones <= 1:
        hvac_status = d["z1_hvac"]
        ztail = f"z1={d['z1_heat_sp']}/{d['z1_cool_sp']}"
    else:
        hvac_status = (
            d["z1_hvac"] if d["z1_hvac"] == d["z2_hvac"]
            else f"z1={d['z1_hvac']} z2={d['z2_hvac']}"
        )
        ztail = (
            f"z1={d['z1_heat_sp']}/{d['z1_cool_sp']} "
            f"z2={d['z2_heat_sp']}/{d['z2_cool_sp']}"
        )
    st.status = (
        f"{reason} {d['period']} {hvac_status} "
        f"{ztail} p={d['desired_presence']}"
    )
    st.writing = False
    st.timers.writing_watch = False
    st.watchdog_active = False


def in_comfort_band(st: State) -> bool:
    h1, c1 = st.comfort_heat, st.comfort_cool
    zs = iter_zones(st)
    heat_need = max(h1 - z.current for z in zs)
    cool_need = max(z.current - c1 for z in zs)
    return heat_need <= 0.5 and cool_need <= 0.5


def vacation_boost_start(st: State) -> str:
    zs = iter_zones(st)
    start = sum(z.current for z in zs) / float(len(zs))
    st.vacation_start_temp = start
    if in_comfort_band(st):
        st.timers.vacation_boost = False
        return "in_band"
    st.timers.late_arrival = False
    st.timers.precool_safety = False
    st.timers.morning_boost = False
    st.timers.vacation_boost = True
    st.boost_starts += 1
    return "started"


def boost_reached_template(st: State) -> bool:
    if not st.timers.vacation_boost:
        return False
    zs = [z.current for z in iter_zones(st)]
    start = st.vacation_start_temp
    h1, c1 = st.comfort_heat, st.comfort_cool
    if start < h1:
        return all(c >= h1 for c in zs)
    if start > c1:
        return all(c <= c1 for c in zs)
    return all(h1 <= c <= c1 for c in zs)


def need_boost(st: State) -> bool:
    zs = [z.current for z in iter_zones(st)]
    spread = (max(zs) - min(zs)) if zs else 0.0
    o = st.outdoor
    return spread >= 2.5 or (o is not None and (o >= 78 or o <= 40))


def travel_use_cool(st: State) -> bool:
    latch = latch_of(st)
    o = st.outdoor
    return latch == "cool" or (latch not in ("heat", "cool") and o is not None and o >= SEASON)


def travel_comfort(st: State) -> float:
    return st.comfort_cool if travel_use_cool(st) else st.comfort_heat


def travel_delta(st: State) -> float:
    z = st.z2 if st.n_zones >= 2 else st.z1
    t = z.current
    return abs(t - travel_comfort(st)) if t is not None else 0.0


def lead_min(st: State) -> float:
    slope = 6.0 if travel_use_cool(st) else 8.0
    lead_raw = slope * travel_delta(st)
    a, b = 15.0, 60.0
    lo, hi = min(a, b), max(a, b)
    return min(hi, max(lo, lead_raw))


def family_eta(st: State) -> int:
    best = 9999
    if st.phones:
        for d, eta_raw in st.phones:
            if not toward_dir(str(d)):
                continue
            if isinstance(eta_raw, (int, float)) and not isinstance(eta_raw, bool):
                mins = int(eta_raw)
            else:
                mins = parse_eta(str(eta_raw))
            if 0 < mins < best:
                best = mins
    if st.teslas:
        for car in st.teslas:
            mins = tesla_eta_min(car)
            if 0 < mins < best:
                best = mins
    if best < 9999:
        return best
    if st.travel_raw:
        mins = parse_eta(st.travel_raw)
        if 0 < mins < 9999:
            return mins
    if toward_of(st.travel_kind):
        e = eta_of(st.travel_kind)
        if 0 < e < 9999:
            return e
    return 9999


def zmatch(z: Zone, hvac: str, *, temp: float | None = None,
           lo: float | None = None, hi: float | None = None, tol: float = 0.4) -> bool:
    if z.hvac != hvac:
        return False
    if hvac in ("heat", "cool"):
        return z.temperature is not None and temp is not None and abs(z.temperature - temp) <= tol
    if hvac == "heat_cool":
        return (
            z.target_low is not None and z.target_high is not None
            and lo is not None and hi is not None
            and abs(z.target_low - lo) <= tol and abs(z.target_high - hi) <= tol
        )
    return True


def zsnap(z: Zone) -> str:
    if z.hvac in ("heat", "cool"):
        return f"{z.hvac}:{z.temperature}"
    if z.hvac == "heat_cool":
        return f"heat_cool:{z.target_low}/{z.target_high}"
    return f"{z.hvac}"


def cancel_brain_timers(st: State) -> None:
    st.timers.writing_watch = False
    st.timers.away_debounce = False
    st.timers.empty_confirm = False
    st.timers.late_arrival = False
    st.timers.morning_boost = False
    st.timers.precool_safety = False
    st.timers.arrival_lockout = False
    st.timers.vacation_boost = False
    st.writing = False
    st.lockout_bool = False
    st.watchdog_active = False


def load_zone(st: State) -> None:
    z = int(st.edit_zone or 1)
    if z <= 2:
        p = "z1" if z == 1 else "z2"
        st.edit_comfort_heat = getattr(st, f"{p}_comfort_heat")
        st.edit_comfort_cool = getattr(st, f"{p}_comfort_cool")
        st.edit_away_heat = getattr(st, f"{p}_away_heat")
        st.edit_away_cool = getattr(st, f"{p}_away_cool")
        st.edit_boost_heat = getattr(st, f"{p}_boost_heat")
        st.edit_boost_cool = getattr(st, f"{p}_boost_cool")
        st.edit_night_heat = getattr(st, f"night_{p}_heat")
        st.edit_night_cool = getattr(st, f"night_{p}_cool")
        return
    zone = zone_at(st, z - 1)
    st.edit_comfort_heat = zone.comfort_heat
    st.edit_comfort_cool = zone.comfort_cool
    st.edit_away_heat = zone.away_heat
    st.edit_away_cool = zone.away_cool
    st.edit_boost_heat = zone.boost_heat
    st.edit_boost_cool = zone.boost_cool
    st.edit_night_heat = zone.night_heat
    st.edit_night_cool = zone.night_cool


def save_zone(st: State) -> None:
    z = int(st.edit_zone or 1)
    if z <= 2:
        p = "z1" if z == 1 else "z2"
        setattr(st, f"{p}_comfort_heat", st.edit_comfort_heat)
        setattr(st, f"{p}_comfort_cool", st.edit_comfort_cool)
        setattr(st, f"{p}_away_heat", st.edit_away_heat)
        setattr(st, f"{p}_away_cool", st.edit_away_cool)
        setattr(st, f"{p}_boost_heat", st.edit_boost_heat)
        setattr(st, f"{p}_boost_cool", st.edit_boost_cool)
        setattr(st, f"night_{p}_heat", st.edit_night_heat)
        setattr(st, f"night_{p}_cool", st.edit_night_cool)
        return
    zone = zone_at(st, z - 1)
    zone.comfort_heat = st.edit_comfort_heat
    zone.comfort_cool = st.edit_comfort_cool
    zone.away_heat = st.edit_away_heat
    zone.away_cool = st.edit_away_cool
    zone.boost_heat = st.edit_boost_heat
    zone.boost_cool = st.edit_boost_cool
    zone.night_heat = st.edit_night_heat
    zone.night_cool = st.edit_night_cool


def zone_defaults(st: State) -> None:
    z = int(st.edit_zone or 1)
    st.edit_comfort_heat, st.edit_comfort_cool = 71.0, 74.0
    st.edit_away_heat, st.edit_away_cool = 65.0, 78.0
    st.edit_boost_heat, st.edit_boost_cool = 73.0, 70.0
    st.edit_night_heat = 64.0 if z == 1 else 65.0
    st.edit_night_cool = 76.0 if z == 1 else 72.0
    save_zone(st)


def power_off(st: State) -> None:
    st.enabled = False
    cancel_brain_timers(st)
    st.status = "HVAC control off"
    st.stopped = "hvac_off"
    st.evaluate_skipped = True


def power_on(st: State) -> None:
    cancel_brain_timers(st)
    st.enabled = True
    if st.outdoor is not None and st.outdoor >= SEASON + 1:
        st.latch = "cool"
    if st.outdoor is not None and st.outdoor <= SEASON - 1:
        st.latch = "heat"
    evaluate(st, "power_on")


def startup(st: State, reason: str, gap: float) -> None:
    st.writing = False
    st.timers.writing_watch = False
    st.watchdog_active = False
    if st.outdoor is not None and st.outdoor >= SEASON + 1:
        st.latch = "cool"
    if st.outdoor is not None and st.outdoor <= SEASON - 1:
        st.latch = "heat"
    if (st.occupancy not in ("on", "off")
            and not st.vacation
            and not st.timers.vacation_boost):
        st.status = "HA start — occupancy not ready, no Away guess"
        st.stopped = "ha_start_occ_unknown"
        st.evaluate_skipped = True
        return
    if any(not z.available for z in iter_zones(st)):
        st.stopped = "ha_start_trane"
        st.evaluate_skipped = True
        return
    if gap > 300:
        st.timers.precool_safety = False
        st.timers.arrival_lockout = False
        st.timers.late_arrival = False
        st.timers.morning_boost = False
        st.timers.away_debounce = False
        st.timers.vacation_boost = False
        st.timers.empty_confirm = False
        st.lockout_bool = False
    if occupied(st) and (st.z2_hm <= st.hm < st.z1_hm) and need_boost(st):
        st.timers.morning_boost = True
    evaluate(st, reason)


def handle(st: State, event: str) -> None:
    st.trigger_seq.append(event)
    st.stopped = None
    st.evaluate_skipped = False

    if event in ("hvac_off", "enabled_off"):
        power_off(st)
        return
    if event in ("hvac_on", "enabled_on"):
        power_on(st)
        return
    if event == "load_zone":
        load_zone(st)
        st.stopped = "load_zone"
        st.evaluate_skipped = True
        return
    if event == "save_zone":
        save_zone(st)
        st.stopped = "save_zone"
        st.evaluate_skipped = True
        return
    if event == "zone_defaults":
        zone_defaults(st)
        st.stopped = "zone_defaults"
        st.evaluate_skipped = True
        return

    if not st.enabled and event not in ("evaluate", "enabled"):
        st.stopped = "disabled_router"
        st.evaluate_skipped = True
        return

    if event in TIME_EVENTS and not st.time_triggers_bound:
        live = {"night_start": st.night_hm, "morning_z2": st.z2_hm,
                "morning_z1": st.z1_hm, "day_start": st.day_hm}
        if st.hm != live.get(event, CLOCK_HM[event]):
            st.missed_time.append(event)
            st.stopped = "time_trigger_unbound"
            st.evaluate_skipped = True
            return

    if event == "vacation_on":
        st.vacation = True
        st.timers.precool_safety = False
        st.timers.late_arrival = False
        st.timers.morning_boost = False
        st.timers.vacation_boost = False
        evaluate(st, "vacation")
        return

    if event == "vacation_off":
        st.vacation = False
        vacation_boost_start(st)
        evaluate(st, "vacation")
        return

    if event in ("vacation_boost_done", "vacation_boost_reached"):
        if event == "vacation_boost_reached" and not boost_reached_template(st):
            st.stopped = "reached_template_false"
            st.evaluate_skipped = True
            return
        st.timers.vacation_boost = False
        evaluate(st, event)
        return

    if event == "occupancy_off":
        prev = st.occupancy
        st.occupancy_from = prev
        st.occupancy = "off"
        if prev in UNAVAIL:
            evaluate(st, "occupancy_restore")
            st.stopped = "occupancy_restore_off"
            return
        st.timers.away_debounce = True
        st.timers.empty_confirm = True
        st.empty_since_sec = 0.0
        st.was_empty_15m = False
        st.stopped = "occupancy_off_debounce"
        st.evaluate_skipped = True
        return

    if event == "occupancy_on":
        prev = st.occupancy
        st.occupancy_from = prev
        st.occupancy = "on"
        if prev in UNAVAIL:
            st.timers.away_debounce = False
            st.timers.empty_confirm = False
            if st.z2_hm <= st.hm < st.z1_hm and need_boost(st):
                st.timers.morning_boost = True
            evaluate(st, "occupancy_restore")
            st.stopped = "occupancy_restore_on"
            return
        empty_sec = st.empty_since_sec
        was_debouncing = st.timers.away_debounce or empty_sec < st.debounce_sec
        real_arrival = empty_sec >= st.empty_need_sec
        until_z2 = (st.z2_hm - st.hm + 1440) % 1440
        st.timers.away_debounce = False
        st.timers.empty_confirm = False
        if was_debouncing:
            st.stopped = "flicker"
            st.evaluate_skipped = True
            return
        cleared_vacation = st.vacation and real_arrival
        if cleared_vacation:
            st.vacation = False
            st.queued.append("vacation_off")
        st.timers.precool_safety = False
        st.timers.arrival_lockout = True
        st.lockout_bool = True
        st.was_empty_15m = False
        if cleared_vacation:
            vacation_boost_start(st)
        elif real_arrival and in_night(st.hm) and until_z2 > 0:
            st.timers.late_arrival = True
        evaluate(st, "occupancy_on")
        return

    if event == "away_debounce_done":
        st.timers.away_debounce = False
        if occupied(st):
            st.stopped = "debounce_occupied"
            st.evaluate_skipped = True
            return
        st.timers.late_arrival = False
        st.timers.morning_boost = False
        if family_eta(st) >= 9999:
            st.timers.precool_safety = False
        evaluate(st, "away_debounce_done")
        return

    if event == "empty_confirm_done":
        st.timers.empty_confirm = False
        if occupied(st):
            st.stopped = "confirm_occupied"
            st.evaluate_skipped = True
            return
        st.was_empty_15m = True
        evaluate(st, "empty_confirm_done")
        return

    if event == "night_start":
        evaluate(st, "night_start")
        return

    if event == "morning_z2":
        st.timers.late_arrival = False
        prev_mb = st.timers.morning_boost
        if occupied(st) and need_boost(st):
            st.timers.morning_boost = True
        st.mb_started_this = (not prev_mb) and st.timers.morning_boost
        evaluate(st, "morning_z2")
        return

    if event == "morning_z1":
        st.timers.late_arrival = False
        st.timers.morning_boost = False
        st.timers.precool_safety = False
        evaluate(st, "morning_z1")
        return

    if event == "day_start":
        evaluate(st, "day_start")
        return

    if event in ("outdoor_summer", "outdoor_winter"):
        if event == "outdoor_summer":
            if st.outdoor is None or st.outdoor < SEASON + 1:
                st.stopped = "summer_template_false"
                st.evaluate_skipped = True
                return
            new_latch = "cool"
        else:
            if st.outdoor is None or not (st.outdoor <= SEASON - 1):
                st.stopped = "winter_template_false"
                st.evaluate_skipped = True
                return
            new_latch = "heat"
        if st.latch != new_latch:
            st.latch = new_latch
            st.queued.append("latch")
        else:
            st.latch = new_latch
        if occupied(st) or st.timers.away_debounce or st.timers.precool_safety:
            st.stopped = "outdoor_occupied"
            st.evaluate_skipped = True
            return
        evaluate(st, event)
        return

    if event == "latch":
        if occupied(st) or st.timers.away_debounce or st.timers.precool_safety:
            st.stopped = "latch_occupied"
            st.evaluate_skipped = True
            return
        evaluate(st, "latch")
        return

    if event.startswith("ha_start"):
        if event == "ha_start_2min":
            gap = 2 * 60
        elif event == "ha_start_10min":
            gap = 10 * 60
        else:
            gap = 6 * 3600
        startup(st, "ha_start", gap)
        return

    if event == "yaml_reload":
        st.time_triggers_bound = False
        gap = st.last_write_age if st.last_write_valid else 99999.0
        startup(st, "reloaded", gap)
        return

    if event == "travel":
        if not st.phase2:
            st.stopped = "phase2_off"
            st.evaluate_skipped = True
            return
        if st.teslas:
            for car in st.teslas:
                car.direction = tesla_direction(car)
        eta = family_eta(st)
        if st.teslas:
            for car in st.teslas:
                if car.dist_km is not None:
                    car.last_km = float(car.dist_km)
        lead = lead_min(st)
        empty = st.occupancy == "off"
        occ = occupied(st)
        should_start = (
            0 < eta < 9999 and eta <= lead and empty
            and not st.vacation
            and not st.timers.vacation_boost
            and not st.timers.away_debounce
            and not st.lockout_bool
            and not st.timers.arrival_lockout
            and not st.timers.precool_safety
        )
        someone_toward = 0 < eta < 9999
        should_cancel = (
            st.timers.precool_safety and (
                occ or st.vacation or st.timers.vacation_boost
                or (not empty) or st.timers.away_debounce or (not someone_toward)
                or (eta > lead + 5)
            )
        )
        if should_start:
            if (occ or st.vacation or st.timers.vacation_boost
                    or st.timers.away_debounce or st.lockout_bool):
                st.precool_illegal = True
            st.timers.precool_safety = True
            st.precool_started_valid = True
            t = st.z2.current
            st.precool_start_temp = t if t is not None else travel_comfort(st)
            st.precool_starts += 1
        if should_cancel:
            st.timers.precool_safety = False
        if not should_start and not should_cancel:
            st.stopped = "travel_no_cross"
            st.evaluate_skipped = True
            return
        evaluate(st, "travel")
        return

    if event == "precool_safety":
        st.timers.precool_safety = False
        evaluate(st, "precool_safety")
        return

    if event == "arrival_lockout_done":
        st.lockout_bool = False
        st.timers.arrival_lockout = False
        st.stopped = "arrival_lockout_expired"
        st.evaluate_skipped = True
        return

    if event == "late_arrival_done":
        st.timers.late_arrival = False
        evaluate(st, "late_arrival_done")
        return

    if event == "morning_boost_done":
        st.timers.morning_boost = False
        evaluate(st, "morning_boost_done")
        return

    if event == "occupancy_unknown":
        st.occupancy_from = st.occupancy
        st.occupancy = "unknown"
        st.stopped = "occupancy_went_unknown"
        st.evaluate_skipped = True
        return

    if event == "writing_watch_done":
        if st.timers.writing_watch or st.writing:
            st.writing = False
            st.timers.writing_watch = False
            st.watchdog_active = False
            st.stopped = "watchdog_cleared"
        else:
            st.stopped = "watchdog_inactive"
        st.evaluate_skipped = True
        return

    if event in ("evaluate", "enabled", "home_hvac", "reloaded", "setpoints"):
        if event == "reloaded":
            startup(st, "reloaded", st.last_write_age if st.last_write_valid else 99999.0)
            return
        evaluate(st, "manual" if event == "evaluate" else event)
        return

    if event == "night_slider":
        if period_of(st) not in ("night", "morning_z2"):
            st.stopped = "sliders_not_night"
            st.evaluate_skipped = True
            return
        evaluate(st, "night_slider")
        return

    st.stopped = f"unknown_event:{event}"
    st.evaluate_skipped = True


def fire(st: State, event: str) -> None:
    st.eval_this = 0
    st.writes_this = 0
    st.trigger_seq = []
    st.period_seq = []
    st.write_seq = []
    st.eval_seq = []
    st.queued = []
    st.missed_time = []
    st.boost_starts = 0
    st.precool_starts = 0
    st.mb_started_this = False
    st.write_recs = []
    st.brain_temps = []
    st.writing_leaked = False
    st.precool_illegal = False
    chain = 0
    handle(st, event)
    while st.queued:
        chain += 1
        if chain > LOOP_LIMIT:
            st.stopped = "WRITE_LOOP"
            return
        if chain > ROUTER_MAX:
            st.stopped = "ROUTER_MAX"
            return
        nxt = st.queued.pop(0)
        handle(st, nxt)
    if st.writing and not st.hang_after_writing:
        st.writing_leaked = True


def make(**kw) -> State:
    st = State()
    rooms = kw.pop("rooms", (70.0, 72.0))
    st.z1.current = float(rooms[0])
    st.z2.current = float(rooms[1])
    st.travel_kind = kw.pop("travel", "none")
    vb = kw.pop("vacation_boost", False)
    debounce = kw.pop("debounce", False)
    precool = kw.pop("precool", False)
    late = kw.pop("late_hold", False)
    lockout = kw.pop("lockout", False)
    mboost = kw.pop("morning_boost", False)
    econfirm = kw.pop("empty_confirm", False)
    time_label = kw.pop("time", None)
    if time_label is not None:
        for name, hm in TIMES:
            if name == time_label:
                st.hm = hm
                break
        else:
            if isinstance(time_label, int):
                st.hm = time_label
    hm = kw.pop("hm", None)
    if hm is not None:
        st.hm = hm
    occupancy = kw.pop("occupancy", None)
    if occupancy is not None:
        st.occupancy = occupancy
        st.occupancy_from = occupancy
    occ_from = kw.pop("occupancy_from", None)
    if occ_from is not None:
        st.occupancy_from = occ_from
    for k, v in kw.items():
        if hasattr(st, k):
            setattr(st, k, v)
    st.timers.vacation_boost = bool(vb)
    st.timers.away_debounce = bool(debounce)
    st.timers.precool_safety = bool(precool)
    st.timers.late_arrival = bool(late)
    st.timers.arrival_lockout = bool(lockout)
    st.timers.morning_boost = bool(mboost)
    st.timers.empty_confirm = bool(econfirm)
    if lockout:
        st.lockout_bool = True
    return st


def js_toward(dir_raw: str) -> bool:
    d = str(dir_raw or "").lower()
    return ("toward" in d) and ("inhome" not in d) and ("instat" not in d)


def aba(seq: list) -> bool:
    if len(seq) < 3:
        return False
    for i in range(len(seq) - 2):
        if seq[i] == seq[i + 2] and seq[i] != seq[i + 1]:
            return True
    return False


def forbidden_writes(st: State) -> list[float]:
    return [t for t in st.brain_temps if float(t) in FORBIDDEN_TEMPS]


def inverted_boost(rec: dict) -> bool:
    if rec.get("kind") != "dual":
        return False
    lo, hi = rec.get("low"), rec.get("high")
    return (lo, hi) in ((73.0, 70.0), (73.0, 76.0), (70.0, 73.0))
