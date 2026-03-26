# Coffee Dial-In App — Project Brief
> Paste this entire file as your first message in any new Claude session to continue development.

---

## One-line summary
A personal coffee intelligence web app: equipment manager + dial-in logbook + GitHub sync, built as a single React `.jsx` file with no external dependencies beyond Google Fonts.

---

## The file
- **`coffee-dialin-app.jsx`** — the entire app lives here (one file, ~500 lines)
- All CSS is injected via a `<style>` tag inside a `useEffect` (stored in the `CSS` constant at the top)
- Rendered as a React artifact in Claude.ai

---

## Tech stack
| Layer | Choice | Reason |
|---|---|---|
| Framework | React (JSX, hooks only) | Works as a Claude artifact, no build step |
| Styling | Inline CSS string injected at runtime | Single-file constraint |
| Fonts | Cormorant Garamond + Jost + DM Mono (Google Fonts) | Distinctive aesthetic |
| Storage | `localStorage` (offline cache) + GitHub REST API (sync) | Offline-first, no backend |
| AI assistant | Claude.ai (external — user brings bag photos here) | No API key needed in app |

---

## Design aesthetic
- **Theme:** Dark roast — deep espresso browns (`#0C0501` bg), warm amber accent (`#C87840`)
- **Tone:** Refined / editorial. Not app-like, more like a barista's notebook.
- **Typography:** Cormorant Garamond (serif, display) + Jost (UI sans) + DM Mono (numbers/code)
- **Key visual rule:** Grind setting number is always the largest, most prominent element on any card or detail view
- **Grain texture overlay** on the whole app via SVG noise filter (subtle, adds depth)

---

## App structure (screens)

```
home       → Kit selector grid + 3 most recent dial-ins + sync button
kit        → Equipment list for one kit + dial-ins filtered to that kit
logbook    → All dial-ins, searchable + filterable by kit
dialin     → Full detail view for one dial-in
add        → New dial-in form
settings   → GitHub credentials (owner, repo, branch, PAT token)
```

Navigation: bottom nav bar (Kits / Log / Add / Settings). Detail screens (kit, dialin, add) hide the bottom nav and show a ← back button in the header.

---

## Data structures

### Kit object (`kits.json` — array)
```json
{
  "id": "home-espresso",
  "name": "Home Espresso",
  "subtitle": "Clickmill Pop Up",
  "tag": "ESPR",
  "color": "#C87840",
  "equipment": [
    { "category": "Machine",       "name": "Clickmill Pop Up",  "notes": "Home espresso machine" },
    { "category": "Portafilter",   "name": "Naked Portafilter", "notes": "Bottomless" },
    { "category": "Basket",        "name": "Pullman Basket",    "notes": "Precision extraction basket" },
    { "category": "Shower Screen", "name": "IMS Shower Screen", "notes": "Improved water distribution" },
    { "category": "Grinder",       "name": "Timemore 064S",     "notes": "Electric flat burr grinder" }
  ]
}
```

### Dial-in object (`dialins.json` — array, newest first)
```json
{
  "id": "d-1710000000000-abc1",
  "date": "2024-03-15",
  "kitId": "home-espresso",
  "coffeeName": "Ethiopia Yirgacheffe Natural",
  "roaster": "The Barn",
  "origin": "Ethiopia",
  "region": "Yirgacheffe",
  "process": "Natural",
  "roastLevel": "Light",
  "intendedFor": "Espresso",
  "flavorNotes": "Blueberry, dark chocolate, red wine",
  "grindSetting": "12.5",
  "grinder": "Timemore 064S",
  "doseIn": 18,
  "yieldOut": 36,
  "timeSeconds": 29,
  "temperature": 93,
  "rating": 5,
  "status": "dialed",
  "notes": "Perfect shot. Clean berry notes with dark chocolate finish."
}
```

**Allowed enum values:**
- `process`: Washed | Natural | Honey | Anaerobic | Wet-Hulled | Other
- `roastLevel`: Light | Medium-Light | Medium | Medium-Dark | Dark
- `intendedFor`: Espresso | Filter | Both
- `status`: experimenting | dialed
- `rating`: 0–5 (integer)

---

## GitHub sync

### How it works
- **Read:** `GET https://raw.githubusercontent.com/{owner}/{repo}/{branch}/kits.json` (no auth needed for public repos)
- **Write:** GitHub Contents API `PUT /repos/{owner}/{repo}/contents/{file}` — requires a Personal Access Token with `repo` scope
- On every app write, it fetches the current SHA of the file first (required by GitHub API to update)
- All data is also cached in `localStorage` under keys `ca_kits`, `ca_dialins`, `ca_settings`

### Repo structure expected
```
your-repo/
├── kits.json       ← array of Kit objects
└── dialins.json    ← array of DialIn objects (newest first)
```

---

## The Claude → App workflow (primary way to add dial-ins)

This is the intended day-to-day flow. No manual file editing needed.

### Step by step
1. Open Claude.ai on any device
2. Start a new chat — paste the project brief for context if starting fresh
3. Chat about your new coffee — describe the bag, share a photo, discuss the dial-in
4. When you've settled on parameters, say: **"Generate a dial-in JSON entry"**
5. Claude outputs a JSON block (see schema below)
6. Copy the JSON
7. Open the app → tap **Import** (⊕ in bottom nav)
8. Paste → Preview → **Save to GitHub**
9. App pushes directly to your repo — done

### Claude prompt to generate a dial-in JSON entry
Use this at the end of any dialing session:

```
Generate a dial-in JSON entry for my coffee app using this exact schema:

{
  "id": "d-[timestamp]-[4 random chars]",
  "date": "[today's date YYYY-MM-DD]",
  "kitId": "[home-espresso | office-espresso | pour-over | french-press]",
  "coffeeName": "",
  "roaster": "",
  "origin": "",
  "region": "",
  "process": "[Washed | Natural | Honey | Anaerobic | Wet-Hulled | Other]",
  "roastLevel": "[Light | Medium-Light | Medium | Medium-Dark | Dark]",
  "intendedFor": "[Espresso | Filter | Both]",
  "flavorNotes": "",
  "grindSetting": "",
  "grinder": "[Timemore Sculptor 064S | Eureka Zenith 65E | Baratza Encore ESP]",
  "doseIn": 0,
  "yieldOut": 0,
  "timeSeconds": 0,
  "temperature": 0,
  "rating": 0,
  "status": "[dialed | experimenting]",
  "notes": ""
}

Output ONLY the raw JSON, no explanation, no markdown code fences.
```

### Import screen features
- Accepts single object `{}` or array `[{}, {}]`
- Strips markdown code fences automatically
- Shows a preview before saving
- Auto-fills missing `id` and `date` if not provided
- Pushes directly to GitHub using the stored token
- Falls back to local cache if offline

---

## Current kit inventory (verified product names)

### Home Espresso — Quick Mill Pop-Up
| Category | Product | Notes |
|---|---|---|
| Machine | Quick Mill Pop-Up | Single boiler, PID + pressure profiling — filtered water only |
| Shower Screen | IMS Competition Shower Screen | Precision water distribution upgrade |
| Portafilter | MHW-3BOMBER Bottomless Portafilter | Naked / bottomless — 58mm |
| Basket | Pullman Barista Basket | Precision 58mm extraction basket |
| Tamper | Ikape V6 Calibrated Tamper | Constant-pressure click tamper |
| Puck Prep | Ikape Blind Basket | Backflushing & cleaning |
| Grinder | Timemore Sculptor 064S | 64mm flat burrs, stock, stepless |
| Scale | Timemore Black Mirror Mini | With real-time flow rate display |
| Kettle | Sencor Clever Gooseneck Kettle | 600ml max, variable temperature |

### Office Espresso — Gaggia Classic Evo Pro
| Category | Product | Notes |
|---|---|---|
| Machine | Gaggia Classic Evo Pro | Black — bought used, single owner, home use |
| Grinder | Eureka Zenith 65E | 65mm flat burrs — used, burrs mid-life |
| Portafilter | MHW-3BOMBER Bottomless Portafilter | Naked / bottomless — Gaggia 58mm version |
| Baskets | Gaggia 58mm Double / Single / Blind | Stock Gaggia baskets |
| Tamper | Ikape V6 Calibrated Tamper | Constant-pressure click tamper |
| Puck Prep | 58mm Puck Screen + IWS Distribution & WDT Tools | Standard puck prep set |
| Scale | Generic Digital Scale | No Bluetooth — AliExpress, manual read |
| Water | Filtered Water | |
| Incoming | GaggiMate Standard Kit | Smart PID + temperature control — arriving ~2–3 weeks |

### Pour Over — Office Filter
| Category | Product | Notes |
|---|---|---|
| Dripper | Hario V60 Drip Coffee Dripper 02 | Moving from home to office |
| Filters | Hario V60 02 Paper Filters | |
| Grinder | Baratza Encore ESP | Bought used via Aukro — condition TBD, burr upgrade planned |
| Scale | Generic Digital Scale | Shared with espresso kit — Bluetooth + flow rate scale TBD |
| Kettle | Timemore Fish Smart Electric Kettle | TBD — shortlisted |

### French Press — Home Immersion
| Category | Product | Notes |
|---|---|---|
| Brewer | IKEA UPPHETTA French Press | Stainless steel & glass, wooden accents |
| Grinder | Timemore Sculptor 064S | Shared home grinder |

---

## Known pre-loaded dial-ins (seed data in DEF_DIALINS)

1. **Ethiopia Yirgacheffe Natural** — The Barn — Grind 12.5 — ★★★★★ — Home Espresso
2. **Colombia El Paraíso Washed** — Nomad Coffee — Grind 11 — ★★★★ — Home Espresso

---

## Development rules (important for future sessions)

1. **Never rewrite the whole file.** Always use `str_replace` to edit only the changed section.
2. **CSS lives in the `CSS` constant** at the very top of the file. Add new classes there.
3. **Default data** lives in `DEF_KITS` and `DEF_DIALINS` constants — these are the fallback when no GitHub data is loaded.
4. **Navigation** is handled by `screen` state string + `nav(screenName, data)` function. Adding a new screen = add to the `views` object in the root `App` component.
5. **No external React libraries** — hooks only (`useState`, `useEffect`). No routing library, no state management library.
6. **Mobile-first:** max-width 480px centered. Test all changes at mobile width.
7. **Grind setting** must always be visually dominant — never bury it.

---

## Planned / backlog features (not yet built)

- [ ] Fill out Office Espresso, Pour Over, French Press equipment lists
- [ ] Edit / delete a dial-in entry
- [ ] "All Kits" view showing every dial-in regardless of kit
- [ ] Sort options in logbook (by date, by rating, by grind setting)
- [ ] Duplicate a dial-in (for quick iteration)
- [ ] Extraction timer (countdown in the Add form)
- [ ] Export logbook as CSV or PDF
- [ ] Push new dial-in to GitHub from inside the app (already works — make it more obvious in UI)
- [ ] Onboarding flow for first-time GitHub setup

---

## Confidence weighting system — CRITICAL for palate queries

This is the most important context for any future Claude session when the user asks about preferences, rebuying coffees, or palate analysis.

### Background
- Hardware (Quick Mill Pop-Up + Timemore Sculptor 064S) arrived **November 2025**
- 1kg cheap coffee seasoning run done before first real bag
- First real dial-ins started **September–December 2025** (CSV entries)
- Flat burr grinders need **3–5kg** to fully season — at 250g/bag that's 12–20 bags minimum

### Three-layer confidence matrix

| Period | Hardware | Technique | Palate | Overall weight |
|---|---|---|---|---|
| Sep–Dec 2025 | Unseasoned burrs | Learning | Forming | **~30%** |
| Jan–Feb 2026 | Partially seasoned | Building | Developing | **~60%** |
| Mar 2026+ | Fully seasoned | Reliable | Clear signal | **100%** |

### What this means in practice

**Grind settings from Sep–Dec 2025 are coarser than equivalent today.**
When rebuying a coffee from that period, start **0.5–1.5 clicks finer** than the stored setting.

**Ratings from Sep–Dec 2025 carry reduced signal — both positive and negative.**
- A ★★★★★ from Dec 2025 ≠ a ★★★★★ from Mar 2026+
- A ★★ from Dec 2025 does NOT mean "never again" — it means "inconclusive, retry with seasoned setup"
- Coffees dismissed early may have had more to give
- Coffees accepted as "dialed" may not have been fully explored

**Palate preferences evolve — newer entries reflect truer preferences.**
When asked "what coffees should I rebuy?" or "what does my palate prefer?":
- Weight recent dial-ins (Mar 2026+) most heavily
- Treat Sep–Dec 2025 ratings as directional hints, not conclusions
- If a user says their taste is shifting (e.g. discovering they prefer floral/filter over dark/espresso), update your understanding and re-evaluate old ratings through that new lens

### The "early period" flag
Dial-ins dated before **1 March 2026** should be treated as early period entries.
In the app these are marked with an `earlyPeriod: true` flag and a subtle badge.

### When asked about palate preferences, always note:
> "Your earlier entries (Sep–Dec 2025) were pulled on an unseasoned grinder with a developing technique and palate. I'm weighting your more recent dial-ins more heavily in this analysis."

---

## Palate profile (evolving — update as new data comes in)

Based on dial-ins to date, emerging preferences:
- **Enjoys:** Expressive fruit-forward profiles (banana, tropical, berry), anaerobic/experimental processes, medium-light roasts for espresso
- **Anchor coffees:** Blends that work for both espresso and milk (Beskydská Směs type)
- **Less preferred:** Flat or one-dimensional profiles (Brazil Sul de Minas — "flat when pushed")
- **Still discovering:** Filter coffee preferences, dark roast limits
- **Note:** All of the above is based on early-period data and should be treated as provisional until more Mar 2026+ entries accumulate

---

## Planned / backlog features (not yet built)

- [ ] `earlyPeriod` badge on dial-ins before Mar 2026 in the app UI
- [ ] Confidence indicator on dial-in detail view
- [ ] Sort options in logbook (by date, by rating, by grind setting)
- [ ] Duplicate a dial-in (for quick iteration)
- [ ] Extraction timer (countdown in the Add form)
- [ ] Export logbook as CSV or PDF
- [ ] Delete a dial-in entry
- [ ] "All Kits" view showing every dial-in regardless of kit
- [ ] Auto-retry SHA mismatch already done in push.html ✅
- [ ] Edit dial-in and kit — already built ✅

---

*Last updated: March 2026 — added confidence weighting system, palate profile, photo-based coffee info workflow.*
