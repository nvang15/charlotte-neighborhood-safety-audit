# Hand-off: make "Spin Doctor" an immersive game

You are picking up a working prototype. The data and game logic are done and tested; **the art, scenes, feel and polish are placeholders.** Your job is the immersive game experience. Read this whole file first.

## 1. What this project is
Class project "Rated for Whom? Auditing Neighborhood Safety Scores in Charlotte". Neighborhood "safety scores" are built from police-reported crime, and the way a score is built (what you divide by, which crimes and years you count, how big the area is, who you compare against, how it is headlined) can make the same place look safe or dangerous. The game teaches that by letting the player do the spinning.

**Premise:** the player is a data analyst. A client (a realtor who wants an area to look SAFE, or a security vendor who wants it to look DANGEROUS) hires them. The player chooses presentation settings; the data never change. A reveal shows the straight version, how far they moved the impression, and which trick did the most.

## 2. Where things are
- Repo: `~/Documents/charlotte-neighborhood-safety-audit` (clone of `github.com/nvang15/charlotte-neighborhood-safety-audit`). Work branch: **`d3-model-eval`**. The game is in `game/`. Do **not** commit to `main`, and do not touch the groupmate's D2 work (`dashboard/`, `data_preparation/`, `source_audit/`, `d2_eda/`) or their live Modal app. **Pushing needs the user's explicit OK** (the last two local commits, including the game, are not pushed yet).
- `game/index.html`, `style.css`, `game.js`: the whole game (static page, Phaser 3.80.1 from cdnjs, ~250 lines of JS).
- `game/data/game_data.json` (87 KB): precomputed numbers. `outlines.json`: SVG paths of each NPA boundary. `photo_credits.json`: licenses/credits for photos in `game/img/`.
- `d3_modeling/spin_engine.py`: generates `game_data.json` (run `cd d3_modeling && ../.venv/bin/python spin_engine.py`; the venv is `.venv` in the repo root).
- `game/README.md` has run instructions.

Run: `python3 -m http.server 8610 --directory game`, open http://localhost:8610. Controls: WASD/arrows move, **E** uses a station, **Shift+E** cycles a lever backwards.

## 3. How the current game works
- One Phaser scene (`Main`) with two modes: `office` (4 case-file cabinets, one per neighborhood) and `lab` (6 lever stations, a publish desk, an exit). The player is a rectangle plus circle; stations are rectangles with text labels. The nearest station within 70 px shows an "E" prompt.
- State is a plain object `S = {mode, nb, goal, sel}` where `sel` has one index per lever. The right-hand HTML panel (headline, meter, lever list, photo or boundary) is redrawn by `updateUI()`. The reveal is an HTML modal built in `publish()`.
- No backend. Every number is looked up from `game_data.json`.

### The six levers (index order is fixed; options live in `meta.levers`)
| key | options |
|---|---|
| denominator | none (raw counts) / per resident / per resident + jobs / per resident + 2x jobs ("daytime population") |
| offenses | all offenses / reliably-reported only / violent only / property only |
| year | 2025 / 2024 / 2023 / 2022 / 2021 |
| geography | this NPA only / NPA + neighbors / NPA + neighbors + their neighbors |
| peer | all Charlotte NPAs / similar-size NPAs / the 100 highest-count NPAs / the 100 lowest-count NPAs |
| framing | letter grade / % change since peak year / % change since lowest year (applied in JS, not precomputed) |

### Data schema
`game_data.json` = `{meta, neighborhoods[]}`. Each neighborhood has `id, npa, name, blurb, population, jobs, income` and `data: {pc, val, peak, low}`, each an array of 960 numbers, indexed by `(((denominator*4 + offenses)*5 + year)*3 + geography)*4 + peer`.
- `pc`: percentile (0 to 100) of the neighborhood's score among its peer group; higher = more reported crime.
- `peak` / `low`: fractional change in score from the highest / lowest year up to the chosen year (<=0 / >=0).
- `val`: the raw score (currently unused).
- `meta.honest` = the "straight version" lever settings: per resident, reliably-reported, 2025, own NPA, all NPAs, letter grade.

### Scoring in `game.js`
- Grade framing: perceived safety = `100 - pc`; letter grade A <20, B <40, C <60, D <80, F otherwise (on `pc`).
- Trend framing: perceived = `clamp(50 - 100*change)`.
- Spin score = sign(goal) x (perceived - honest perceived), compared with the best possible over all 2,880 combinations; 3 stars at >=75%.
- The reveal also resets one lever at a time to its honest value to rank which trick contributed most.

## 4. The four neighborhoods (all data are real CMPD reports, 2017 to 2025)
| id | NPA | Honest "perceived safety" | Range reachable with levers |
|---|---|---|---|
| sugar-creek-west | 138 (W. Sugar Creek Rd / I-85 motels) | 1.5 | 0 to 86 |
| sugar-creek-east | 21 (E. Sugar Creek Rd, NoDa side) | 4.2 | 0 to 77 |
| myers-park | 392 | 69.2 | 0 to 100 |
| plaza-midwood | 315 | 19.0 | 0 to 100 |

**Caution:** the name-to-NPA matches came from address lookups plus a point-in-polygon test, not an official list. An NPA is a city statistical area, not a neighborhood; one neighborhood can span several. Have the user confirm in the Charlotte Quality of Life Explorer (mcmap.org/qol) before presenting. Keep the "NPA" labeling visible in the UI.

## 5. Constraints you must respect
1. **Ethics.** The project promised not to label real neighborhoods "safe" or "unsafe". The game is about how numbers are *framed*. Never write text asserting an area is good/bad or dangerous. Keep the footer disclaimer (reported counts are not a measure of all crime; NPAs are not neighborhoods). The color scale for outputs is a neutral blue-violet in the map app; the meter red-to-green is the only good/bad coding, and it is labeled "looks dangerous / looks safe" (the impression), not the truth.
2. **Photos must be openly licensed with credit shown.** Existing: `myers-park.jpg` (CC BY-SA 3.0, Transderm) and `plaza-midwood.jpg` (CC BY-SA 4.0, RoxylovesHistory), both from Wikimedia Commons. Missing: NPA 138 (nothing relevant exists on Commons) and NPA 21 (the "Sidewalk in NoDa" file by Escapists606, CC BY-SA 4.0, failed to download because Wikimedia returned HTTP 429; retry slowly with a descriptive User-Agent). Do not scrape Google Street View. Options: Mapillary (CC BY-SA), the user's own photos, or illustrated scenes.
3. **Honesty about what the numbers are.** Counts are police-reported records (unfounded and non-criminal reports removed), at NPA level, 2017 to 2025. "Reliably-reported" means motor vehicle theft, burglary, robbery. The game's "straight version" is our own reasonable baseline, not ground truth, and the "rating site" behavior is our imitation, not any real company's method.
4. **Keep it a static site** (no server) unless the user asks otherwise. Target hosting: Vercel static. Do not deploy, publish or push without the user's confirmation.

## 6. What the user wants from you
"A better immersive experience for game development": a real video-game feel with a character you control. The prototype proves the loop; make it feel like a game. Ideas, roughly by value:
1. **Art and tilemap:** pixel-art office and analyst room (e.g. Tiled map or a hand-built tilemap in Phaser), a character sprite with 4-direction walk animation, collision with furniture, proper depth sorting.
2. **Walkable neighborhood scenes:** after taking a case, the player walks into the actual neighborhood (a stylized scene using the photo or an illustration as backdrop) and meets NPC residents/clients whose dialogue sets the story, instead of only a room of boxes. The levers can become in-world objects (a "denominator" calculator, a "which crimes" filing cabinet, a "map and ruler" for area size, a "comparison board", a "calendar" for the year, a "headline press").
3. **Narrative and progression:** an intro/tutorial, client dialogue, 4 cases of escalating difficulty, a "newspaper front page" payoff for the published headline, a final debrief ("how to read a safety score"), shareable result card.
4. **Juice:** sound and music, screen shake/transition effects, animated meter, lever animations.
5. **UX:** mobile/touch controls (virtual joystick plus action button), keyboard-accessible HTML panel, pause/menu, and a plain "sliders only" mode for people who do not want to walk.
6. **Content:** a "reveal the real numbers" screen with a small chart per neighborhood (counts by year) so players see the honest trend; optional extra neighborhoods (rerun `spin_engine.py` with more entries in `NEIGHBORHOODS`).

## 7. Practical notes
- Phaser pauses its game loop when the browser tab is hidden. In automated or background-tab testing nothing moves; step the scene manually: `G.scene.update(0, 16)` (a global `G` and `S` are exposed on `window`) or bring the tab to the foreground.
- Keep `calc()`, `publish()` and the `game_data.json` index formula in sync if you change lever counts (the index multipliers are hard-coded as 4/4/5/3/4 in `game.js` and `spin_engine.py`).
- If you change numbers in the engine, regenerate `game_data.json` and re-check that each neighborhood's reachable range is sensible (the engine prints it).
- Test in Chrome at ~800 px and phone width; the canvas is 800x520 and scales via CSS.
- Do not put secrets or incident-level data in the game; everything shipped is aggregated NPA-level data.

## 8. Wider project context (so you do not break it)
- D3 deliverable (model evaluation) lives in `d3_modeling/` (note: `D3_modeling_note.pdf`). It compares a naive raw-count score with an Empirical-Bayes rate, a Poisson regression (selected) and gradient boosting, using rolling temporal validation and a one-time 2025 test.
- A separate Streamlit app (`app/streamlit_app.py`, "Label Lottery") shows how many of 84 reasonable recipes label each NPA "worst 10%": 121 of 453 NPAs are labeled so by at least one recipe, only 6 by all. The game is the playful companion to that finding.
- Data pipeline: `d3_modeling/run_all.sh` fetches city data (CMPD ArcGIS layer and the Quality of Life service) and regenerates everything.
