# Exterior jet & helicopter photos

**Game rule:** exterior airframe views only — no cabin, galley, cockpit, or interior.

## Current layout

- `images/user/` — player Plane Wallpapers library (cropped/compressed). Wired via catalog `images: [...]` on matching types.

## How the game picks images

1. Catalog `images` / `localImage` / `localImages`, or global `LOCAL_IMAGES` in `index.html`
2. Baked Commons exterior thumb URLs
3. Live Commons search (fallback only)

## Adding more

Drop exteriors into `images/user/` (or a new folder), then point the type’s `images` array at those paths, or extend `LOCAL_IMAGES` keyed as `Manufacturer|DisplayName`.
