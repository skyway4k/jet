# Exterior jet & helicopter photos

**Game rules:**
- Exterior airframe views only — no cabin, galley, cockpit, or interior
- Prefer **side or clear 3/4 profile** showing fuselage windows + engines + tail
- **Exactly one aircraft** in frame (no multi-aircraft ramps; no prominent second jet)

## Current layout

- `images/user/` — player Plane Wallpapers library (cropped/compressed). Wired via catalog `images: [...]` on matching types.

## How the game picks images

1. Catalog `images` / `localImage` / `localImages`, or global `LOCAL_IMAGES` in `index.html`
2. Baked Commons exterior thumb URLs
3. Live Commons search (fallback only)

## Adding more

Drop exteriors into `images/user/` (or a new folder), then point the type’s `images` array at those paths, or extend `LOCAL_IMAGES` keyed as `Manufacturer|DisplayName`.
