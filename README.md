# Name That Private Jet

Mobile-first trivia: identify business jets from live Wikimedia Commons photos.

**Play:** https://skyway4k.github.io/name-that-jet/

## Features

- 6 multiple-choice options per round, optional hints, score
- Name entry at start; current **streak** of consecutive correct answers
- On a miss, your streak is saved to a local **leaderboard** (name + streak + date)
- Spoiler-safe: Commons attribution and type-bearing image alt only after you answer

## Notes

Player name and leaderboard live in **browser `localStorage`** (`nameThatJetPlayerName`, `nameThatJetLeaderboard`). They are per-device / per-browser — not synced across phones or private windows.

Single self-contained `index.html` — no build step. GitHub Pages serves from `main`.
