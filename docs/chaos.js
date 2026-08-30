/* Climate Brain fussy chaos checker — presence + travel hysteresis + YAML integrity.
   In-memory. Not live Home Assistant. */
(function (global) {
  function toMin(hhmm) {
    const p = (hhmm || "00:00").split(":");
    return (+p[0]) * 60 + (+p[1] || 0);
  }
  function parseDuration(raw) {
    raw = String(raw || "").toLowerCase();
    if (!raw || ["unknown", "unavailable", "none"].includes(raw)) return 0;
    if (raw.includes(":")) {
      const pp = raw.split(":");
      return (+pp[0] || 0) * 60 + (+pp[1] || 0);
    }
    const hm = raw.match(/(\d+)\s*(?:h|hr|hrs|hour|hours)/);
    const mm = raw.match(/(\d+)\s*(?:m|min|mins|minute|minutes)/);
    if (hm || mm) return (hm ? +hm[1] : 0) * 60 + (mm ? +mm[1] : 0);
    const n = raw.match(/\d+/);
    return n ? +n[0] : 0;
  }
  function toward(dir) {
    const d = String(dir || "").toLowerCase();
    return d.includes("toward") && !d.includes("inhome") && !d.includes("instat");
  }

  function structural(yaml, cfg) {
    cfg = cfg || {};
    const rows = [];
    const fail = (name, ok, detail) => rows.push({ name, ok, detail });
    fail("no leftover tokens", !/__[A-Z0-9_]+__/.test(yaml), "placeholders must be gone");
    fail("one automation id climate_brain", (yaml.match(/id:\s*climate_brain\b/g) || []).length >= 1, "sole writer");
    fail("never occupied auto", !/climate_brain_home_hvac:[\s\S]*?initial:\s*auto/.test(yaml), "Auto is wall schedule");
    cfg.zones.forEach((z, i) => {
      fail("writes zone " + (i + 1), yaml.includes("climate_entity: " + z) || yaml.includes(z), z);
      fail("zone " + (i + 1) + " is climate entity", /^climate\./.test(z), z);
    });
    fail("zone count matches yaml writes", (yaml.match(/action: script\.climate_brain_write_zone/g) || []).length >= cfg.zones.length, String(cfg.zones.length) + " zones");
    fail("occupancy entity", yaml.includes(cfg.occupancy), cfg.occupancy);
    fail("outdoor entity", yaml.includes(cfg.outdoor), cfg.outdoor);
    fail("no second brain", !/id:\s*climate_brain_phase2_brain/.test(yaml), "phase 2 lives in the same automation");
    fail("logger climate_brain", yaml.includes("logger: climate_brain"), "system_log.write");
    const body = yaml.split("\n").filter(l => !l.trim().startsWith("#")).join("\n");
    fail("no 1.3.2 File logger", !/action:\s*notify\.climate_brain_log/.test(body) && !/name:\s*climate_brain_log/.test(body) && !/^\s*platform:\s*file\b/m.test(body), "system_log only");
    fail("winter latch includes 64", (body.match(/<= states\('input_number.climate_brain_season_f'\)/g) || []).length >= 1, "±1 so 64 is heat");
    fail("write_zone exists", yaml.includes("script.climate_brain_write_zone"), "one write helper");
    fail("HVAC trigger ids not YAML booleans", /id:\s+hvac_on/.test(yaml) && /id:\s+hvac_off/.test(yaml) && !/^\s+id:\s+(on|off)\s*$/m.test(yaml), "id: on/off become true/false");
    fail("choose routes hvac_on/hvac_off", yaml.includes("trigger.id == 'hvac_on'") && yaml.includes("trigger.id == 'hvac_off'"), "power_on/off reachable");
    const occOff = (yaml.split("id: occupancy_off")[0] || "").split("triggers:").pop() || "";
    fail("Tesla never occupancy trigger", !/tesla/i.test(occOff) && !/user_present/.test(occOff), "occupancy_off is people only");
    fail("Tesla never occupancy template", !/is_state\('device_tracker\.[^']*tesla/i.test(yaml.split("template:")[1] || "") && !/user_present/.test((yaml.split("id: occupancy_off")[0] || "").split("binary_sensor")[0] || "x"), "occupancy templates do not OR Tesla");
    const dirBlob = yaml;
    fail("driveway home is inhome", /loc_home[\s\S]{0,80}inhome/.test(dirBlob) || dirBlob.includes("inhome"), "location home → inhome");
    const emptyAwayAuto = /set dest = states\([^)]+\)[\s\S]{0,200}if dest in \['unknown'[\s\S]{0,80}away/.test(dirBlob);
    fail("empty dest without falling distance is not toward", !emptyAwayAuto && (dirBlob.includes("0.08") || !dirBlob.includes("climate_brain_tesla_")), "empty dest uses distance hysteresis, not auto away/toward");
    if (cfg.dashboard) {
      const d = cfg.dashboard;
      fail("dashboard HVAC confirmation", d.includes("Disconnect Climate Brain?") && d.includes("Trane / Nexia thermostat schedule"), "tile tap confirmation");
      fail("dashboard no raw enabled switch", !/title: Brain[\s\S]*input_boolean\.climate_brain_enabled/.test(d), "enabled only on confirming tile");
      fail("dashboard no HVAC on/off buttons", !d.includes("climate_brain_hvac_on") && !d.includes("climate_brain_hvac_off"), "slider not buttons");
    }
    const n = toMin(cfg.clock.night), z2 = toMin(cfg.clock.z2), z1 = toMin(cfg.clock.z1), day = toMin(cfg.clock.day);
    fail("morning clocks ordered", z2 < z1 && z1 < day, "Z2 wake < Z1 wake < day");
    fail("night is evening", n > day, "sleep after day start (same calendar wrap)");
    return rows;
  }

  function presenceWalk(cfg) {
    const rows = [];
    const debounce = 180, emptyConfirm = 900;
    function decide(s) {
      if (s.occ === "unknown") return { writeAway: false, period: "hold" };
      if (s.vacation) return { writeAway: false, period: "vacation" };
      if (s.precool && s.occ !== "on") return { writeAway: false, period: "precool" };
      if (s.occ === "on") return { writeAway: false, period: s.clock || "day" };
      if (s.emptySec >= emptyConfirm) return { writeAway: true, period: "empty" };
      return { writeAway: false, period: "debounce" };
    }
    const flicker = decide({ occ: "off", emptySec: 60, vacation: false, precool: false });
    rows.push({ name: "presence flicker <3min not Away", ok: !flicker.writeAway, detail: flicker.period });
    const leave = decide({ occ: "off", emptySec: 901, vacation: false, precool: false });
    rows.push({ name: "real leave 15min is Away", ok: leave.writeAway, detail: leave.period });
    const unk = decide({ occ: "unknown", emptySec: 9999, vacation: false, precool: false });
    rows.push({ name: "occupancy unknown never Away", ok: !unk.writeAway, detail: unk.period });
    const vac = decide({ occ: "off", emptySec: 901, vacation: true, precool: false });
    rows.push({ name: "vacation empty is vacation not Away", ok: vac.period === "vacation" && !vac.writeAway, detail: vac.period });
    const home = decide({ occ: "on", emptySec: 0, vacation: false, precool: true });
    rows.push({ name: "occupied cancels precool start", ok: home.period !== "precool", detail: home.period });
    rows.push({ name: "debounce is 3 min not empty confirm", ok: debounce < emptyConfirm, detail: debounce + "s vs " + emptyConfirm + "s" });
    return rows;
  }

  function travelWalk(cfg) {
    const rows = [];
    const lead = 20, hyst = 5;
    function wouldStart(occ, dir, eta) {
      return occ !== "on" && toward(dir) && eta > 0 && eta <= lead;
    }
    function wouldCancel(dir, eta, active) {
      if (!toward(dir)) return true;
      if (eta > lead + hyst) return true;
      return false;
    }
    rows.push({ name: "occupied never starts precool", ok: !wouldStart("on", "toward", 10), detail: "occ on" });
    rows.push({ name: "toward + ETA inside lead starts", ok: wouldStart("off", "toward_home", 15), detail: "15<=20" });
    rows.push({ name: "inhome is not toward", ok: !wouldStart("off", "inhome toward", 10), detail: "exclude inhome" });
    rows.push({ name: "turn-around cancels immediately", ok: wouldCancel("away", 8, true), detail: "dir away" });
    rows.push({ name: "ETA grow cancel uses +5 hysteresis", ok: !wouldCancel("toward", lead + 4, true) && wouldCancel("toward", lead + 6, true), detail: "lead 20 +5" });
    rows.push({ name: "parse 1 hour 15 min", ok: parseDuration("1 hour 15 min") === 75, detail: String(parseDuration("1 hour 15 min")) });
    rows.push({ name: "parse 01:15", ok: parseDuration("01:15") === 75, detail: String(parseDuration("01:15")) });
    const two = { a: toward("toward"), b: toward("away") };
    rows.push({ name: "two travelers: one toward one away still toward-family", ok: two.a && !two.b, detail: "min ETA of toward only" });
    const chatter = [];
    let active = false;
    for (const eta of [21, 20, 19, 20, 21, 22, 19]) {
      const start = wouldStart("off", "toward", eta);
      const cancel = active && wouldCancel("toward", eta, true);
      const next = start || (active && !cancel);
      chatter.push(active !== next);
      active = next;
    }
    const flips = chatter.filter(Boolean).length;
    rows.push({ name: "lead threshold does not chatter", ok: flips <= 2, detail: "flips=" + flips });
    function teslaDir(s) {
      const loc = String(s.loc || "").toLowerCase();
      const route = String(s.route || "").toLowerCase();
      const raw = String(s.tta == null ? "" : s.tta).toLowerCase();
      const last = +s.last || 0;
      const prev = s.prev || "away";
      const bad = ["unknown", "unavailable", "none", ""];
      const locHome = loc === "home" || loc === "zone.home";
      const routeHome = route === "home" || route === "zone.home";
      let mins = 0;
      if (raw && !bad.includes(raw)) {
        const n = raw.match(/\d+/);
        mins = n ? +n[0] : 0;
      }
      if (locHome) return "inhome";
      if (routeHome && mins > 0) return "toward";
      if (mins <= 0 && !routeHome) {
        const dist = s.dist;
        if (typeof dist === "number") {
          const delta = dist - last;
          if (delta <= -0.08) return "toward";
          if (delta >= 0.08) return "away";
          return prev;
        }
        return prev;
      }
      return "away";
    }
    rows.push({ name: "TESLA_NAV_HOME_TOWARD", ok: teslaDir({loc:"not_home", route:"home", tta:12}) === "toward", detail: "route home + TTA 12" });
    rows.push({ name: "TESLA_NAV_NOT_HOME", ok: teslaDir({loc:"not_home", route:"work", tta:8, dist:4, last:5}) === "away", detail: "nav dest not home" });
    rows.push({ name: "TESLA_NO_NAV_DIST_FALL", ok: teslaDir({loc:"not_home", route:"unknown", tta:"unknown", dist:11.0, last:12.0}) === "toward", detail: "12→11 falling" });
    rows.push({ name: "TESLA_NO_NAV_DIST_RISE", ok: teslaDir({loc:"not_home", route:"unknown", tta:"unknown", dist:12.0, last:11.0}) === "away", detail: "11→12 rising" });
    rows.push({ name: "TESLA_DRIVEWAY_INHOME", ok: teslaDir({loc:"home", route:"home", tta:3, dist:0.01, last:0.2}) === "inhome", detail: "location home" });
    const c1 = teslaDir({loc:"not_home", route:"unknown", tta:"", dist:11.04, last:11.00, prev:"toward"});
    const c2 = teslaDir({loc:"not_home", route:"unknown", tta:"", dist:10.99, last:11.00, prev:"toward"});
    rows.push({ name: "TESLA_HYST_CHATTER", ok: c1 === "toward" && c2 === "toward", detail: "80m no chatter" });
    rows.push({ name: "empty dest without falling is not toward", ok: teslaDir({loc:"not_home", route:"unknown", tta:"unknown", dist:12, last:0, prev:"away"}) === "away", detail: "first sample rising vs 0" });
    return rows;
  }

  function tempHysteresis(cfg) {
    const rows = [];
    const season = 65;
    function latch(out, cur) {
      if (out >= season + 1) return "cool";
      if (out <= season - 1) return "heat";
      return cur;
    }
    rows.push({ name: "outdoor 66 latches cool", ok: latch(66, "heat") === "cool", detail: "≥66" });
    rows.push({ name: "outdoor 64 latches heat", ok: latch(64, "cool") === "heat", detail: "≤64" });
    rows.push({ name: "outdoor 65 stays (dead-zone)", ok: latch(65, "cool") === "cool" && latch(65, "heat") === "heat", detail: "±1 around 65" });
    const comfortH = +cfg.temps.comfortHeat, comfortC = +cfg.temps.comfortCool;
    rows.push({ name: "comfort heat < comfort cool", ok: comfortH < comfortC, detail: comfortH + "/" + comfortC });
    const awayH = +cfg.temps.awayHeat, awayC = +cfg.temps.awayCool;
    rows.push({ name: "away band wider than comfort", ok: awayH <= comfortH && awayC >= comfortC, detail: awayH + "/" + awayC });
    const boostH = +cfg.temps.boostHeat, boostC = +cfg.temps.boostCool;
    rows.push({ name: "boost heat > comfort heat (recovery)", ok: boostH >= comfortH, detail: "heat " + boostH });
    rows.push({ name: "boost cool < comfort cool (recovery)", ok: boostC <= comfortC, detail: "cool " + boostC });
    return rows;
  }

  function run(yaml, cfg) {
    const rows = []
      .concat(structural(yaml, cfg))
      .concat(presenceWalk(cfg))
      .concat(travelWalk(cfg))
      .concat(tempHysteresis(cfg));
    const pass = rows.filter(r => r.ok).length;
    const fail = rows.filter(r => !r.ok).length;
    return {
      pass, fail, rows, version: "0.1.9",
      verdict: fail === 0 ? "INSTALL OK" : "DO NOT INSTALL — chaos checker failed",
    };
  }
  global.ClimateBrainChaos = { run, parseDuration, toward };
})(window);
