# Derived game data

- `fleet-regs.json` — compact Tail/country weights + sample civil registrations.
  Built offline from private fleet CSVs (bizjet/GA filtered).
  Contains **registrations and country weights only** — no operator, owner, or other PII.

- `type-operators.json` — compact Name That Jet **owner/operator bonus** labels.
  Keys match quiz `manufacturer|displayName`. Each type lists real operator names
  used as answers (rotated) plus shared distractor pools by size class.
  Built offline from private fleet CSVs; **quiz catalog types only** — not a full
  fleet dump. Prefer current-status rows; blanks / “Private” / OEM factory pools
  / registration-looking junk are filtered out.

Source CSVs are **not** published in this repo. Rebuild with
`scripts/build_type_operators.py` when private CSVs or the quiz catalog change.
