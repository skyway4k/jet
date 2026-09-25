# Name That Private Jet

Mobile-first trivia: identify business jets (and a few helicopters) from exterior photos.

**Play:** https://skyway4k.github.io/jet/

## Features

- Expanded catalog (~108 types), 4 similar multiple-choice options, optional hints
- **Family uniqueness:** distractors never include a near-variant of the correct type (e.g. Global 6500 will not appear with Global 6000/7500; G650 not with G650ER; Falcon 7X not with 8X)
- Name entry at start; **streak** of consecutive correct answers
- On a miss, streak saved to a local **leaderboard** (name + streak + date)
- Tap anywhere after a correct answer to continue (no Continue button)
- Spoiler-safe: attribution and type-bearing alt only after you answer
- **Exterior photos only** — prefer **side / 3/4 profile** views with **exactly one aircraft** in frame

## Photo loading (fast path)

Rounds prefer, in order:

1. **User-hosted exteriors** under `images/user/` (catalog `images` / `localImage`)
2. **Baked Wikimedia Commons exterior thumbs** embedded in `index.html` (no Commons search API)
3. **Live Commons search** — fallback only if a URL fails

Upcoming rounds are preloaded aggressively, including during the name-entry screen.

See `images/README.md` for adding more of your own exterior photos.

## Notes

Player name and leaderboard live in **browser `localStorage`** (`nameThatJetPlayerName`, `nameThatJetLeaderboard`). They are per-device / per-browser — not synced across phones or private windows.

Single self-contained `index.html` — no build step. GitHub Pages serves from `main` at `/jet/`.
