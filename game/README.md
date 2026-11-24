# Spin Doctor (game)

Walk a little analyst around an office, open a neighborhood's case file, take a client (a realtor who wants the area to look safe, or a security vendor who wants it to look dangerous), then walk between six "lever" stations and cycle the settings. The headline and the safety meter on the right update live. Walk to the publish desk to see the reveal: the straight version, how far you moved the impression, and which trick did the most work. The data never change, only the presentation.

## Run it
```bash
python3 -m http.server 8610 --directory game     # then open http://localhost:8610
```
Controls: WASD or arrow keys to move, **E** to use a station, **Shift+E** to cycle a lever backwards. It is a static page (Phaser 3.80.1 from cdnjs), so it can be hosted anywhere, e.g. Vercel.

## How it works
- `d3_modeling/spin_engine.py` precomputes every combination of six levers for four NPAs and writes `data/game_data.json` (87 KB). Levers: what to divide by, which crimes count, which year, how big the area is (own NPA / plus neighbors / plus their neighbors), which comparison group, and how it is headlined (letter grade / % change since peak / % change since lowest year).
- `game.js` looks up the precomputed numbers; there is no backend. "Perceived safety" is 100 minus the percentile (grade framing) or a function of the % change (trend framing). The straight version is per resident, reliably-reported crimes, 2025, own NPA, all NPAs.
- The four neighborhoods: NPA 138 (W. Sugar Creek Rd / I-85), NPA 21 (E. Sugar Creek Rd), NPA 392 (Myers Park), NPA 315 (Plaza Midwood). **The name-to-NPA match came from address lookups and is approximate; verify it in the Charlotte Quality of Life Explorer.** An NPA is not the same as a neighborhood.
- Photos are from Wikimedia Commons (credits in `data/photo_credits.json`, shown in the game). There is no openly licensed photo of NPA 138, and the NoDa photo for NPA 21 hit a Wikimedia rate limit; both show the NPA outline instead. To add a photo, drop `img/<id>.jpg` and add its entry to `photo_credits.json`.

## Hand-off notes for whoever polishes this
Everything visual is placeholder rectangles drawn in `game.js`; the logic is in good shape. Good next steps:
1. Real art: pixel-art office and analyst room (tilemap), character sprite with walk animation, NPC clients with dialogue, sound.
2. Make each neighborhood its own walkable scene with the real photo as a backdrop.
3. Mobile controls (virtual joystick and an action button).
4. Keyboard accessibility for the HTML panel, plus a non-game "just use sliders" mode.
5. More cases, and photos for the two Sugar Creek areas.
Keep the disclaimer in the footer; the game must not label real neighborhoods as good or bad.
