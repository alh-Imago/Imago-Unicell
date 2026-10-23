/* composer3d_v1.js -- the page of the 3D Composer (exploration, VM-only toy grid; see composer3d_v1.py). No libraries: two canvases.
   Plan view = one layer, editable.  3D view = whole stack, rotatable.  Depth slider = current layer; every other layer is faded (strength is a setting). */
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var FACES = ["N", "S", "E", "W", "U", "D"];
  var DELTA = { N: [-1, 0, 0], S: [1, 0, 0], E: [0, 1, 0], W: [0, -1, 0], U: [0, 0, 1], D: [0, 0, -1] };
  var COL = window.C3_COLOURS || {};
  var S = null;                       // last state from the server
  var cur = 0;                        // current layer
  var tool = "select";
  var pal = { kind: "relay", gate: null };
  var sel = null;                     // selected cell name
  var linkFrom = null;                // name of the first cell of a join
  var cam = { yaw: -0.6, pitch: 0.55, zoom: 1, px: 0, py: 0 };
  var spin = false;
  var css = getComputedStyle(document.documentElement);
  function v(name, dflt) { return (css.getPropertyValue(name) || "").trim() || dflt; }
  var C = { bg: v("--bg-input", "#0b100c"), panel: v("--bg-panel", "#161d18"), line: v("--line", "#2a352c"), fg: v("--fg", "#e9ede6"), dim: v("--fg-dim", "#9aab98"), copper: v("--copper", "#c17f45"), gold: v("--gold", "#d9b46a"), ok: v("--ok", "#7fae7a"), warn: v("--warn", "#c1a145"), err: v("--err", "#d0786a") };

  /* ------------------------------------------------------------------ server */
  function api(action, body, quiet) {
    return fetch("/api/" + action, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j.ok) { say(j.error || "refused", "err"); return null; }
        S = j; afterState(); if (!quiet) { if (j.warning) say(j.warning, "err"); else if (j.routed && j.routed.length) say("joined with " + j.routed.length + " relay cell(s)", "ok"); }
        return j;
      }).catch(function (e) { say("server not reachable: " + e, "err"); return null; });
  }
  function say(msg, cls) { var s = $("status"); s.textContent = msg || ""; s.className = cls || ""; }

  /* ------------------------------------------------------------------ helpers on the state */
  function cellAt(r, c, l) { if (!S) return null; for (var i = 0; i < S.cells.length; i++) { var p = S.cells[i].pos; if (p[0] === r && p[1] === c && p[2] === l) return S.cells[i]; } return null; }
  function cellNamed(n) { if (!S) return null; for (var i = 0; i < S.cells.length; i++) if (S.cells[i].name === n) return S.cells[i]; return null; }
  function colourOf(c) { return c.kind === "gate" ? COL[c.gate] : (c.shift ? COL.shift : COL.relay); }
  function labelOf(c) { return c.kind === "gate" ? c.gate : (c.shift ? (c.left ? "«" : "»") + c.shift : "→"); }
  function alphaOf(layer) {
    if (layer === cur) return 1;
    var f = parseFloat($("fade").value);
    return f / (1 + 0.6 * (Math.abs(layer - cur) - 1));
  }
  function hexw(x) { return "0x" + (x >>> 0).toString(16).toUpperCase().padStart(8, "0"); }
  function rgba(hex, a) { var n = parseInt(hex.slice(1), 16); return "rgba(" + (n >> 16) + "," + ((n >> 8) & 255) + "," + (n & 255) + "," + a + ")"; }
  function shade(hex, f) { var n = parseInt(hex.slice(1), 16), r = n >> 16, g = (n >> 8) & 255, b = n & 255; return "rgb(" + Math.min(255, Math.round(r * f)) + "," + Math.min(255, Math.round(g * f)) + "," + Math.min(255, Math.round(b * f)) + ")"; }
  function simCell(c) { return S && S.sim && S.sim.cells[c.pos.join(",")]; }
  function fired(c) { return S && S.sim && S.sim.fired.some(function (p) { return p[0] === c.pos[0] && p[1] === c.pos[1] && p[2] === c.pos[2]; }); }

  /* ------------------------------------------------------------------ panels */
  function afterState() {
    var z = S.size;
    $("rows").value = z.rows; $("cols").value = z.cols;
    var d = $("depth"); d.max = Math.max(0, z.layers - 1);
    if (cur > z.layers - 1) cur = z.layers - 1; if (cur < 0) cur = 0;
    d.value = cur; setDepthLab();
    if (sel && !cellNamed(sel)) sel = null;
    if (linkFrom && !cellNamed(linkFrom)) linkFrom = null;
    $("undo").disabled = !S.can_undo;
    drawSummary(); drawProblems(); drawCfg(); drawRun(); draw();
  }
  function setDepthLab() {
    var n = S ? S.size.layers : 1;
    var here = S ? S.cells.filter(function (c) { return c.pos[2] === cur; }).length : 0;
    $("depthLab").textContent = "layer " + cur + " of 0–" + (n - 1) + " · " + here + " cell" + (here === 1 ? "" : "s");
    $("capPlan").textContent = "floor plan · layer " + cur + (cur === 0 ? " (bottom)" : cur === n - 1 ? " (top)" : "");
  }
  function setLayer(l) { if (!S) return; cur = Math.max(0, Math.min(S.size.layers - 1, l)); $("depth").value = cur; setDepthLab(); drawCfg(); draw(); }

  function drawSummary() {
    var m = S.summary, b = m.bounding_box;
    $("summary").innerHTML = "<b>" + m.cells + "</b> cells on <b>" + m.layers_used + "</b> of " + S.size.layers + " layers<br>" + m.gates + " gates · " + m.shift_cells + " shift cells · " + m.plain_relays + " plain relays<br>" + m.vertical_links + " vertical joins · most neighbours on one cell: " + m.most_neighbours + (b ? "<br>box " + b[0] + "×" + b[1] + "×" + b[2] : "") + "<br>entries: " + (S.entries.join(", ") || "none") + " · exits: " + (S.exits.join(", ") || "none");
    $("desc").textContent = S.description || "";
  }
  function drawProblems() {
    var ul = $("problems"); ul.innerHTML = "";
    if (!S.problems.length) { ul.innerHTML = "<li>none</li>"; return; }
    S.problems.forEach(function (p) {
      var li = document.createElement("li"); li.className = p.level; li.textContent = p.msg + "  [layer " + p.pos[2] + "]";
      li.onclick = function () { setLayer(p.pos[2]); var c = cellAt(p.pos[0], p.pos[1], p.pos[2]); if (c) { sel = c.name; drawCfg(); draw(); } };
      ul.appendChild(li);
    });
  }
  function drawCfg() {
    var box = $("cfg"); var c = sel && cellNamed(sel);
    if (!c) { box.textContent = tool === "link" && linkFrom ? "join from " + linkFrom + ": click the target cell" : "tap a cell (Select tool) to edit it"; return; }
    var h = '<div class="row"><label>name</label><input id="cName" value="' + c.name + '"></div>' +
      '<div class="row"><label>position</label><span>row ' + c.pos[0] + ' col ' + c.pos[1] + ' layer ' + c.pos[2] + '</span></div>' +
      '<div class="row"><label>kind</label><select id="cKind"><option>relay</option><option>gate</option></select></div>' +
      '<div class="row"><label>gate</label><select id="cGate"' + (c.kind === "gate" ? "" : " disabled") + '>' + ["AND", "OR", "XOR", "NOR", "NAND", "XNOR"].map(function (g) { return "<option>" + g + "</option>"; }).join("") + '</select></div>' +
      '<div class="row"><label>shift bits</label><input id="cShift" type="number" min="0" max="31" value="' + c.shift + '"' + (c.kind === "gate" ? " disabled" : "") + '></div>' +
      '<div class="row"><label>shift direction</label><select id="cLeft"' + (c.kind === "gate" ? " disabled" : "") + '><option value="1">left «</option><option value="0">right »</option></select></div>' +
      '<div>sends to (a face is on only if a cell is there):</div><div class="faces" id="cFaces">' +
      FACES.map(function (f) { var d = DELTA[f], t = cellAt(c.pos[0] + d[0], c.pos[1] + d[1], c.pos[2] + d[2]); var on = c.down.indexOf(f) >= 0; return '<button data-f="' + f + '" class="' + (on ? "on" : "") + '"' + (t || on ? "" : " disabled") + ' title="' + (t ? "to " + t.name : "no cell here") + '">' + f + (t ? " " + t.name : "") + "</button>"; }).join("") +
      '</div><div>receives from: ' + (c.from.join(", ") || "nothing") + '</div><div class="actions"><button id="cDel">Delete cell</button></div>';
    box.innerHTML = h;
    $("cKind").value = c.kind; if (c.gate) $("cGate").value = c.gate; $("cLeft").value = c.left ? "1" : "0";
    function upd(ch) { api("set", Object.assign({ pos: c.pos }, ch)); }
    $("cName").onchange = function () { var old = sel; var nv = this.value; api("set", { pos: c.pos, name: nv }).then(function (j) { if (j) sel = nv; else sel = old; }); };
    $("cKind").onchange = function () { upd({ kind: this.value }); };
    $("cGate").onchange = function () { upd({ gate: this.value }); };
    $("cShift").onchange = function () { upd({ shift: parseInt(this.value || "0", 10) }); };
    $("cLeft").onchange = function () { upd({ left: this.value === "1" }); };
    $("cDel").onclick = function () { api("delete", { pos: c.pos }); };
    Array.prototype.forEach.call($("cFaces").querySelectorAll("button"), function (b) { b.onclick = function () { api("face", { pos: c.pos, face: b.getAttribute("data-f"), on: !b.classList.contains("on") }); }; });
  }
  function drawRun() {
    var box = $("run"), sim = S.sim, h = "";
    if (!sim) {
      h += "give each entry cell a word (decimal or 0x hex):";
      S.entries.forEach(function (n) { h += '<div class="in"><span>' + n + '</span><input type="text" data-in="' + n + '" value="' + (runVals[n] || "") + '" placeholder="0"></div>'; });
      if (!S.entries.length) h += "<div>(no entry cells yet: an entry is a cell that sends but receives nothing)</div>";
      h += '<div class="in"><span>watch</span><select id="rWatch"><option value="">none</option>' + S.cells.map(function (c) { return "<option" + (c.name === runWatch ? " selected" : "") + ">" + c.name + "</option>"; }).join("") + "</select></div>";
      h += '<div class="actions"><button id="rStart" class="primary">Start</button>' + (S.meta && S.meta.expect ? '<button id="rCheck" title="run 100 adder vectors against real addition">Check adder</button>' : "") + "</div>";
      if (S.check) h += "<div>" + (S.check.ok ? "<b>adder check passed</b>: " + S.check.checked + " vectors, settled at tick " + S.check.ticks.join("/") : "<b>FAILED</b> at a=" + hexw(S.check.failed.a) + " b=" + hexw(S.check.failed.b) + " got " + (S.check.failed.got === null ? "nothing" : hexw(S.check.failed.got))) + "</div>";
    } else {
      h += "tick <b>" + sim.tick + "</b> · " + (sim.settled ? "settled" : sim.cells ? Object.keys(sim.cells).length + " cells hold words" : "") + "<br>fired this tick: " + sim.fired.length + " · words moving: " + sim.moves.length;
      if (sim.watch) h += "<br>watch " + sim.watch.name + ": " + (sim.watch.value === null ? "no word yet" : "<b>" + hexw(sim.watch.value) + "</b> (first at tick " + sim.watch.first_tick + ")");
      h += '<div class="actions"><button id="rStep">Step</button><button id="rStep10">+10</button><button id="rRun">Run to end</button><button id="rReset">Stop</button></div>';
    }
    box.innerHTML = h;
    if (!sim) {
      Array.prototype.forEach.call(box.querySelectorAll("input[data-in]"), function (i) { i.oninput = function () { runVals[i.getAttribute("data-in")] = i.value; }; });
      if ($("rWatch")) $("rWatch").onchange = function () { runWatch = this.value; };
      $("rStart").onclick = function () {
        var inputs = {}; S.entries.forEach(function (n) { inputs[n] = runVals[n] === undefined || runVals[n] === "" ? "0" : runVals[n]; });
        api("sim_start", { inputs: inputs, watch: runWatch || null });
      };
      if ($("rCheck")) $("rCheck").onclick = function () { say("checking…"); api("check", {}).then(function (j) { if (j) say(j.check.ok ? "adder check passed" : "adder check FAILED", j.check.ok ? "ok" : "err"); }); };
    } else {
      $("rStep").onclick = function () { api("sim_step", { n: 1 }, true); };
      $("rStep10").onclick = function () { api("sim_step", { n: 10 }, true); };
      $("rRun").onclick = function () { api("sim_run", {}); };
      $("rReset").onclick = function () { api("sim_reset", {}, true); };
    }
  }
  var runVals = {}, runWatch = "";

  /* ------------------------------------------------------------------ canvases */
  function fit(cv) {
    var r = cv.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
    var w = Math.max(10, Math.round(r.width)), h = Math.max(10, Math.round(r.height));
    if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
    var g = cv.getContext("2d"); g.setTransform(dpr, 0, 0, dpr, 0, 0); return { g: g, w: w, h: h };
  }
  function draw() { if (!S) return; drawPlan(); draw3d(); }

  /* ---- plan */
  var pl = { cs: 30, ox: 0, oy: 0 };
  function drawPlan() {
    var cv = $("plan"), f = fit(cv), g = f.g, z = S.size;
    g.fillStyle = C.bg; g.fillRect(0, 0, f.w, f.h);
    pl.cs = Math.max(8, Math.min((f.w - 16) / z.cols, (f.h - 16) / z.rows));
    pl.ox = (f.w - pl.cs * z.cols) / 2; pl.oy = (f.h - pl.cs * z.rows) / 2;
    var cs = pl.cs;
    g.fillStyle = C.panel; g.fillRect(pl.ox, pl.oy, cs * z.cols, cs * z.rows);
    g.strokeStyle = C.line; g.lineWidth = 1; g.beginPath();
    for (var i = 0; i <= z.cols; i++) { g.moveTo(pl.ox + i * cs, pl.oy); g.lineTo(pl.ox + i * cs, pl.oy + z.rows * cs); }
    for (var j = 0; j <= z.rows; j++) { g.moveTo(pl.ox, pl.oy + j * cs); g.lineTo(pl.ox + z.cols * cs, pl.oy + j * cs); }
    g.stroke();
    var ctr = function (c) { return [pl.ox + (c.pos[1] + 0.5) * cs, pl.oy + (c.pos[0] + 0.5) * cs]; };
    // other layers first, faded (layers further from the current one fade more); cells on the current layer drawn after, in full
    var others = S.cells.filter(function (c) { return c.pos[2] !== cur; }).sort(function (a, b) { return Math.abs(b.pos[2] - cur) - Math.abs(a.pos[2] - cur); });
    others.forEach(function (c) {
      var a = alphaOf(c.pos[2]); if (a <= 0) return;
      var p = ctr(c), s = cs * 0.62;
      g.fillStyle = rgba(colourOf(c), a * 0.8); g.strokeStyle = rgba(c.pos[2] > cur ? C.gold : C.dim, a); g.lineWidth = 1;
      g.beginPath(); g.rect(p[0] - s / 2, p[1] - s / 2, s, s); g.fill(); g.stroke();
      if (cs >= 22) { g.fillStyle = rgba(C.fg, a); g.font = Math.round(cs * 0.28) + "px monospace"; g.textAlign = "center"; g.textBaseline = "middle"; g.fillText(c.pos[2] > cur ? "▲" + c.pos[2] : "▼" + c.pos[2], p[0], p[1]); }
    });
    var here = S.cells.filter(function (c) { return c.pos[2] === cur; });
    // links on this layer
    S.links.forEach(function (l) {
      if (l.src[2] !== cur) return;
      var s = ctr({ pos: l.src }), d = DELTA[l.face];
      if (d[2] === 0) {
        var e = [s[0] + d[1] * cs, s[1] + d[0] * cs];
        arrow(g, s[0] + d[1] * cs * 0.3, s[1] + d[0] * cs * 0.3, e[0] - d[1] * cs * 0.28, e[1] - d[0] * cs * 0.28, l.dst ? C.fg : C.warn, Math.max(1.5, cs * 0.07), cs * 0.16);
      }
    });
    here.forEach(function (c) {
      var p = ctr(c), s = cs * 0.74, sc = simCell(c), fi = fired(c);
      g.fillStyle = colourOf(c); g.strokeStyle = fi ? C.copper : sc ? C.ok : C.fg; g.lineWidth = fi ? 3 : sc ? 2 : 1;
      roundRect(g, p[0] - s / 2, p[1] - s / 2, s, s, cs * 0.12); g.fill(); g.stroke();
      if (sel === c.name || linkFrom === c.name) { g.strokeStyle = linkFrom === c.name ? C.gold : C.copper; g.lineWidth = 3; roundRect(g, p[0] - s / 2 - 3, p[1] - s / 2 - 3, s + 6, s + 6, cs * 0.16); g.stroke(); }
      if (cs >= 20) {
        g.fillStyle = "#0b100c"; g.textAlign = "center"; g.textBaseline = "middle"; g.font = "600 " + Math.round(cs * 0.27) + "px monospace";
        g.fillText(labelOf(c), p[0], p[1] - (cs >= 34 ? cs * 0.08 : 0));
        if (cs >= 34) { g.font = Math.round(cs * 0.2) + "px monospace"; g.fillText(c.name.slice(0, 6), p[0], p[1] + cs * 0.17); }
      }
      if (sc && sc.out !== null && cs >= 44) { g.fillStyle = C.ok; g.font = Math.round(cs * 0.18) + "px monospace"; g.fillText((sc.out >>> 0).toString(16), p[0], p[1] + s / 2 + cs * 0.1); }
      // vertical joins: filled gold triangle = this cell sends up/down; hollow = it receives from there
      var x = p[0] + s / 2 - cs * 0.07, y1 = p[1] - s / 2 + cs * 0.1, y2 = p[1] + s / 2 - cs * 0.1, t = cs * 0.13;
      if (c.down.indexOf("U") >= 0) tri(g, x, y1, t, true, true);
      if (c.down.indexOf("D") >= 0) tri(g, x, y2, t, false, true);
      S.links.forEach(function (l) {
        if (!l.dst || l.dst[0] !== c.pos[0] || l.dst[1] !== c.pos[1] || l.dst[2] !== cur || l.src[2] === cur) return;
        if (l.face === "U") tri(g, p[0] - s / 2 + cs * 0.1, y2, t, false, false);   // arrives from below
        if (l.face === "D") tri(g, p[0] - s / 2 + cs * 0.1, y1, t, true, false);    // arrives from above
      });
    });
    // pending join marker
    g.fillStyle = C.dim; g.font = "11px monospace"; g.textAlign = "left"; g.textBaseline = "top";
    g.fillText(tool === "place" ? "click an empty square to place " + (pal.kind === "gate" ? pal.gate : "relay") : tool === "link" ? (linkFrom ? "join " + linkFrom + " → click target" : "click the source cell") : tool === "delete" ? "click a cell to delete" : "", 8, f.h - 18);
  }
  function roundRect(g, x, y, w, h, r) { g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r); g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath(); }
  function tri(g, x, y, t, up, filled) {
    g.beginPath(); if (up) { g.moveTo(x, y - t); g.lineTo(x + t, y + t); g.lineTo(x - t, y + t); } else { g.moveTo(x, y + t); g.lineTo(x + t, y - t); g.lineTo(x - t, y - t); }
    g.closePath(); g.lineWidth = 1.5; g.strokeStyle = C.gold; if (filled) { g.fillStyle = C.gold; g.fill(); } g.stroke();
  }
  function arrow(g, x1, y1, x2, y2, col, w, head) {
    g.strokeStyle = col; g.fillStyle = col; g.lineWidth = w; g.beginPath(); g.moveTo(x1, y1); g.lineTo(x2, y2); g.stroke();
    var a = Math.atan2(y2 - y1, x2 - x1); g.beginPath(); g.moveTo(x2 + Math.cos(a) * head * 0.6, y2 + Math.sin(a) * head * 0.6);
    g.lineTo(x2 - Math.cos(a - 0.5) * head * 0.6, y2 - Math.sin(a - 0.5) * head * 0.6); g.lineTo(x2 - Math.cos(a + 0.5) * head * 0.6, y2 - Math.sin(a + 0.5) * head * 0.6); g.closePath(); g.fill();
  }
  function planHit(ev) {
    var r = $("plan").getBoundingClientRect(), x = ev.clientX - r.left - pl.ox, y = ev.clientY - r.top - pl.oy;
    var col = Math.floor(x / pl.cs), row = Math.floor(y / pl.cs);
    if (!S || row < 0 || col < 0 || row >= S.size.rows || col >= S.size.cols) return null;
    return [row, col, cur];
  }

  /* ---- 3D */
  var P3 = [];   // projected cell centres of the last frame, for picking
  function proj(o, x, y, z) {
    var cy = Math.cos(cam.yaw), sy = Math.sin(cam.yaw), cp = Math.cos(cam.pitch), sp = Math.sin(cam.pitch);
    var x1 = x * cy + z * sy, z1 = -x * sy + z * cy, y2 = y * cp - z1 * sp, z2 = y * sp + z1 * cp;
    var s = o.D / (o.D + z2);
    return { x: o.cx + cam.px + x1 * s * o.k, y: o.cy + cam.py - y2 * s * o.k, z: z2, s: s };
  }
  function draw3d() {
    var cv = $("d3"), f = fit(cv), g = f.g, z = S.size, gap = parseFloat($("gap").value);
    g.fillStyle = C.bg; g.fillRect(0, 0, f.w, f.h);
    if ($("layout").value === "plan-only") return;
    var radius = 0.5 * Math.sqrt(z.cols * z.cols + z.rows * z.rows + Math.pow(z.layers * gap, 2));
    var o = { cx: f.w / 2, cy: f.h / 2, D: radius * 3.2, k: Math.min(f.w, f.h) * 0.5 / radius * 1.15 * cam.zoom };
    var X = function (c) { return c - (z.cols - 1) / 2; }, Z = function (r) { return r - (z.rows - 1) / 2; }, Y = function (l) { return (l - (z.layers - 1) / 2) * gap; };
    var items = [];
    // layer sheets
    for (var l = 0; l < z.layers; l++) {
      var a = l === cur ? 1 : alphaOf(l);
      var cs4 = [[-0.5, -0.5], [z.cols - 0.5, -0.5], [z.cols - 0.5, z.rows - 0.5], [-0.5, z.rows - 0.5]].map(function (q) { return proj(o, X(q[0]), Y(l), Z(q[1])); });
      items.push({ z: (cs4[0].z + cs4[1].z + cs4[2].z + cs4[3].z) / 4 + 1000, sheet: cs4, layer: l, a: a });
    }
    // cells
    P3 = [];
    var proxy = {};
    S.cells.forEach(function (c) {
      var a = alphaOf(c.pos[2]); if (a <= 0 && c.pos[2] !== cur) return;
      var ctr = proj(o, X(c.pos[1]), Y(c.pos[2]), Z(c.pos[0]));
      proxy[c.pos.join(",")] = { c: c, p: ctr, a: a };
      items.push({ z: ctr.z, cell: c, p: ctr, a: a });
      P3.push({ c: c, x: ctr.x, y: ctr.y, z: ctr.z, r: Math.max(5, 0.4 * ctr.s * o.k) });
    });
    S.links.forEach(function (l) {
      if (!l.dst) return;
      var A = proxy[l.src.join(",")], B = proxy[l.dst.join(",")]; if (!A || !B) return;
      var a = Math.min(A.a, B.a); if (a <= 0) return;
      items.push({ z: (A.p.z + B.p.z) / 2 - 0.01, link: [A.p, B.p], a: a, vert: l.src[2] !== l.dst[2], hot: S.sim && S.sim.moves.some(function (m) { return m.src.join() === l.src.join() && m.dst.join() === l.dst.join(); }) });
    });
    items.sort(function (a, b) { return b.z - a.z; });
    items.forEach(function (it) {
      if (it.sheet) {
        var q = it.sheet, on = it.layer === cur;
        g.beginPath(); g.moveTo(q[0].x, q[0].y); for (var i = 1; i < 4; i++) g.lineTo(q[i].x, q[i].y); g.closePath();
        g.fillStyle = on ? rgba(C.copper, 0.10) : rgba(C.dim, 0.025 + 0.03 * it.a); g.fill();
        g.strokeStyle = on ? C.copper : rgba(C.dim, 0.12 + 0.5 * it.a); g.lineWidth = on ? 2 : 1; g.stroke();
        if (on || it.a > 0) { g.fillStyle = on ? C.copper : rgba(C.dim, 0.4 + it.a); g.font = "11px monospace"; g.textAlign = "left"; g.textBaseline = "middle"; g.fillText("L" + it.layer, q[3].x + 4, q[3].y); }
      } else if (it.link) {
        var A = it.link[0], B = it.link[1], col = it.hot ? C.copper : it.vert ? C.gold : C.fg;
        g.globalAlpha = it.a; arrow(g, A.x + (B.x - A.x) * 0.25, A.y + (B.y - A.y) * 0.25, A.x + (B.x - A.x) * 0.72, A.y + (B.y - A.y) * 0.72, col, it.a >= 1 ? 2 : 1.2, 11 * A.s); g.globalAlpha = 1;
      } else {
        cube(g, o, it.cell, it.a, X, Y, Z);
      }
    });
    g.fillStyle = C.dim; g.font = "11px monospace"; g.textAlign = "left"; g.textBaseline = "top";
    g.fillText("drag: rotate · shift/right-drag: pan · wheel: zoom · click a cell: select", 8, f.h - 18);
  }
  var CUBE = [[-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1], [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]];
  var FACES6 = [[0, 1, 2, 3, 1.0], [4, 5, 6, 7, 1.0], [0, 1, 5, 4, 0.82], [2, 3, 7, 6, 0.82], [0, 3, 7, 4, 0.66], [1, 2, 6, 5, 0.66]];
  function cube(g, o, c, a, X, Y, Z) {
    var h = 0.36, cx = X(c.pos[1]), cy = Y(c.pos[2]), cz = Z(c.pos[0]);
    var pts = CUBE.map(function (q) { return proj(o, cx + q[0] * h, cy + q[1] * h, cz + q[2] * h); });
    var base = colourOf(c), fs = FACES6.map(function (F) { var zc = (pts[F[0]].z + pts[F[1]].z + pts[F[2]].z + pts[F[3]].z) / 4; return { F: F, z: zc }; }).sort(function (p, q) { return q.z - p.z; });
    var on = c.pos[2] === cur, hl = sel === c.name || linkFrom === c.name, sc = simCell(c), fi = fired(c);
    fs.forEach(function (e) {
      var F = e.F; g.beginPath(); g.moveTo(pts[F[0]].x, pts[F[0]].y); for (var i = 1; i < 4; i++) g.lineTo(pts[F[i]].x, pts[F[i]].y); g.closePath();
      g.globalAlpha = on ? 1 : Math.min(1, a * 1.2); g.fillStyle = shade(base, F[4] + (F === FACES6[1] ? 0.12 : 0)); g.fill();
      g.strokeStyle = hl ? C.copper : fi ? C.copper : sc ? C.ok : on ? "rgba(233,237,230,.55)" : "rgba(233,237,230,.35)"; g.lineWidth = hl || fi ? 2 : 1; g.stroke();
    });
    g.globalAlpha = 1;
    if (on) {   // label on the current layer only, so the faded ones stay quiet
      var p = proj(o, cx, cy + h, cz); g.fillStyle = "#0b100c"; g.font = "600 " + Math.max(8, Math.round(0.34 * p.s * o.k)) + "px monospace"; g.textAlign = "center"; g.textBaseline = "middle";
      if (0.34 * p.s * o.k >= 7) g.fillText(labelOf(c), p.x, p.y);
    }
  }
  function pick3d(x, y) {
    var best = null;
    P3.forEach(function (q) { var d = Math.hypot(q.x - x, q.y - y); if (d <= q.r && (!best || q.z < best.z)) best = q; });
    return best && best.c;
  }

  /* ------------------------------------------------------------------ interaction */
  function clickCell(c) {
    if (tool === "delete") { if (c) api("delete", { pos: c.pos }); return; }
    if (tool === "link") {
      if (!c) { linkFrom = null; drawCfg(); draw(); return; }
      if (!linkFrom) { linkFrom = c.name; say("join from " + c.name + ": now click the target cell"); drawCfg(); draw(); return; }
      var src = cellNamed(linkFrom); linkFrom = null;
      if (src && src.name !== c.name) api("link", { src: src.pos, dst: c.pos, any_layer: $("anyLayer").checked }); else { drawCfg(); draw(); }
      return;
    }
    sel = c ? c.name : null; if (c) { setLayer(c.pos[2]); } drawCfg(); draw();
  }
  $("plan").addEventListener("click", function (ev) {
    if (!S) return; var p = planHit(ev); if (!p) return;
    var c = cellAt(p[0], p[1], p[2]);
    if (tool === "place") { if (c) { sel = c.name; drawCfg(); draw(); return; } api("place", { pos: p, kind: pal.kind, gate: pal.gate }); return; }
    clickCell(c);
  });
  var drag = null;
  var d3 = $("d3");
  d3.addEventListener("contextmenu", function (e) { e.preventDefault(); });
  d3.addEventListener("pointerdown", function (e) { d3.setPointerCapture(e.pointerId); drag = { x: e.clientX, y: e.clientY, moved: 0, pan: e.shiftKey || e.button === 2 || e.button === 1 }; d3.classList.add("drag"); spin = false; $("spin").classList.remove("on"); });
  d3.addEventListener("pointermove", function (e) {
    if (!drag) return; var dx = e.clientX - drag.x, dy = e.clientY - drag.y; drag.x = e.clientX; drag.y = e.clientY; drag.moved += Math.abs(dx) + Math.abs(dy);
    if (drag.pan) { cam.px += dx; cam.py += dy; } else { cam.yaw += dx * 0.008; cam.pitch = Math.max(-1.5, Math.min(1.5, cam.pitch + dy * 0.008)); }
    draw3d();
  });
  d3.addEventListener("pointerup", function (e) {
    var was = drag; drag = null; d3.classList.remove("drag");
    if (was && was.moved < 5 && !was.pan) { var r = d3.getBoundingClientRect(); var c = pick3d(e.clientX - r.left, e.clientY - r.top); if (tool === "place") { if (c) { sel = c.name; setLayer(c.pos[2]); } } else clickCell(c); }
  });
  d3.addEventListener("wheel", function (e) { e.preventDefault(); cam.zoom = Math.max(0.3, Math.min(6, cam.zoom * (e.deltaY < 0 ? 1.1 : 1 / 1.1))); draw3d(); }, { passive: false });
  Array.prototype.forEach.call(document.querySelectorAll("[data-cam]"), function (b) {
    b.onclick = function () {
      var k = b.getAttribute("data-cam"); cam.px = cam.py = 0; cam.zoom = 1;
      if (k === "iso") { cam.yaw = -0.6; cam.pitch = 0.55; } else if (k === "top") { cam.yaw = 0; cam.pitch = 1.5; } else if (k === "front") { cam.yaw = 0; cam.pitch = 0; } else { cam.yaw = Math.PI / 2; cam.pitch = 0; }
      draw3d();
    };
  });
  $("spin").onclick = function () { spin = !spin; this.classList.toggle("on", spin); };
  setInterval(function () { if (spin && S) { cam.yaw += 0.01; draw3d(); } }, 33);

  // depth
  $("depth").oninput = function () { setLayer(parseInt(this.value, 10)); };
  $("dUp").onclick = function () { setLayer(cur + 1); };
  $("dDown").onclick = function () { setLayer(cur - 1); };
  $("fade").onchange = draw; $("gap").oninput = draw3d;
  $("layout").onchange = function () { $("views").className = "views " + this.value.replace("split", ""); draw(); };

  // tools and palette
  Array.prototype.forEach.call(document.querySelectorAll("[data-tool]"), function (b) {
    b.onclick = function () { tool = b.getAttribute("data-tool"); linkFrom = null; Array.prototype.forEach.call(document.querySelectorAll("[data-tool]"), function (x) { x.classList.toggle("on", x === b); }); $("plan").className = tool; drawCfg(); draw(); };
  });
  (function () {
    var items = [{ label: "Relay", kind: "relay", gate: null, col: COL.relay }].concat(["AND", "OR", "XOR", "NOR", "NAND", "XNOR"].map(function (g) { return { label: g + " gate", kind: "gate", gate: g, col: COL[g] }; }));
    items.forEach(function (it, i) {
      var b = document.createElement("button"); b.textContent = it.label; b.style.setProperty("--sw", it.col); if (i === 0) b.classList.add("on");
      b.onclick = function () { pal = { kind: it.kind, gate: it.gate }; Array.prototype.forEach.call($("palette").children, function (x) { x.classList.toggle("on", x === b); }); document.querySelector('[data-tool="place"]').click(); };
      $("palette").appendChild(b);
    });
  })();

  // file bar
  $("newBtn").onclick = function () { if (S && S.cells.length && !confirm("Start a new empty design? (Undo brings the old one back.)")) return; api("clear", { rows: 10, cols: 10, layers: 4 }); };
  $("example").onchange = function () { var id = this.value; this.value = ""; if (id) { sel = null; api("example", { id: id }).then(function (j) { if (j) { setLayer(0); say("opened example: " + id, "ok"); } }); } };
  $("undo").onclick = function () { api("undo", {}); };
  $("save").onclick = function () {
    api("export", {}, true).then(function (j) {
      if (!j) return; var blob = new Blob([JSON.stringify(j.doc, null, 1)], { type: "application/json" }), a = document.createElement("a");
      a.href = URL.createObjectURL(blob); a.download = "design.3d.json"; document.body.appendChild(a); a.click(); a.remove(); say("saved design.3d.json (an imago-3d-design file, not an ICM file)", "ok");
    });
  };
  $("openBtn").onclick = function () { $("file").click(); };
  $("file").onchange = function () {
    var f = this.files[0]; this.value = ""; if (!f) return; var r = new FileReader();
    r.onload = function () { var doc; try { doc = JSON.parse(r.result); } catch (e) { say("that file is not JSON", "err"); return; } sel = null; api("load", { doc: doc }).then(function (j) { if (j) { setLayer(0); say("opened " + f.name, "ok"); } }); };
    r.readAsText(f);
  };
  $("rows").onchange = function () { api("resize", { rows: parseInt(this.value, 10) }); };
  $("cols").onchange = function () { api("resize", { cols: parseInt(this.value, 10) }); };
  $("layerTop").onclick = function () { api("add_layer", { side: "top" }).then(function (j) { if (j) setLayer(S.size.layers - 1); }); };
  $("layerBot").onclick = function () { api("add_layer", { side: "bottom" }).then(function (j) { if (j) setLayer(0); }); };
  $("rmTop").onclick = function () { api("remove_layer", { side: "top" }); };
  $("rmBot").onclick = function () { api("remove_layer", { side: "bottom" }); };

  document.addEventListener("keydown", function (e) {
    var t = (e.target && e.target.tagName) || ""; if (t === "INPUT" || t === "SELECT" || t === "TEXTAREA") return;
    if (e.key === "[") setLayer(cur - 1); else if (e.key === "]") setLayer(cur + 1);
    else if ((e.ctrlKey || e.metaKey) && e.key === "z") { e.preventDefault(); api("undo", {}); }
    else if ((e.key === "Delete" || e.key === "Backspace") && sel) { var c = cellNamed(sel); if (c) api("delete", { pos: c.pos }); }
    else if (e.key === "Escape") { linkFrom = null; sel = null; drawCfg(); draw(); }
  });
  window.addEventListener("resize", draw);
  if (window.ResizeObserver) new ResizeObserver(function () { draw(); }).observe($("views"));

  // hooks for the tests / the browser check
  window.C3 = { state: function () { return S; }, setLayer: setLayer, cam: cam, layer: function () { return cur; }, api: api };
  api("state", {}, true).then(function () { if (S && S.cells.length) { var layers = S.cells.map(function (c) { return c.pos[2]; }); setLayer(Math.min.apply(null, layers)); } });
})();
