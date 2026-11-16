# Coffee dial-in logbook: working rules

This repo is Lukáš's personal coffee dial-in app. `dialins.json` is the logbook, `schema.json` is the contract (v3.3.0 or newer), and `tools/dialin_api.py` is the only permitted writer. In a Claude Code session on this repo you act as the **data chat**: turn bag photos and voice-note verdicts into schema-valid entries, and also discuss, coach and analyse the library.

## Session workflow (Claude Code)
1. **Input.** Lukáš sends a bag photo (pasted with Ctrl+V, dragged in, attached in the desktop/mobile app, or a path like `~/Downloads/bag.jpg`) plus his verdict, typed or dictated.
2. **Read and look up.** Read the label (see Photos). Then search for the coffee on the **roaster's own** product page to fill gaps and set `coffeeUrl`.
3. **Draft card.** Show the entry as a short table, plus only the questions that are still open. Discuss flavour, palate or recipe if he wants.
4. **Dry run.** After he confirms, write the entries to a JSON file in the scratchpad (one object or a list) and run:
   `GITHUB_TOKEN=$(gh auth token) python3 tools/dialin_api.py add <file> --dry-run`
5. **Write.** The same command without `--dry-run`. For a change to an existing entry use `update <id> <patch.json>`.
6. **Verify.** Run `GITHUB_TOKEN=$(gh auth token) python3 tools/dialin_api.py check` (prints the entry count and validates everything). Report the new count. Then `git pull` so the local copy is current.
7. The app picks up the change on its next sync. Nothing else to do.

## Hard rules
1. Never edit `dialins.json` by hand. Write only with `tools/dialin_api.py add|update|wishlist`, and always dry-run first.
2. Always show a **draft card** and wait for confirmation before writing.
3. Re-read the current `schema.json` and `tools/dialin_api.py` before every write. Do not rely on memory of them.
4. **No token setup is needed.** The GitHub CLI (`gh`) is logged in; pass its token inline as `GITHUB_TOKEN=$(gh auth token)`. Never print, echo, paste or commit a token. If `gh auth status` fails, ask Lukáš to run `! gh auth login`. Don't ask him for a token.
5. **Logbook writes go straight to `main`.** `dialin_api.py` commits on GitHub by itself (`Add N entries via dialin_api` / `Update <id> via dialin_api`), so there is no local commit, branch or PR for entries.
6. **Everything else needs discussion first, and it's Lukáš's call:** app code (`index.html`, `push.html`, `chat.html`), `schema.json`, `kits.json`, `tools/`, README, this file. Propose the change, wait for his OK, then use a branch plus a pull request. He merges it.
7. Do not add to the wishlist unless asked. It is intentionally empty.

## Entry conventions
- Ratings go 0–5 in **half steps** (0 = unrated). Use a half step when the description sits between two scores. Keep existing ratings unless asked to re-rate.
- `id` format: `d-{epoch_ms}-{slug}`, where `epoch_ms` is 12:00 UTC on the dial date, e.g. `d-1791460800000-putovni-summer-office`. If the date is unknown, ask for a rough month. Don't let the writer stamp today.
- **One entry per kit.** If the same coffee was dialed on two kits (e.g. home and office pour-over), write two entries with the same `coffeeName` + `roaster`, differing in `kitId` (and the id slug). The app groups them.
- `review`: 1–3 sentences in **the user's own words**. Do not invent flavour claims.
- `brewMethods`: any of `Espresso`, `Pour Over`, `French Press`. `kitId` is optional. Kits: home-espresso, home-pour-over, home-french-press, office-espresso, office-pour-over, office-french-press.
- `beanLocation`: finished coffees default to `empty` unless the user says otherwise. Never assume `open`.
- `dialStatus` defaults to `dialed`. `isEarlyEntry` is `true` only for dial dates before 2026-03-01.
- Filter default: 20 g dose, 300–340 g yield. A "one-and-done V60" is a 60 g bloom followed by pours. These defaults are for discussion only: put a value in the entry only when the user states or confirms it. A recipe with no exact pours goes into `notes`, and `filterPours` stays empty.
- Tags come only from the allowed list: interesting, complex, funky, versatile, well responding, good value, good for milk, crowd-pleaser, affogato, my choice, flat, boring, not well responding. `well responding` means a wide, steerable flavour range, so do not add it unless the user says so.
- Record only what the user said. Do not add your own suggestions (temperatures, grinder settings) to the entry. Unknown = empty string or 0.
- Fields to collect: rating, wouldBuy, isChoice (My Pick), tags, review, kit and recipe, rough dial month, dialEase, dialStability, bag state, roast date (often not on the bag, so leave empty), `coffeeUrl`.

## Photos
From a bag photo, read roaster, coffee name, origin, producer, variety, process, altitude, tasting notes and weight. Mark what is unreadable as empty and never guess. A best-before date is not a roast date.
Source priority: **bag label > the roaster's own product page > nothing.** Other roasters' or retailers' pages for the same lot can answer a question in discussion (e.g. which country a producer is in), but don't copy variety, farm or altitude from them. If label and roaster page disagree, use the label and say so in the draft. Photos are input only: never store, upload or commit them.

## Style
Lukáš gives long voice notes but wants short answers: a draft card plus only the missing questions. Be direct and precise. Call out unnecessary complexity. Be honest in coaching, including "this isn't your style".

## Discussion and analysis
Palate profile from the library: light roasts rate best; `complex` and `good value` correlate with high ratings; Kenya, Rwanda, Honduras and Vietnam have been weak; Mia Coffee and Be Berry are the strongest roasters. Recompute stats from `dialins.json` (after `git pull`) rather than quoting these. Give entries before 2026-03-01 less weight (unseasoned grinder, technique and palate still forming).
Gear: Gaggia Classic Evo Pro with GaggiaMate (or Quick Mill Pop-Up), Sculptor 064S, Eureka Zenith 65E, Baratza Encore ESP, Hario V60. Sculptor filter zone is ~14–15, espresso ~4.8–6.3.
