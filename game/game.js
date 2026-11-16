/* Spin Doctor: walk around, pull the levers, publish the headline. Static game; all numbers precomputed
   by d3_modeling/spin_engine.py into data/game_data.json. Phaser draws the world, the HTML panel shows data. */
const W = 800, H = 520;
let G, OUT = {}, CREDITS = {};
const S = { mode: "office", nb: null, goal: null, sel: {} };
const KEYS = ["denominator", "offenses", "year", "geography", "peer", "framing"];
const SHORT = { denominator: "Divide by", offenses: "Crimes", year: "Year", geography: "Area size", peer: "Compare to", framing: "Headline" };
const TIPS = {
  denominator: "Dividing by residents plus jobs makes workplace-heavy areas look calmer. Ask: per what? Do commuters count as the people this score describes?",
  offenses: "Choosing which crimes count can flip a label. Ask: who picked the offense list, and why?",
  year: "A single year can be unusually good or bad. Ask: what do the other years look like?",
  geography: "Blending in neighboring areas dilutes (or concentrates) a hotspot. Ask: where exactly are the borders?",
  peer: "Rankings depend on who you are compared with. Ask: compared with whom?",
  framing: "'Down 20% since its peak' and 'a D grade' can describe the same place. Ask: which baseline, and what is the actual level?"
};
const $ = (id) => document.getElementById(id);
const L = () => G.meta.levers;
const gradeOf = (pc) => (pc < 20 ? "A" : pc < 40 ? "B" : pc < 60 ? "C" : pc < 80 ? "D" : "F");
const clamp = (x) => Math.max(0, Math.min(100, x));

function calc(nb, sel) {
  const i = (((sel.denominator * 4 + sel.offenses) * 5 + sel.year) * 3 + sel.geography) * 4 + sel.peer;
  const d = nb.data, pc = d.pc[i], pk = d.peak[i] * 100, lo = d.low[i] * 100, peer = L()[4].options[sel.peer];
  let perceived, html;
  if (sel.framing === 0) {
    perceived = 100 - pc;
    html = `<span class="grade">${gradeOf(pc)}</span> fewer reported incidents than ${Math.round(100 - pc)}% of ${peer}`;
  } else if (sel.framing === 1) {
    perceived = clamp(50 - pk);
    html = Math.abs(pk) < 0.5 ? "Reported crime is at its peak year" : `Reported crime <span style="color:var(--good)">down ${Math.abs(pk).toFixed(0)}%</span> since its peak year`;
  } else {
    perceived = clamp(50 - lo);
    html = lo < 0.5 ? "Reported crime is at its lowest year" : `Reported crime <span style="color:var(--bad)">up ${lo.toFixed(0)}%</span> since its lowest year`;
  }
  return { perceived, html, pc };
}
const honestSel = () => ({ ...G.meta.honest });
function allCombos(fn) { // iterate every lever combination
  for (let d = 0; d < 4; d++) for (let o = 0; o < 4; o++) for (let y = 0; y < 5; y++) for (let g = 0; g < 3; g++) for (let p = 0; p < 4; p++) for (let f = 0; f < 3; f++) fn({ denominator: d, offenses: o, year: y, geography: g, peer: p, framing: f });
}

function toast(msg) { const t = $("toast"); t.textContent = msg; t.style.opacity = 1; clearTimeout(toast.h); toast.h = setTimeout(() => (t.style.opacity = 0), 1800); }

function updateUI() {
  const nb = S.nb;
  $("caseTitle").textContent = nb ? nb.name : "Walk to a case file and press E";
  $("goal").textContent = S.goal === "safe" ? "Client: a realtor. Make it look SAFE." : S.goal === "danger" ? "Client: a security vendor. Make it look DANGEROUS." : "";
  if (!nb) { $("headline").textContent = ""; $("meterFill").style.left = "50%"; $("meterLabel").innerHTML = ""; $("levers").innerHTML = ""; $("visual").innerHTML = ""; $("credit").textContent = ""; return; }
  const c = calc(nb, S.sel);
  $("headline").innerHTML = c.html;
  $("meterFill").style.left = `calc(${c.perceived}% - 2px)`;
  $("meterLabel").innerHTML = "<span>looks dangerous</span><span>looks safe</span>";
  const hs = honestSel();
  $("levers").innerHTML = '<div style="font-weight:700;margin-bottom:4px">Your levers</div>' + KEYS.map((k, n) => `<div class="lever ${S.sel[k] !== (k === "framing" ? 0 : hs[k]) ? "changed" : ""}"><b>${L()[n].label}</b><span class="v">${L()[n].options[S.sel[k]]}</span></div>`).join("");
  if (!$("visual").dataset.nb || $("visual").dataset.nb !== nb.id) {
    $("visual").dataset.nb = nb.id;
    const o = OUT[nb.id], cr = CREDITS[nb.id];
    const svg = o ? `<svg viewBox="-4 -4 ${o.w + 8} ${o.h + 8}"><path d="${o.path}" fill="var(--accent)" fill-opacity=".35" stroke="var(--accent)" stroke-width="1.2"/></svg>` : "";
    if (cr) { $("visual").innerHTML = `<img src="img/${nb.id}.jpg" alt="${nb.name}">`; $("visual").querySelector("img").onerror = () => { $("visual").innerHTML = svg; $("credit").textContent = "NPA boundary shown (no openly licensed photo available)."; };
      $("credit").innerHTML = `Photo: "${cr.title}" by ${cr.author}, ${cr.license} (<a href="${cr.url}" target="_blank" rel="noopener">source</a>). ${nb.blurb}`; }
    else { $("visual").innerHTML = svg; $("credit").textContent = `NPA boundary shown (no openly licensed photo available). ${nb.blurb}`; }
  }
}

function openReveal(html) { $("revealCard").innerHTML = html; $("reveal").hidden = false; G.scene.pause = true; }
function closeReveal() { $("reveal").hidden = true; G.scene.pause = false; }

function chooseGoal(nb) {
  openReveal(`<h2>${nb.name}</h2><p>${nb.blurb}</p><p>Population ${nb.population.toLocaleString()} &middot; jobs ${nb.jobs.toLocaleString()}${nb.income ? ` &middot; median household income $${Math.round(nb.income).toLocaleString()}` : ""}</p>
    <p><b>Pick your client.</b> The data stay real; only the presentation changes.</p>
    <button onclick="startCase('${nb.id}','safe')">A realtor: make it look SAFE</button>
    <button onclick="startCase('${nb.id}','danger')">A security vendor: make it look DANGEROUS</button>
    <button class="alt" onclick="closeReveal()">Cancel</button>`);
}
window.closeReveal = closeReveal;
window.startCase = (id, goal) => {
  S.nb = G.neighborhoods.find((n) => n.id === id); S.goal = goal;
  S.sel = { denominator: 0, offenses: 0, year: 0, geography: 0, peer: 0, framing: 0 };
  closeReveal(); G.scene.enterLab(); updateUI();
};

function publish() {
  const nb = S.nb, sign = S.goal === "safe" ? 1 : -1, hs = honestSel(), honest = calc(nb, hs);
  const mine = calc(nb, S.sel);
  let best = 0; allCombos((s) => { best = Math.max(best, sign * (calc(nb, s).perceived - honest.perceived)); });
  const shift = sign * (mine.perceived - honest.perceived), pct = best > 0 ? Math.max(0, shift) / best : 0;
  const stars = pct >= 0.75 ? 3 : pct >= 0.4 ? 2 : pct > 0.05 ? 1 : 0;
  const contrib = KEYS.map((k, n) => { const alt = { ...S.sel, [k]: k === "framing" ? 0 : hs[k] }; return { k, n, d: sign * (mine.perceived - calc(nb, alt).perceived) }; })
    .filter((c) => S.sel[c.k] !== (c.k === "framing" ? 0 : hs[c.k]) && Math.abs(c.d) >= 0.5).sort((a, b) => b.d - a.d);
  const rows = contrib.map((c) => `<tr><td>${L()[c.n].label}</td><td>${L()[c.n].options[S.sel[c.k]]}</td><td>${c.d >= 0 ? "+" : ""}${c.d.toFixed(0)}</td></tr>`).join("");
  const top = contrib[0];
  openReveal(`<h2>${"&#9733;".repeat(stars)}${"&#9734;".repeat(3 - stars)} ${stars === 3 ? "Master spinner" : stars === 2 ? "Convincing" : stars === 1 ? "A nudge" : "Barely moved"}</h2>
    <p><b>Your headline:</b> ${mine.html}</p>
    <p><b>The straight version</b> (per resident, reliably-reported crimes, latest year, this NPA, all NPAs): ${honest.html}</p>
    <p>You moved the public impression <b>${Math.max(0, shift).toFixed(0)}</b> of a possible <b>${best.toFixed(0)}</b> points toward your client, without altering any data.</p>
    ${rows ? `<table><tr><th>Lever you pulled</th><th>Setting</th><th>Points toward goal</th></tr>${rows}</table>` : ""}
    ${top && top.d > 0 ? `<p><b>Biggest trick:</b> ${TIPS[top.k]}</p>` : ""}
    <p style="color:var(--muted);font-size:13px">Takeaway: a safety score is a bundle of choices. When you see one, ask what it divides by, which crimes and years it counts, how big the area is, and who it is compared with.</p>
    <button onclick="startCase('${nb.id}','${S.goal === "safe" ? "danger" : "safe"}')">Same place, opposite client</button>
    <button onclick="startCase('${nb.id}','${S.goal}')">Try again</button>
    <button class="alt" onclick="closeReveal();G.scene.enterOffice()">Back to the office</button>
    <button class="alt" onclick="closeReveal()">Keep tweaking</button>`);
}

class Main extends Phaser.Scene {
  create() {
    G.scene = this; this.stations = []; this.objs = [];
    this.player = this.add.container(W / 2, H - 80, [this.add.rectangle(0, 8, 22, 26, 0x5b3fb0), this.add.circle(0, -10, 9, 0xf1c9a5)]).setDepth(5);
    this.cur = this.input.keyboard.createCursorKeys();
    this.wasd = this.input.keyboard.addKeys("W,A,S,D,E,SHIFT");
    this.prompt = this.add.text(0, 0, "", { fontFamily: "system-ui", fontSize: "13px", color: "#fff", backgroundColor: "#000c", padding: { x: 6, y: 3 } }).setDepth(9).setVisible(false);
    this.enterOffice();
  }
  clear() { this.objs.forEach((o) => o.destroy()); this.objs = []; this.stations = []; }
  add_(o) { this.objs.push(o); return o; }
  station(x, y, w, h, color, label, use, dyn) {
    const r = this.add_(this.add.rectangle(x, y, w, h, color).setStrokeStyle(2, 0x1d1b22));
    const t = this.add_(this.add.text(x, y - h / 2 - 36, label, { fontFamily: "system-ui", fontSize: "12px", color: "#1d1b22", align: "center", wordWrap: { width: w + 70 } }).setOrigin(0.5, 0));
    const s = { x, y, w, h, use, label, t, dyn }; this.stations.push(s); return s;
  }
  floor(c1, c2) { this.cameras.main.setBackgroundColor(c1); this.add_(this.add.rectangle(W / 2, H / 2, W - 20, H - 20, c2).setStrokeStyle(3, 0x1d1b22)); }
  enterOffice() {
    S.mode = "office"; this.clear(); this.floor(0xcfc7ba, 0xefe8dc);
    this.add_(this.add.text(W / 2, 28, "THE OFFICE: walk to a case file and press E", { fontFamily: "system-ui", fontSize: "18px", color: "#1d1b22" }).setOrigin(0.5));
    G.neighborhoods.forEach((nb, i) => this.station(120 + i * 187, 150, 96, 60, 0x8a6f4d, nb.name.replace(/ \(NPA/, "\n(NPA"), () => chooseGoal(nb)));
    this.add_(this.add.text(W / 2, H - 40, "Move: WASD / arrows   Use: E", { fontFamily: "system-ui", fontSize: "13px", color: "#6b6672" }).setOrigin(0.5));
    this.player.setPosition(W / 2, H - 100);
  }
  enterLab() {
    S.mode = "lab"; this.clear(); this.floor(0xbfc9d6, 0xe6ecf4);
    this.add_(this.add.text(W / 2, 28, `ANALYST ROOM: ${S.nb.name}`, { fontFamily: "system-ui", fontSize: "18px", color: "#1d1b22" }).setOrigin(0.5));
    KEYS.forEach((k, n) => {
      const x = 150 + (n % 3) * 250, y = 140 + Math.floor(n / 3) * 150;
      this.station(x, y, 110, 56, 0x4a6fa5, "", (dir) => { S.sel[k] = (S.sel[k] + dir + L()[n].options.length) % L()[n].options.length; toast(`${L()[n].label} ${L()[n].options[S.sel[k]]}`); this.refresh(); updateUI(); }, { k, n });
    });
    this.station(W / 2, H - 70, 130, 50, 0xb3402e, "PUBLISH DESK\n(E to publish)", () => publish());
    this.station(70, H - 70, 70, 50, 0x8a6f4d, "Exit to office", () => this.enterOffice());
    this.add_(this.add.text(W / 2, H - 22, "E: next setting   Shift+E: previous", { fontFamily: "system-ui", fontSize: "12px", color: "#6b6672" }).setOrigin(0.5));
    this.refresh(); this.player.setPosition(W / 2, H - 140);
  }
  refresh() { this.stations.forEach((s) => { if (s.dyn) s.t.setText(`${SHORT[s.dyn.k]}\n${L()[s.dyn.n].options[S.sel[s.dyn.k]].slice(0, 26)}`); }); }
  update(_, dt) {
    if (this.pause) return;
    const sp = 0.19 * dt, c = this.cur, w = this.wasd; let dx = 0, dy = 0;
    if (c.left.isDown || w.A.isDown) dx -= 1; if (c.right.isDown || w.D.isDown) dx += 1;
    if (c.up.isDown || w.W.isDown) dy -= 1; if (c.down.isDown || w.S.isDown) dy += 1;
    if (dx && dy) { dx *= 0.707; dy *= 0.707; }
    const p = this.player; p.x = Phaser.Math.Clamp(p.x + dx * sp, 30, W - 30); p.y = Phaser.Math.Clamp(p.y + dy * sp, 60, H - 30);
    let near = null, nd = 70;
    this.stations.forEach((s) => { const d = Math.hypot(s.x - p.x, s.y - p.y); if (d < nd) { nd = d; near = s; } });
    if (near) { this.prompt.setText(S.mode === "lab" && near.dyn ? "E / Shift+E" : "Press E").setPosition(p.x - 30, p.y - 44).setVisible(true); } else this.prompt.setVisible(false);
    if (near && Phaser.Input.Keyboard.JustDown(w.E)) near.use(w.SHIFT.isDown ? -1 : 1);
  }
}

async function boot() {
  const [data, outl, cred] = await Promise.all([fetch("data/game_data.json").then((r) => r.json()), fetch("data/outlines.json").then((r) => r.json()), fetch("data/photo_credits.json").then((r) => r.json()).catch(() => ({}))]);
  G = { meta: data.meta, neighborhoods: data.neighborhoods }; OUT = outl; CREDITS = cred;
  window.G = G;
  new Phaser.Game({ type: Phaser.AUTO, parent: "game", width: W, height: H, scene: Main, pixelArt: true });
  updateUI();
}
boot();
