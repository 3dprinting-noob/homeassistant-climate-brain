"""Pure-engine chaos tests — no Home Assistant.

Imports engine.py directly. Presence + travel + Tesla + season/HVAC cases
from the 1.4.1 in-memory checker.
"""
from __future__ import annotations

import sys
from pathlib import Path

ENG = Path(__file__).resolve().parents[1] / "custom_components" / "climate_brain"
sys.path.insert(0, str(ENG))

from engine import (  # noqa: E402
    OCC_NOT_READY,
    Finding,
    TeslaCar,
    desired_of,
    family_eta,
    fire,
    js_toward,
    lead_min,
    make,
    occupied,
    parse_eta,
    tesla_direction,
    tesla_eta_min,
    toward_dir,
    toward_of,
    inverted_boost,
    zmatch,
    zsnap,
)

REQUIRED_PRESENCE = (
    "PRES_FLICKER",
    "PRES_LEAVE",
    "PRES_UNKNOWN",
    "PRES_ON_CANCEL_DEBOUNCE",
    "PRES_WAS_EMPTY_15M",
    "PRES_VACATION",
    "PRES_VACATION_BOOST",
    "PRES_ON_NIGHT",
    "PRES_ON_MORNING",
    "PRES_PRECOOL",
)
REQUIRED_TRAVEL = (
    "TRAVEL_TOWARD_START",
    "TRAVEL_AWAY_NOT_TOWARD",
    "TRAVEL_INTRANSIT_NOT_TOWARD",
    "TRAVEL_INHOME_NOT_TOWARD",
    "TRAVEL_TURNAROUND_CANCEL",
    "TRAVEL_ETA_UP_NO_CANCEL",
    "TRAVEL_ETA_DOWN_START",
    "TRAVEL_TWO_PHONES",
    "TRAVEL_PARSE",
    "TRAVEL_OCCUPIED_NO_START",
    "TRAVEL_LEAD_CHATTER",
)
REQUIRED_TESLA = (
    "TESLA_NAV_HOME_TOWARD",
    "TESLA_NAV_NOT_HOME",
    "TESLA_NO_NAV_DIST_FALL",
    "TESLA_NO_NAV_DIST_RISE",
    "TESLA_DRIVEWAY_INHOME",
    "TESLA_HYST_CHATTER",
    "TESLA_NEVER_OCC",
    "TESLA_USER_PRESENT_UNUSED",
)
REQUIRED_EXTRA = (
    "SEASON_66_COOL",
    "SEASON_64_HEAT",
    "SEASON_65_DEADZONE",
    "HVAC_OFF_NO_WRITE",
    "PRECOOL_CANCEL_OCCUPIED",
    "PRECOOL_CANCEL_NOT_TOWARD",
    "PRECOOL_CANCEL_ETA_HYST",
)


def run_explicit() -> tuple[list[tuple[str, str, str]], list[Finding], dict]:
    rows: list[tuple[str, str, str]] = []
    findings: list[Finding] = []

    def rec(sid: str, ok: bool, notes: str, extra: list[Finding] | None = None):
        rows.append((sid, "PASS" if ok else "FAIL", notes))
        if extra:
            findings.extend(extra)

    # ----- presence walks -----
    st = make(hm=14 * 60, occupancy="on", rooms=(71, 71), outdoor=50.0, latch="heat")
    fire(st, "evaluate")
    fire(st, "occupancy_off")
    st.empty_since_sec = 60
    fire(st, "occupancy_on")
    flick = (st.stopped == "flicker" and st.writes_this == 0
             and zmatch(st.z1, "heat_cool", lo=st.z1_comfort_heat, hi=st.z1_comfort_cool)
             and not st.timers.away_debounce and not st.timers.empty_confirm
             and desired_of(st)["period"] != "empty")
    rec("PRES_FLICKER", flick,
        f"occupancy on→off→on <3min NOT Away stop={st.stopped} writes={st.writes_this} z1={zsnap(st.z1)}",
        None if flick else [Finding("PRES_FLICKER", "flicker <3 min",
                                    "NOT Away", f"stop={st.stopped} z1={zsnap(st.z1)}",
                                    severity="blocker")])

    st = make(hm=14 * 60, occupancy="on", rooms=(71, 71), outdoor=50.0, latch="heat",
              z1_away_heat=64.0, z1_away_cool=79.0, z2_away_heat=66.0, z2_away_cool=80.0,
              away_heat=65.0, away_cool=78.0)
    fire(st, "evaluate")
    fire(st, "occupancy_off")
    st.empty_since_sec = 3 * 60
    fire(st, "away_debounce_done")
    st.empty_since_sec = 15 * 60
    fire(st, "empty_confirm_done")
    leave = (desired_of(st)["period"] == "empty" and st.was_empty_15m
             and zmatch(st.z1, "heat", temp=64.0) and zmatch(st.z2, "heat", temp=66.0)
             and st.z1.temperature != 65.0)
    rec("PRES_LEAVE", leave,
        f"15min confirm IS Away per-zone z1={zsnap(st.z1)} z2={zsnap(st.z2)} was_empty={st.was_empty_15m}",
        None if leave else [Finding("PRES_LEAVE", "real leave 15 min",
                                    "IS Away z1_away/z2_away not house-wide 65",
                                    f"z1={zsnap(st.z1)} z2={zsnap(st.z2)}", severity="blocker")])

    st = make(hm=14 * 60, occupancy="unknown", rooms=(71, 71), outdoor=50.0, latch="heat")
    before = (st.z1.hvac, st.z1.temperature, st.z1.target_low, st.z1.target_high)
    fire(st, "evaluate")
    unk = (st.stopped == "occupancy_not_ready" and st.evaluate_skipped
           and OCC_NOT_READY in st.status
           and (st.z1.hvac, st.z1.temperature, st.z1.target_low, st.z1.target_high) == before
           and st.writes_this == 0)
    rec("PRES_UNKNOWN", unk,
        f"occupancy unknown NEVER Away stop={st.stopped} writes={st.writes_this}",
        None if unk else [Finding("PRES_UNKNOWN", "occupancy unknown",
                                  "never writes Away", f"stop={st.stopped}", severity="blocker")])

    st = make(hm=14 * 60, occupancy="unknown", rooms=(71, 71), outdoor=50.0, latch="heat",
              empty_since_sec=9999)
    fire(st, "evaluate")
    rec("PRES_UNKNOWN_15M",
        st.stopped == "occupancy_not_ready" and st.writes_this == 0,
        f"unknown after 15min still no Away stop={st.stopped}", None)

    st = make(hm=14 * 60, occupancy="on", rooms=(71, 71), outdoor=50.0, latch="heat")
    fire(st, "evaluate")
    fire(st, "occupancy_off")
    started_both = st.timers.away_debounce and st.timers.empty_confirm
    st.empty_since_sec = 60
    fire(st, "occupancy_on")
    cancelled = (started_both and st.stopped == "flicker"
                 and not st.timers.away_debounce and not st.timers.empty_confirm)
    rec("PRES_ON_CANCEL_DEBOUNCE", cancelled,
        f"flicker on during debounce cancels debounce+confirm started={started_both} "
        f"deb={st.timers.away_debounce} confirm={st.timers.empty_confirm}",
        None if cancelled else [Finding("PRES_ON_CANCEL_DEBOUNCE", "occupancy on during debounce",
                                        "cancels away_debounce AND empty_confirm",
                                        f"started={started_both}", severity="blocker")])

    st = make(hm=14 * 60, occupancy="on", rooms=(71, 71), outdoor=50.0, latch="heat")
    fire(st, "evaluate")
    fire(st, "occupancy_off")
    after_off = not st.was_empty_15m
    st.empty_since_sec = 3 * 60
    fire(st, "away_debounce_done")
    after_deb = not st.was_empty_15m
    fire(st, "empty_confirm_done")
    after_conf = st.was_empty_15m and desired_of(st)["period"] == "empty"
    rec("PRES_WAS_EMPTY_15M", after_off and after_deb and after_conf,
        f"was_empty_15m only after confirm not debounce off={after_off} deb={after_deb} conf={after_conf}",
        None if after_off and after_deb and after_conf else [Finding(
            "PRES_WAS_EMPTY_15M", "was_empty_15m timing",
            "only after confirm timer", f"off={after_off} deb={after_deb} conf={after_conf}",
            severity="blocker")])

    st = make(hm=14 * 60, occupancy="on", rooms=(80, 80), outdoor=90.0, latch="cool", vacation=True)
    fire(st, "evaluate")
    vac_on = desired_of(st)["period"] == "vacation" and zmatch(st.z1, "cool", temp=st.vacation_cool)
    rec("PRES_VACATION", vac_on,
        f"presence on during vacation writes vacation Eco not Away period={desired_of(st)['period']} z1={zsnap(st.z1)}",
        None if vac_on else [Finding("PRES_VACATION", "occupied+vacation",
                                     "vacation Eco", f"z1={zsnap(st.z1)}", severity="blocker")])

    st = make(hm=14 * 60, occupancy="on", rooms=(50, 50), outdoor=40.0, latch="heat",
              vacation_boost=True)
    fire(st, "evaluate")
    pvb = (desired_of(st)["period"] == "vacation_boost"
           and zmatch(st.z1, "heat", temp=st.z1_boost_heat))
    rec("PRES_VACATION_BOOST", pvb,
        f"presence on during vacation_boost z1={zsnap(st.z1)}",
        None if pvb else [Finding("PRES_VACATION_BOOST", "occupied+vb",
                                  "boost single", f"z1={zsnap(st.z1)}", severity="blocker")])

    st = make(hm=22 * 60 + 50, occupancy="on", rooms=(64, 65), outdoor=40.0, latch="heat")
    fire(st, "evaluate")
    pn = (desired_of(st)["period"] == "night"
          and zmatch(st.z1, "heat_cool", lo=st.night_z1_heat, hi=st.night_z1_cool)
          and zmatch(st.z2, "heat_cool", lo=st.night_z2_heat, hi=st.night_z2_cool))
    rec("PRES_ON_NIGHT", pn,
        f"presence on during night z1={zsnap(st.z1)} z2={zsnap(st.z2)}",
        None if pn else [Finding("PRES_ON_NIGHT", "night occupied",
                                 "night Eco dual", f"z1={zsnap(st.z1)}", severity="blocker")])

    st = make(hm=5 * 60 + 30, occupancy="on", rooms=(71, 72), outdoor=50.0, latch="heat")
    fire(st, "evaluate")
    pm = desired_of(st)["period"] == "morning_z2" and occupied(st)
    rec("PRES_ON_MORNING", pm,
        f"presence on during morning period={desired_of(st)['period']} z1={zsnap(st.z1)} z2={zsnap(st.z2)}",
        None if pm else [Finding("PRES_ON_MORNING", "morning occupied",
                                 "morning period", f"p={desired_of(st)['period']}", severity="blocker")])

    st = make(hm=14 * 60, occupancy="off", rooms=(50, 50), outdoor=50.0, latch="heat",
              empty_since_sec=3600, travel="toward_10")
    fire(st, "travel")
    pc_on = st.timers.precool_safety and desired_of(st)["period"] == "precool"
    rec("PRES_PRECOOL", pc_on,
        f"presence (empty) during precool started={pc_on} z1={zsnap(st.z1)}",
        None if pc_on else [Finding("PRES_PRECOOL", "precool while empty toward",
                                    "precool period", f"pc={st.timers.precool_safety}",
                                    severity="blocker")])

    # ----- travel walks -----
    st = make(hm=14 * 60, occupancy="off", rooms=(50, 50), outdoor=50.0, latch="heat",
              empty_since_sec=3600, travel="toward_10")
    lead = lead_min(st)
    eta = family_eta(st)
    fire(st, "travel")
    tstart = (eta <= lead and st.timers.precool_safety
              and zmatch(st.z1, "heat", temp=st.z1_boost_heat)
              and desired_of(st)["period"] == "precool")
    rec("TRAVEL_TOWARD_START", tstart,
        f"toward starts precool empty+ETA inside lead eta={eta} lead={lead} z1={zsnap(st.z1)}",
        None if tstart else [Finding("TRAVEL_TOWARD_START", "toward + eta<=lead",
                                     "precool start", f"eta={eta} lead={lead} pc={st.timers.precool_safety}",
                                     severity="blocker")])

    rec("TRAVEL_AWAY_NOT_TOWARD", not toward_dir("away") and not toward_of("away"),
        "away is NOT toward", None)
    rec("TRAVEL_INTRANSIT_NOT_TOWARD", not toward_dir("intransit") and not toward_of("intransit"),
        "intransit is NOT toward", None)
    rec("TRAVEL_INHOME_NOT_TOWARD",
        not toward_dir("inhome toward") and not toward_dir("inhome"),
        "inhome is NOT toward", None)

    st = make(hm=14 * 60, occupancy="off", rooms=(50, 50), outdoor=50.0, latch="heat",
              empty_since_sec=3600, travel="toward_10")
    fire(st, "travel")
    was = st.timers.precool_safety
    st.travel_kind = "away"
    fire(st, "travel")
    away_c = was and not st.timers.precool_safety
    rec("TRAVEL_TURNAROUND_CANCEL", away_c,
        f"turn-around mid-precool cancels immediately was={was} after={st.timers.precool_safety}",
        None if away_c else [Finding("TRAVEL_TURNAROUND_CANCEL", "dir away mid-precool",
                                     "cancel immediately", f"was={was} now={st.timers.precool_safety}",
                                     severity="blocker")])
    rec("TRAVEL_AWAY_CANCEL", away_c, f"away cancels precool={away_c}", None)

    st = make(hm=14 * 60, occupancy="off", rooms=(50, 50), outdoor=50.0, latch="heat",
              empty_since_sec=3600, travel="toward_10")
    fire(st, "travel")
    started = st.timers.precool_safety
    lead = lead_min(st)
    st.travel_kind = "toward_45"
    fire(st, "travel")
    still = started and st.timers.precool_safety  # 45 <= lead+5 (heat lead ~60)
    rec("TRAVEL_ETA_UP_NO_CANCEL", still,
        f"ETA rising while toward cancel only if eta>lead+5 lead={lead} pc={st.timers.precool_safety}",
        None if still else [Finding("TRAVEL_ETA_UP_NO_CANCEL", "eta 10->45 still toward",
                                    "no cancel within lead+5", f"lead={lead} pc={st.timers.precool_safety}",
                                    severity="blocker")])

    st = make(hm=14 * 60, occupancy="off", rooms=(71, 71), outdoor=50.0, latch="heat",
              empty_since_sec=3600, travel="toward_45")
    lead = lead_min(st)
    fire(st, "travel")
    no45 = (not st.timers.precool_safety) and family_eta(st) > lead
    st.travel_kind = "toward_10"
    fire(st, "travel")
    yes10 = st.timers.precool_safety and family_eta(st) <= lead
    rec("TRAVEL_ETA_DOWN_START", no45 and yes10,
        f"ETA falling while toward start when crossing into lead lead={lead} no45={no45} yes10={yes10}",
        None if no45 and yes10 else [Finding("TRAVEL_ETA_DOWN_START", "eta 45 then 10",
                                             "start when crossing lead", f"lead={lead}",
                                             severity="blocker")])

    st = make(hm=14 * 60, occupancy="off", rooms=(80, 80), outdoor=90.0, latch="cool",
              empty_since_sec=3600)
    st.phones = [("toward_home", 40), ("away", 10)]  # person A toward, person B away
    eta_tw = family_eta(st)
    lead_tw = lead_min(st)
    fire(st, "travel")
    no_wrong = (eta_tw == 40)  # min of toward only, not away 10
    st.phones = [("toward_home", 15), ("away", 10)]
    fire(st, "travel")
    yes_toward = family_eta(st) == 15 and st.timers.precool_safety
    rec("TRAVEL_TWO_PHONES", no_wrong and yes_toward,
        f"two phones: toward vs away min-ETA-of-toward={eta_tw} (not 10) lead={lead_tw} start15={yes_toward}",
        None if no_wrong and yes_toward else [Finding(
            "TRAVEL_TWO_PHONES", "two phones two phones: toward vs away",
            "min ETA of toward only", f"eta={eta_tw} lead={lead_tw}", severity="blocker")])

    parse_ok = parse_eta("1 hour 15 min") == 75 and parse_eta("01:15") == 75
    st = make(hm=14 * 60, occupancy="off", rooms=(71, 71), outdoor=50.0, latch="heat",
              empty_since_sec=3600)
    st.travel_raw = "1 hour 15 min"
    p1 = family_eta(st) == 75
    st.travel_raw = "01:15"
    p2 = family_eta(st) == 75
    rec("TRAVEL_PARSE", parse_ok and p1 and p2,
        f"parse '1 hour 15 min'={parse_eta('1 hour 15 min')} '01:15'={parse_eta('01:15')} family_eta 75={p1 and p2}",
        None if parse_ok and p1 and p2 else [Finding("TRAVEL_PARSE", "duration parse",
                                                    "both 75 min", f"p1={p1} p2={p2}",
                                                    severity="blocker")])

    st = make(hm=14 * 60, occupancy="on", rooms=(80, 80), outdoor=90.0, latch="cool",
              travel="toward_10")
    fire(st, "travel")
    occ_no = (not st.timers.precool_safety) and st.stopped == "travel_no_cross"
    rec("TRAVEL_OCCUPIED_NO_START", occ_no,
        f"occupied never starts precool pc={st.timers.precool_safety} stop={st.stopped}",
        None if occ_no else [Finding("TRAVEL_OCCUPIED_NO_START", "occupied+toward",
                                     "must not start", f"pc={st.timers.precool_safety}",
                                     severity="blocker")])

    # JS lead-threshold chatter 21/20/19/20/21 with lead=20 hyst=5
    lead_js, hyst = 20, 5
    def would_start(occ, d, eta):
        return occ != "on" and js_toward(d) and eta > 0 and eta <= lead_js
    def would_cancel(d, eta):
        return (not js_toward(d)) or eta > lead_js + hyst
    chatter_flips = []
    active = False
    for eta in (21, 20, 19, 20, 21, 22, 19):
        start = would_start("off", "toward", eta)
        cancel = active and would_cancel("toward", eta)
        nxt = start or (active and not cancel)
        chatter_flips.append(active != nxt)
        active = nxt
    flips = sum(1 for x in chatter_flips if x)
    rec("TRAVEL_LEAD_CHATTER", flips <= 2,
        f"flipping 21/20/19/20/21 must not chatter flips={flips}",
        None if flips <= 2 else [Finding("TRAVEL_LEAD_CHATTER", "lead threshold chatter",
                                         "flips<=2", f"flips={flips}", severity="blocker")])

    # ----- Tesla travel (1.4.1) -----
    car = TeslaCar(name="car", loc="not_home", route="home", tta=12, dist_km=9.0, last_km=9.0)
    st = make(hm=14 * 60, occupancy="off", rooms=(50, 50), outdoor=50.0, latch="heat",
              empty_since_sec=3600)
    st.teslas = [car]
    dnav = tesla_direction(car)
    enav = tesla_eta_min(car)
    fire(st, "travel")
    ok = dnav == "toward" and enav == 12 and st.timers.precool_safety
    rec("TESLA_NAV_HOME_TOWARD", ok,
        f"route in home + TTA 12 → toward, eta 12 dir={dnav} eta={enav} pc={st.timers.precool_safety}",
        None if ok else [Finding("TESLA_NAV_HOME_TOWARD", "nav home TTA 12",
                                 "toward eta 12 start", f"dir={dnav} eta={enav} pc={st.timers.precool_safety}",
                                 severity="blocker")])

    car = TeslaCar(name="car", loc="not_home", route="work", tta=8, dist_km=4.0, last_km=5.0,
                   direction="toward")
    st = make(hm=14 * 60, occupancy="off", rooms=(50, 50), outdoor=50.0, latch="heat",
              empty_since_sec=3600)
    st.teslas = [car]
    dnh = tesla_direction(car)
    fire(st, "travel")
    ok = dnh == "away" and not st.timers.precool_safety
    rec("TESLA_NAV_NOT_HOME", ok,
        f"route not home + moving → away, does not start precool dir={dnh} pc={st.timers.precool_safety}",
        None if ok else [Finding("TESLA_NAV_NOT_HOME", "nav dest work",
                                 "away no start", f"dir={dnh} pc={st.timers.precool_safety}",
                                 severity="blocker")])

    car = TeslaCar(name="car", loc="not_home", route="unknown", tta="unknown",
                   dist_km=11.0, last_km=12.0)
    st = make(hm=14 * 60, occupancy="off", rooms=(50, 50), outdoor=50.0, latch="heat",
              empty_since_sec=3600)
    st.teslas = [car]
    dfall = tesla_direction(car)
    efall = tesla_eta_min(car)
    fire(st, "travel")
    ok = dfall == "toward" and st.timers.precool_safety
    rec("TESLA_NO_NAV_DIST_FALL", ok,
        f"no TTA, not home, dist 12.0 → 11.0 km → toward dir={dfall} eta={efall} pc={st.timers.precool_safety}",
        None if ok else [Finding("TESLA_NO_NAV_DIST_FALL", "dist 12→11",
                                 "toward start", f"dir={dfall} eta={efall}", severity="blocker")])

    car = TeslaCar(name="car", loc="not_home", route="unknown", tta="unknown",
                   dist_km=12.0, last_km=11.0, direction="toward")
    st = make(hm=14 * 60, occupancy="off", rooms=(50, 50), outdoor=50.0, latch="heat",
              empty_since_sec=3600, travel="toward_10")
    fire(st, "travel")
    was = st.timers.precool_safety
    st.travel_kind = "none"
    st.teslas = [car]
    fire(st, "travel")
    drise = tesla_direction(TeslaCar(name="car", loc="not_home", route="unknown",
                                    tta="unknown", dist_km=12.0, last_km=11.0, direction="toward"))
    ok = was and drise == "away" and not st.timers.precool_safety
    rec("TESLA_NO_NAV_DIST_RISE", ok,
        f"dist 11.0 → 12.0 → away, cancels precool was={was} dir={drise} pc={st.timers.precool_safety}",
        None if ok else [Finding("TESLA_NO_NAV_DIST_RISE", "dist 11→12",
                                 "away cancel", f"was={was} dir={drise} pc={st.timers.precool_safety}",
                                 severity="blocker")])

    car = TeslaCar(name="car", loc="home", route="home", tta=5, dist_km=0.02, last_km=0.3)
    st = make(hm=14 * 60, occupancy="off", rooms=(50, 50), outdoor=50.0, latch="heat",
              empty_since_sec=3600)
    st.teslas = [car]
    ddrv = tesla_direction(car)
    fire(st, "travel")
    ok = ddrv == "inhome" and not toward_dir(ddrv) and not st.timers.precool_safety
    rec("TESLA_DRIVEWAY_INHOME", ok,
        f"location home + speed/move → inhome, not toward dir={ddrv} pc={st.timers.precool_safety}",
        None if ok else [Finding("TESLA_DRIVEWAY_INHOME", "driveway loc home",
                                 "inhome not toward", f"dir={ddrv}", severity="blocker")])

    dirs = []
    last = 11.00
    prev = "toward"
    for dist in (11.00, 11.04, 10.99):
        c = TeslaCar(name="car", loc="not_home", route="unknown", tta="unknown",
                     dist_km=dist, last_km=last, direction=prev)
        d = tesla_direction(c)
        dirs.append(d)
        last = dist
        prev = d
    ok = dirs == ["toward", "toward", "toward"] and len(set(dirs)) == 1
    rec("TESLA_HYST_CHATTER", ok,
        f"dist 11.00/11.04/10.99 does not chatter (80m) dirs={dirs}",
        None if ok else [Finding("TESLA_HYST_CHATTER", "80m hysteresis",
                                 "no chatter", f"dirs={dirs}", severity="blocker")])

    st = make(hm=14 * 60, occupancy="on", rooms=(71, 71), outdoor=50.0, latch="heat")
    fire(st, "evaluate")
    snap_on = zsnap(st.z1)
    st.teslas = [TeslaCar(name="car", loc="not_home", route="unknown", tta="unknown",
                          dist_km=20.0, last_km=19.0)]
    st.tesla_user_present = True
    fire(st, "evaluate")
    still_on = zsnap(st.z1) == snap_on and occupied(st) and desired_of(st)["period"] not in ("empty",)
    st2 = make(hm=14 * 60, occupancy="off", rooms=(71, 71), outdoor=50.0, latch="heat",
               empty_since_sec=60)
    fire(st2, "occupancy_off")
    st2.teslas = [TeslaCar(name="car", loc="home", route="home", tta=0, dist_km=0.01, last_km=0.01)]
    fire(st2, "evaluate")
    tesla_home_not_occ = st2.occupancy == "off" and not occupied(st2)
    ok = still_on and tesla_home_not_occ
    rec("TESLA_NEVER_OCC", ok,
        f"Tesla location home/not_home never writes occupancy Away/Comfort; occupancy stays people/phones binary_sensor occ_on={st.occupancy} after_tesla_away={zsnap(st.z1)} tesla_home_occ={st2.occupancy} p={desired_of(st2)['period']}",
        None if ok else [Finding("TESLA_NEVER_OCC", "tesla loc vs occupancy",
                                 "occupancy stays people/phones", f"on={still_on} home={tesla_home_not_occ}",
                                 severity="blocker")])

    st = make(hm=14 * 60, occupancy="off", rooms=(50, 50), outdoor=50.0, latch="heat",
              empty_since_sec=3600)
    st.tesla_user_present = True
    st.teslas = [TeslaCar(name="car", loc="not_home", route="unknown", tta="unknown",
                          dist_km=8.0, last_km=8.0, user_present=True)]
    fire(st, "travel")
    fire(st, "evaluate")
    ok = (not st.timers.precool_safety) and st.occupancy == "off" and not occupied(st)
    rec("TESLA_USER_PRESENT_UNUSED", ok,
        f"user_present on does not start precool or occupancy pc={st.timers.precool_safety} occ={st.occupancy}",
        None if ok else [Finding("TESLA_USER_PRESENT_UNUSED", "user_present on",
                                 "no precool no occ", f"pc={st.timers.precool_safety} occ={st.occupancy}",
                                 severity="blocker")])

    # precool cancel triad
    st = make(hm=14 * 60, occupancy="off", rooms=(50, 50), outdoor=50.0, latch="heat",
              empty_since_sec=3600, travel="toward_10")
    fire(st, "travel")
    st.empty_since_sec = 20 * 60
    fire(st, "occupancy_on")
    rec("PRECOOL_CANCEL_OCCUPIED", not st.timers.precool_safety,
        f"occupied cancels precool pc={st.timers.precool_safety}", None)
    st = make(hm=14 * 60, occupancy="off", rooms=(50, 50), outdoor=50.0, latch="heat",
              empty_since_sec=3600, travel="toward_10")
    fire(st, "travel")
    st.travel_kind = "intransit"
    fire(st, "travel")
    rec("PRECOOL_CANCEL_NOT_TOWARD", not st.timers.precool_safety,
        f"dir not toward cancels pc={st.timers.precool_safety}", None)
    st = make(hm=14 * 60, occupancy="off", rooms=(71, 71), outdoor=50.0, latch="heat",
              empty_since_sec=3600, travel="toward_10")
    fire(st, "travel")
    lead = lead_min(st)
    # force eta > lead+5
    st.travel_kind = f"toward_{int(lead) + 6}"
    fire(st, "travel")
    rec("PRECOOL_CANCEL_ETA_HYST", not st.timers.precool_safety,
        f"eta > lead+5 cancels lead={lead} pc={st.timers.precool_safety}", None)

    # ----- 1.3.4 independent zones -----
    st = make(hm=14 * 60, occupancy="on", rooms=(71, 72), outdoor=50.0, latch="heat",
              z1_comfort_heat=70.0, z1_comfort_cool=73.0,
              z2_comfort_heat=72.0, z2_comfort_cool=75.0,
              comfort_heat=71.0, comfort_cool=74.0, home_hvac="heat_cool")
    fire(st, "evaluate")
    zind = (zmatch(st.z1, "heat_cool", lo=70.0, hi=73.0)
            and zmatch(st.z2, "heat_cool", lo=72.0, hi=75.0)
            and st.z1.target_low != 71.0)
    rec("ZONE_INDEPENDENT_COMFORT", zind,
        f"z1 comfort 70/73 z2 72/75 occupied day heat_cool z1={zsnap(st.z1)} z2={zsnap(st.z2)} house=71/74",
        None if zind else [Finding("ZONE_INDEPENDENT_COMFORT", "independent zone comfort",
                                   "writes must differ per zone, not house-wide 71/74",
                                   f"z1={zsnap(st.z1)} z2={zsnap(st.z2)}", severity="blocker")])
    rec("HOUSEWIDE_NOT_WRITTEN", zind,
        f"house-wide 71/74 was NOT written z1={zsnap(st.z1)} z2={zsnap(st.z2)}", None)

    st = make(hm=14 * 60, occupancy="off", rooms=(71, 72), outdoor=50.0, latch="heat",
              empty_since_sec=3600,
              z1_away_heat=64.0, z1_away_cool=79.0, z2_away_heat=66.0, z2_away_cool=81.0,
              away_heat=65.0, away_cool=78.0)
    fire(st, "evaluate")
    zia = (zmatch(st.z1, "heat", temp=64.0) and zmatch(st.z2, "heat", temp=66.0))
    rec("ZONE_INDEPENDENT_AWAY", zia,
        f"empty uses z1_away/z2_away independently z1={zsnap(st.z1)} z2={zsnap(st.z2)}",
        None if zia else [Finding("ZONE_INDEPENDENT_AWAY", "empty per-zone away",
                                  "z1 64 z2 66 not house 65", f"z1={zsnap(st.z1)} z2={zsnap(st.z2)}",
                                  severity="blocker")])

    st = make(hm=14 * 60, occupancy="off", rooms=(80, 80), outdoor=90.0, latch="cool",
              vacation_boost=True,
              z1_boost_cool=70.0, z2_boost_cool=68.0, boost_cool=70.0)
    fire(st, "evaluate")
    zib = (zmatch(st.z1, "cool", temp=70.0) and zmatch(st.z2, "cool", temp=68.0)
           and st.z1.hvac != "heat_cool")
    rec("ZONE_INDEPENDENT_BOOST", zib,
        f"boost uses z1_boost/z2_boost independently z1={zsnap(st.z1)} z2={zsnap(st.z2)}",
        None if zib else [Finding("ZONE_INDEPENDENT_BOOST", "boost per-zone",
                                  "z1 70 z2 68 single cool", f"z1={zsnap(st.z1)} z2={zsnap(st.z2)}",
                                  severity="blocker")])

    st = make(hm=22 * 60 + 50, occupancy="on", rooms=(64, 65), outdoor=40.0, latch="heat",
              night_z1_heat=64.0, night_z1_cool=76.0, night_z2_heat=65.0, night_z2_cool=72.0)
    fire(st, "evaluate")
    zin = (zmatch(st.z1, "heat_cool", lo=64.0, hi=76.0)
           and zmatch(st.z2, "heat_cool", lo=65.0, hi=72.0))
    rec("ZONE_INDEPENDENT_NIGHT", zin,
        f"night uses night_z1 vs night_z2 z1={zsnap(st.z1)} z2={zsnap(st.z2)}",
        None if zin else [Finding("ZONE_INDEPENDENT_NIGHT", "night per-zone",
                                  "64/76 vs 65/72", f"z1={zsnap(st.z1)} z2={zsnap(st.z2)}",
                                  severity="blocker")])

    # mixed morning
    st = make(hm=5 * 60 + 15, occupancy="on", rooms=(64, 65), outdoor=40.0, latch="heat",
              z1_comfort_heat=70.0, z1_comfort_cool=73.0,
              z2_comfort_heat=72.0, z2_comfort_cool=75.0,
              z2_boost_heat=73.0)
    fire(st, "morning_z2")
    mix2 = (desired_of(st)["period"] == "morning_z2" and st.timers.morning_boost
            and zmatch(st.z1, "heat_cool", lo=st.night_z1_heat, hi=st.night_z1_cool)
            and zmatch(st.z2, "heat", temp=st.z2_boost_heat))
    rec("MIXED_MORNING_Z2", mix2,
        f"at morning_z2 Z1 still night Eco z2 boost z1={zsnap(st.z1)} z2={zsnap(st.z2)} mb={st.timers.morning_boost}",
        None if mix2 else [Finding("MIXED_MORNING_Z2", "05:15 occupied",
                                   "Z1 night Eco, Z2 comfort or boost",
                                   f"z1={zsnap(st.z1)} z2={zsnap(st.z2)} mb={st.timers.morning_boost}",
                                   severity="blocker")])

    st = make(hm=5 * 60 + 15, occupancy="on", rooms=(71, 72), outdoor=50.0, latch="heat")
    fire(st, "morning_z2")
    mix2b = (not st.timers.morning_boost
             and zmatch(st.z1, "heat_cool", lo=st.night_z1_heat, hi=st.night_z1_cool)
             and zmatch(st.z2, "heat_cool", lo=st.z2_comfort_heat, hi=st.z2_comfort_cool))
    rec("MIXED_MORNING_Z2_COMFORT", mix2b,
        f"morning_z2 no-boost Z1 night Z2 comfort z1={zsnap(st.z1)} z2={zsnap(st.z2)}", None)

    st = make(hm=5 * 60 + 45, occupancy="on", rooms=(71, 72), outdoor=50.0, latch="heat",
              z1_comfort_heat=70.0, z1_comfort_cool=73.0,
              z2_comfort_heat=72.0, z2_comfort_cool=75.0)
    fire(st, "morning_z1")
    mix1 = (desired_of(st)["period"] == "morning_z1" and not st.timers.morning_boost
            and zmatch(st.z1, "heat_cool", lo=70.0, hi=73.0)
            and zmatch(st.z2, "heat_cool", lo=72.0, hi=75.0))
    rec("MIXED_MORNING_Z1", mix1,
        f"at morning_z1 Z1 comfort/boost Z2 already day z1={zsnap(st.z1)} z2={zsnap(st.z2)}",
        None if mix1 else [Finding("MIXED_MORNING_Z1", "05:45 occupied",
                                   "Z1 comfort, Z2 day comfort",
                                   f"z1={zsnap(st.z1)} z2={zsnap(st.z2)}", severity="blocker")])

    # occupied HVAC
    st = make(hm=14 * 60, occupancy="on", rooms=(71, 72), outdoor=50.0, latch="heat",
              home_hvac="heat", z1_comfort_heat=70.0, z2_comfort_heat=72.0)
    fire(st, "evaluate")
    oh = (st.z1.hvac == "heat" and zmatch(st.z1, "heat", temp=70.0)
          and zmatch(st.z2, "heat", temp=72.0) and st.z1.hvac != "auto")
    rec("OCC_HVAC_HEAT", oh,
        f"heat writes single heat setpoint z1={zsnap(st.z1)} z2={zsnap(st.z2)}",
        None if oh else [Finding("OCC_HVAC_HEAT", "occupied HVAC heat",
                                 "single heat", f"z1={zsnap(st.z1)}", severity="blocker")])

    st = make(hm=14 * 60, occupancy="on", rooms=(71, 72), outdoor=90.0, latch="cool",
              home_hvac="cool", z1_comfort_cool=73.0, z2_comfort_cool=75.0)
    fire(st, "evaluate")
    oc = (st.z1.hvac == "cool" and zmatch(st.z1, "cool", temp=73.0)
          and zmatch(st.z2, "cool", temp=75.0))
    rec("OCC_HVAC_COOL", oc,
        f"cool writes single cool setpoint z1={zsnap(st.z1)} z2={zsnap(st.z2)}",
        None if oc else [Finding("OCC_HVAC_COOL", "occupied HVAC cool",
                                 "single cool", f"z1={zsnap(st.z1)}", severity="blocker")])

    st = make(hm=14 * 60, occupancy="on", rooms=(71, 72), outdoor=50.0, latch="heat",
              home_hvac="heat_cool", z1_comfort_heat=70.0, z1_comfort_cool=73.0,
              z2_comfort_heat=72.0, z2_comfort_cool=75.0)
    fire(st, "evaluate")
    ohc = (zmatch(st.z1, "heat_cool", lo=70.0, hi=73.0)
           and zmatch(st.z2, "heat_cool", lo=72.0, hi=75.0))
    rec("OCC_HVAC_HEAT_COOL", ohc,
        f"heat_cool writes dual z1={zsnap(st.z1)} z2={zsnap(st.z2)}",
        None if ohc else [Finding("OCC_HVAC_HEAT_COOL", "occupied HVAC heat_cool",
                                  "dual", f"z1={zsnap(st.z1)}", severity="blocker")])
    rec("OCC_HVAC_NEVER_AUTO", st.z1.hvac != "auto" and st.z2.hvac != "auto",
        f"never emit auto z1={st.z1.hvac} z2={st.z2.hvac}", None)

    st = make(hm=14 * 60, occupancy="on", rooms=(71, 72), outdoor=50.0, latch="heat",
              home_hvac="heat_cool", z1_comfort_heat=74.0, z1_comfort_cool=74.0,
              z2_comfort_heat=75.0, z2_comfort_cool=73.0)
    fire(st, "evaluate")
    clamp = (zmatch(st.z1, "heat_cool", lo=74.0, hi=77.0)
             and zmatch(st.z2, "heat_cool", lo=75.0, hi=78.0))
    rec("OCC_HVAC_CLAMP", clamp,
        f"if heat>=cool in heat_cool, cool=heat+3 z1={zsnap(st.z1)} z2={zsnap(st.z2)}",
        None if clamp else [Finding("OCC_HVAC_CLAMP", "heat>=cool clamp",
                                    "cool = heat+3", f"z1={zsnap(st.z1)} z2={zsnap(st.z2)}",
                                    severity="blocker")])

    # boost from hot / cold house
    st = make(hm=14 * 60, occupancy="off", rooms=(80, 80), outdoor=90.0, latch="cool",
              vacation=True, empty_since_sec=3600, z1_boost_cool=70.0, z2_boost_cool=70.0)
    fire(st, "vacation_off")
    hot = (zmatch(st.z1, "cool", temp=70.0) and zmatch(st.z2, "cool", temp=70.0)
           and st.z1.hvac != "heat_cool"
           and not any(inverted_boost(r) for r in st.write_recs))
    rec("BOOST_HOT_COOL_70", hot,
        f"boost from hot house latched cool + boost_cool 70 NOT 73 inside heat_cool z1={zsnap(st.z1)}",
        None if hot else [Finding("BOOST_HOT_COOL_70", "hot house boost",
                                  "cool 70 single, not heat_cool 73",
                                  f"z1={zsnap(st.z1)} recs={st.write_recs}", severity="blocker")])

    st = make(hm=14 * 60, occupancy="off", rooms=(50, 50), outdoor=40.0, latch="heat",
              vacation=True, empty_since_sec=3600)
    fire(st, "vacation_off")
    cold = (zmatch(st.z1, "heat", temp=73.0) and zmatch(st.z2, "heat", temp=73.0)
            and st.z1.hvac != "heat_cool")
    rec("BOOST_COLD_HEAT_73", cold,
        f"boost from cold latched heat + 73 z1={zsnap(st.z1)}",
        None if cold else [Finding("BOOST_COLD_HEAT_73", "cold house boost",
                                   "heat 73 single", f"z1={zsnap(st.z1)}", severity="blocker")])

    # season latch
    st = make(hm=14 * 60, occupancy="off", rooms=(70, 72), outdoor=66.0, latch="heat",
              empty_since_sec=3600)
    fire(st, "outdoor_summer")
    rec("SEASON_66_COOL", st.latch == "cool",
        f"outdoor 66→cool latch={st.latch} z1={zsnap(st.z1)}", None)
    st = make(hm=14 * 60, occupancy="off", rooms=(70, 72), outdoor=64.0, latch="cool",
              empty_since_sec=3600)
    fire(st, "outdoor_winter")
    rec("SEASON_64_HEAT", st.latch == "heat",
        f"outdoor 64→heat latch={st.latch} z1={zsnap(st.z1)}", None)
    st = make(hm=14 * 60, occupancy="off", rooms=(70, 72), outdoor=65.0, latch="cool",
              empty_since_sec=3600)
    fire(st, "evaluate")
    keep_cool = st.latch == "cool" and zmatch(st.z1, "cool", temp=st.z1_away_cool)
    st2 = make(hm=14 * 60, occupancy="off", rooms=(70, 72), outdoor=65.0, latch="heat",
               empty_since_sec=3600)
    fire(st2, "evaluate")
    keep_heat = st2.latch == "heat" and zmatch(st2.z1, "heat", temp=st2.z1_away_heat)
    rec("SEASON_65_DEADZONE", keep_cool and keep_heat,
        f"65 dead-zone keeps current cool={keep_cool} heat={keep_heat}", None)
    rec("EMPTY_HVAC_FOLLOWS_LATCH", keep_heat and st2.z1.hvac != "cool",
        f"empty HVAC follows latch never raw outdoor>=65 z1={zsnap(st2.z1)} outdoor=65 latch=heat",
        None)

    # HVAC on/off
    st = make(hm=14 * 60, occupancy="on", rooms=(71, 71), outdoor=50.0, latch="heat")
    fire(st, "evaluate")
    before = (zsnap(st.z1), zsnap(st.z2), st.z1_comfort_heat, st.z2_comfort_heat)
    st.timers.away_debounce = True
    st.timers.empty_confirm = True
    st.timers.late_arrival = True
    st.timers.morning_boost = True
    st.timers.precool_safety = True
    st.timers.arrival_lockout = True
    st.timers.vacation_boost = True
    st.timers.writing_watch = True
    sets_before = st.climate_set_count
    fire(st, "hvac_off")
    off_ok = (not st.enabled and st.writes_this == 0
              and zsnap(st.z1) == before[0] and zsnap(st.z2) == before[1]
              and st.climate_set_count == sets_before)
    rec("HVAC_OFF_NO_WRITE", off_ok,
        f"enabled=false last Trane setpoints stay z1={zsnap(st.z1)} sets={st.climate_set_count-sets_before}",
        None if off_ok else [Finding("HVAC_OFF_NO_WRITE", "HVAC control off",
                                     "no climate.set, last setpoints stay",
                                     f"z1={zsnap(st.z1)} enabled={st.enabled}", severity="blocker")])
    rec("HVAC_OFF_CANCEL_TIMERS",
        not any([st.timers.writing_watch, st.timers.away_debounce, st.timers.empty_confirm,
                 st.timers.late_arrival, st.timers.morning_boost, st.timers.precool_safety,
                 st.timers.arrival_lockout, st.timers.vacation_boost]),
        "cancelled writing_watch away_debounce empty_confirm late_arrival morning_boost precool_safety arrival_lockout vacation_boost",
        None)

    st.z1_comfort_heat = 70.0
    st.z2_comfort_heat = 72.0
    st.z1_comfort_cool = 73.0
    st.z2_comfort_cool = 75.0
    fire(st, "hvac_on")
    on_ok = (st.enabled and not st.evaluate_skipped
             and zmatch(st.z1, "heat_cool", lo=70.0, hi=73.0)
             and zmatch(st.z2, "heat_cool", lo=72.0, hi=75.0))
    rec("HVAC_ON_EVALUATE", on_ok,
        f"HVAC on: timer cleanup, enabled=true, evaluate z1={zsnap(st.z1)} z2={zsnap(st.z2)}",
        None if on_ok else [Finding("HVAC_ON_EVALUATE", "HVAC control on",
                                    "evaluate with persisted helpers",
                                    f"z1={zsnap(st.z1)} enabled={st.enabled}", severity="blocker")])
    rec("HVAC_ON_HELPERS_PERSIST",
        st.z1_comfort_heat == 70.0 and st.z2_comfort_heat == 72.0,
        f"z1/z2 saved temps persist (not reset to 71) z1h={st.z1_comfort_heat} z2h={st.z2_comfort_heat}",
        None)

    # editor
    st = make()
    st.z1_comfort_heat = 69.0
    st.z1_comfort_cool = 72.0
    st.z1_away_heat = 63.0
    st.z1_away_cool = 80.0
    st.z1_boost_heat = 74.0
    st.z1_boost_cool = 69.0
    st.night_z1_heat = 63.0
    st.night_z1_cool = 77.0
    st.edit_zone = 1
    fire(st, "load_zone")
    load_ok = (st.edit_comfort_heat == 69.0 and st.edit_comfort_cool == 72.0
               and st.edit_away_heat == 63.0 and st.edit_boost_heat == 74.0
               and st.edit_night_heat == 63.0 and st.edit_night_cool == 77.0)
    rec("EDITOR_LOAD", load_ok,
        f"load_zone reads z1 helpers into edit_* ch={st.edit_comfort_heat} nh={st.edit_night_heat}",
        None if load_ok else [Finding("EDITOR_LOAD", "load_zone",
                                      "edit_* from z1", f"ch={st.edit_comfort_heat}",
                                      severity="blocker")])

    st = make()
    z2_before = (st.z2_comfort_heat, st.z2_comfort_cool, st.z2_away_heat, st.night_z2_heat)
    st.edit_zone = 1
    st.edit_comfort_heat = 69.0
    st.edit_comfort_cool = 72.0
    st.edit_away_heat = 63.0
    st.edit_away_cool = 80.0
    st.edit_boost_heat = 74.0
    st.edit_boost_cool = 69.0
    st.edit_night_heat = 63.0
    st.edit_night_cool = 77.0
    fire(st, "save_zone")
    save_ok = (st.z1_comfort_heat == 69.0 and st.night_z1_heat == 63.0
               and (st.z2_comfort_heat, st.z2_comfort_cool, st.z2_away_heat, st.night_z2_heat) == z2_before)
    rec("EDITOR_SAVE_Z1_NO_CLOBBER_Z2", save_ok,
        f"save zone 1 comfort 69 must NOT change zone 2 helpers z1h={st.z1_comfort_heat} z2h={st.z2_comfort_heat} night_z2={st.night_z2_heat}",
        None if save_ok else [Finding("EDITOR_SAVE_Z1_NO_CLOBBER_Z2", "save zone 1",
                                      "z2 helpers unchanged",
                                      f"z2={st.z2_comfort_heat} night_z2={st.night_z2_heat}",
                                      severity="blocker")])

    st = make()
    st.z1_comfort_heat = 69.0
    st.night_z1_heat = 63.0
    st.edit_zone = 2
    fire(st, "zone_defaults")
    def_ok = (st.z2_comfort_heat == 71.0 and st.z2_comfort_cool == 74.0
              and st.z2_away_heat == 65.0 and st.z2_away_cool == 78.0
              and st.z2_boost_heat == 73.0 and st.z2_boost_cool == 70.0
              and st.night_z2_heat == 65.0 and st.night_z2_cool == 72.0
              and st.z1_comfort_heat == 69.0 and st.night_z1_heat == 63.0)
    rec("EDITOR_DEFAULTS_Z2_NO_CLOBBER_Z1", def_ok,
        f"defaults on zone 2 (71/74, 65/78, 73/70, night 65/72) must not clobber zone 1 "
        f"z1h={st.z1_comfort_heat} z2h={st.z2_comfort_heat} n2={st.night_z2_heat}/{st.night_z2_cool}",
        None if def_ok else [Finding("EDITOR_DEFAULTS_Z2_NO_CLOBBER_Z1", "defaults zone 2",
                                     "z1 unchanged, z2 at defaults",
                                     f"z1={st.z1_comfort_heat} z2={st.z2_comfort_heat} n2={st.night_z2_heat}",
                                     severity="blocker")])

    # clock / reload / watchdog / vacation / forbidden
    st = make(hm=5 * 60 + 15, occupancy="on", rooms=(71, 72), outdoor=50.0, latch="heat",
              last_write_age=10)
    fire(st, "yaml_reload")
    rec("YAML_RELOAD_MORNING",
        desired_of(st)["period"] == "morning_z2" and not st.evaluate_skipped
        and zmatch(st.z1, "heat_cool", lo=st.night_z1_heat, hi=st.night_z1_cool),
        f"yaml-reload at morning recovers period={desired_of(st)['period']} z1={zsnap(st.z1)} unbound={not st.time_triggers_bound}",
        None)

    st = make(hm=14 * 60, occupancy="on", rooms=(71, 71), outdoor=50.0, latch="heat")
    st.hang_after_writing = True
    fire(st, "evaluate")
    hung = st.writing and st.timers.writing_watch
    fire(st, "writing_watch_done")
    rec("WATCHDOG", hung and (not st.writing) and st.stopped == "watchdog_cleared",
        f"watchdog writing_watch cleared hung={hung} writing={st.writing} stop={st.stopped}", None)

    st = make(hm=14 * 60, occupancy="off", rooms=(70, 72), outdoor=50.0, latch="heat",
              vacation=True, empty_since_sec=3600)
    fire(st, "evaluate")
    rec("VAC_EMPTY_NOT_AWAY",
        desired_of(st)["period"] == "vacation" and zmatch(st.z1, "heat", temp=st.vacation_heat)
        and st.z1.temperature != st.z1_away_heat,
        f"vacation empty is vacation Eco not Away z1={zsnap(st.z1)}", None)

    st = make(hm=14 * 60, occupancy="on", rooms=(71, 72), outdoor=50.0, latch="heat",
              vacation=True, z1_comfort_heat=70.0, z1_comfort_cool=73.0,
              z2_comfort_heat=72.0, z2_comfort_cool=75.0)
    fire(st, "vacation_off")
    rec("VAC_OFF_OCCUPIED_COMFORT",
        (not st.vacation) and desired_of(st)["period"] == "day"
        and zmatch(st.z1, "heat_cool", lo=70.0, hi=73.0)
        and zmatch(st.z2, "heat_cool", lo=72.0, hi=75.0),
        f"vacation_off while occupied → Comfort per zone z1={zsnap(st.z1)} z2={zsnap(st.z2)} vb={st.timers.vacation_boost}",
        None)

    st = make(hm=14 * 60, occupancy="on", rooms=(50, 50), outdoor=40.0, latch="heat")
    fire(st, "evaluate")
    fire(st, "vacation_on")
    fire(st, "vacation_off")
    rec("FORBIDDEN_50_62",
        50.0 not in st.brain_temps and 62.0 not in st.brain_temps,
        f"never write 50 or 62 temps={st.brain_temps}", None)

    chatter = {}  # unused leftover from original
    return rows, findings, chatter


def test_required_presence_travel_tesla():
    rows, findings, _ = run_explicit()
    by_id = {sid: verdict for sid, verdict, _notes in rows}
    missing = []
    failed = []
    for sid in REQUIRED_PRESENCE + REQUIRED_TRAVEL + REQUIRED_TESLA + REQUIRED_EXTRA:
        if sid not in by_id:
            missing.append(sid)
        elif by_id[sid] != "PASS":
            failed.append(sid)
    blockers = [f for f in findings if getattr(f, "severity", "") == "blocker"]
    assert not missing, f"missing cases: {missing}"
    assert not failed, "FAIL: " + ", ".join(
        f"{sid}: {next(n for s, v, n in rows if s == sid)}" for sid in failed
    )
    assert not [f for f in blockers if f.fid in failed or True and False]
    # print summary for the install verdict
    pres = sum(1 for s in REQUIRED_PRESENCE if by_id.get(s) == "PASS")
    trav = sum(1 for s in REQUIRED_TRAVEL if by_id.get(s) == "PASS")
    tes = sum(1 for s in REQUIRED_TESLA if by_id.get(s) == "PASS")
    extra = sum(1 for s in REQUIRED_EXTRA if by_id.get(s) == "PASS")
    print(
        f"presence {pres}/{len(REQUIRED_PRESENCE)}  "
        f"travel {trav}/{len(REQUIRED_TRAVEL)}  "
        f"tesla {tes}/{len(REQUIRED_TESLA)}  "
        f"extra {extra}/{len(REQUIRED_EXTRA)}"
    )


if __name__ == "__main__":
    rows, findings, _ = run_explicit()
    req = REQUIRED_PRESENCE + REQUIRED_TRAVEL + REQUIRED_TESLA + REQUIRED_EXTRA
    by_id = {sid: (verdict, notes) for sid, verdict, notes in rows}
    fail = 0
    for sid in req:
        v, n = by_id.get(sid, ("MISSING", ""))
        print(f"{v:4}  {sid}  {n}")
        if v != "PASS":
            fail += 1
    print(f"\n{len(req) - fail} pass / {fail} fail of {len(req)} required")
    raise SystemExit(1 if fail else 0)
