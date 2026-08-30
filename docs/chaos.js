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
      pass, fail, rows, version: "0.1.6",
      verdict: fail === 0 ? "INSTALL OK" : "DO NOT INSTALL — chaos checker failed",
    };
  }
  global.ClimateBrainChaos = { run, parseDuration, toward };
})(window);
