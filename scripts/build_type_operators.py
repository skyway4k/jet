#!/usr/bin/env python3
"""Build compact type→operator JSON for Name That Jet owner bonus.

Reads private fleet CSVs (not published) and the quiz catalog in index.html.
Writes data/type-operators.json — quiz types + distractor operators only.
"""
from __future__ import annotations

import csv
import json
import re
import collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "index.html"
OUT = ROOT / "data" / "type-operators.json"

CSV_PATHS = [
    Path("/home/box/agent-data/agents/a0c908c0-2b0e-4a0f-9d3b-44baf901a922/attachments/7415a116f543a3fa27b9dce84f2aa6a0eb7532498d325813a82022a38ce62113.csv"),
    Path("/home/box/agent-data/agents/a0c908c0-2b0e-4a0f-9d3b-44baf901a922/attachments/fc3c2f2a2dd8bd345e9a3c1a55548a494876743857dc77533feb35fe336fa484.csv"),
]

# OEM / factory / delivery-pool names — weak as "who operates this type" answers
OEM_OPERATORS = {
    "gulfstream aerospace",
    "gulfstream aerospace corp",
    "gulfstream aerospace corporation",
    "gulfstream",
    "dassault aviation",
    "dassault falcon jet",
    "dassault falcon jet corp",
    "dassault falcon jet corp.",
    "bombardier",
    "bombardier aerospace",
    "bombardier aerospace corp",
    "bombardier aerospace corp.",
    "bombardier inc",
    "embraer",
    "embraer executive aircraft",
    "embraer s.a.",
    "embraer sa",
    "cessna aircraft company",
    "cessna aircraft",
    "cessna",
    "textron aviation",
    "textron aviation (cessna)",
    "pilatus flugzeugwerke ag",
    "pilatus business aircraft ltd",
    "pilatus aircraft",
    "pilatus",
    "airbus",
    "airbus canada",
    "airbus canada (montreal)",
    "iai",
    "israel aerospace industries",
    "grumman",
    "northrop grumman",
}

JUNK_EXACT = {
    "private", "?", "n/a", "na", "unknown", "none", "-", "--", ".", "n.a.", "n.a",
    "privately owned", "private owner", "private individual", "private aircraft",
    "corporate", "corporation", "owner", "tbd", "tba", "xxx", "test", "demo",
    "private operator", "privately operated", "individual", "not known",
    "undisclosed", "confidential", "withheld", "see notes", "various",
    "private company", "private corp", "private corporation", "llc", "inc",
    "customer", "undelivered", "not delivered", "stock", "inventory",
}

# Big fractional / charter / fleet-management brands — fine as distractors or
# occasional easy answers, but downranked vs named owners / LLCs for correct answers.
EASY_FLEET_SUBSTR = (
    "netjets", "flexjet", "vistajet", "wheels up", "jet linx", "jetlinx",
    "corporate flight management", "execujet", "solairus",
    "executive jet management", "jet aviation", "clay lacy",
    "amber aviation", "thrive aviation", "jet edge", "sta jets",
    "gama aviation", "pentastar aviation", "quanta aviation",
    "alerion aviation", "chartright", "skyservice", "truaviation",
    "wingtip aviation", "jetselect", "fly exclusive", "plane sense",
    "airshare", "xsaviation", "exclusive jets", "jet it",
    "directional aviation", "mountain aviation", "windsor jet",
    "air charter group", "magellan jets", "sentient jet",
)

LLC_HINT = re.compile(
    r"\b(LLC|L\.L\.C\.?|Inc\.?|Ltd\.?|Corp\.?|Corporation|Company|Co\.?|"
    r"Trust|LLP|L\.P\.?|LP|GmbH|AG|S\.A\.?|SA|A\.S\.?|A\.Ş\.?|Pty|PLC)\b",
    re.I,
)


def is_easy_fleet(op: str) -> bool:
    low = (op or "").lower()
    return any(s in low for s in EASY_FLEET_SUBSTR)


def operator_tier(op: str) -> str:
    """named = preferred correct answers; easy = distractors / fallback answers."""
    if is_easy_fleet(op):
        return "easy"
    return "named"


def operator_score(op: str, count: int) -> tuple:
    """Sort key: named first, LLC/Inc hint next, then frequency."""
    tier = 0 if operator_tier(op) == "named" else 1
    llc = 0 if LLC_HINT.search(op or "") else 1
    return (tier, llc, -count, op.lower())



# Prefer these named owners in type answer pools (airframes we ship photos for)
PINNED_TYPE_OPERATORS: dict[str, list[str]] = {
    "Bombardier|Global Express / XRS": ["Genel Air"],
    "Gulfstream|G650ER": ["Pivotal Ventures LLC", "Qatar Executive"],
    "Gulfstream|G500": ["Starshot Ventures LLC"],
    "Gulfstream|G550": ["Silver Stream Aviation LLC"],
}


# Explicit quiz displayName → matchers against CSV model (lowercased)
# Each entry: list of (include_substrings_all, exclude_substrings_any)
# Matched if ANY rule hits (all includes present, no excludes).
TYPE_RULES: dict[str, list[tuple[list[str], list[str]]]] = {
    # Gulfstream
    "G150": [(["g150"], [])],  # may have none
    "G200": [(["g200"], []), (["gulfstream 200"], []), (["galaxy"], ["g280"])],
    "G280": [(["g280"], [])],
    "G350": [(["g350"], []), (["g-iv", "g350"], []), (["giv-x (g350)"], [])],
    "G450": [(["g450"], []), (["giv-x (g450)"], []), (["g-iv-x g450"], [])],
    "G500": [(["gvii-g500"], []), (["gvii (g500)"], [])],  # modern G500 only
    "G550": [(["g550"], ["g500", "c-37", "ea-37", "mc-55", "compass", "caew", "aew"])],
    "G600": [(["gvii-g600"], []), (["gvii (g600)"], [])],
    "G650": [(["g650"], ["g650er", "er)"])],
    "G650ER": [(["g650er"], [])],
    "G700": [(["g700"], []), (["gviii-g700"], [])],
    "G800": [(["g800"], []), (["gviii-g800"], [])],
    "GIV / G400": [(["g-iv"], ["g450", "g350", "g300", "g650", "sp", "x (", "x g", "giv-x"]),
                   (["g400"], ["g450"]), (["g-iv (g400)"], [])],
    "GV / G500 (classic)": [(["g-v"], ["g550", "g650", "sp", "gvii", "gviii"]),
                            (["gv-sp (g500)"], [])],
    "GII / GIII": [(["g-ii"], []), (["g-iii"], []), (["gii"], ["giii"]), (["giii"], [])],
    "G100": [(["g100"], []), (["astra"], [])],
    # Bombardier Global
    "Global 5000": [(["global 5000"], ["5500", "express 5000"])],
    "Global 5500": [(["global 5500"], []), (["express 5500"], [])],
    "Global 6000": [(["global 6000"], ["6500", "e-11"])],
    "Global 6500": [(["global 6500"], ["e-11", "hades", "globaleye", "tp 106"])],
    "Global 7500": [(["global 7500"], [])],
    "Global 8000": [(["global 8000"], [])],
    "Global Express / XRS": [(["global express"], ["5000", "5500", "6000", "7500", "8000", "e-11"]),
                             (["global xrs"], []), (["express xrs"], ["e-11", "5000", "6000"])],
    # Challenger
    "Challenger 300": [(["challenger 300"], ["350"])],
    "Challenger 350": [(["challenger 350"], ["3500"])],
    "Challenger 3500": [(["challenger 3500"], [])],
    "Challenger 600": [(["challenger 600"], ["605", "650", "crj"])],
    "Challenger 605": [(["challenger 605"], [])],
    "Challenger 650": [(["challenger 650"], [])],
    # Learjet — CSV may lack
    "Learjet 40": [(["learjet 40"], ["400", "45"])],
    "Learjet 45": [(["learjet 45"], [])],
    "Learjet 60": [(["learjet 60"], [])],
    "Learjet 70": [(["learjet 70"], [])],
    "Learjet 75": [(["learjet 75"], [])],
    "Learjet 31": [(["learjet 31"], [])],
    "Learjet 35": [(["learjet 35"], [])],
    # Cessna
    "Citation M2": [(["citation m2"], []), (["m2"], ["mustang"])],
    "Citation CJ2": [(["cj2"], []), (["citation cj2"], [])],
    "Citation CJ3": [(["cj3"], []), (["citation cj3"], [])],
    "Citation CJ4": [(["cj4"], []), (["citation cj4"], [])],
    "Citation Mustang": [(["mustang"], [])],
    "Citation Excel / XLS": [(["excel"], []), (["xls"], ["longitude"])],
    "Citation Latitude": [(["latitude"], []), (["680a"], [])],
    "Citation Longitude": [(["longitude"], []), (["700 citation"], [])],
    "Citation X": [(["citation x"], ["x+", "xplus"]), (["750 citation x"], ["x+"])],
    "Citation X+": [(["citation x+"], []), (["750 citation x+"], [])],
    "Citation Sovereign": [(["sovereign"], ["+", "plus"]), (["680 citation"], ["680a", "+"])],
    "Citation Ascend": [(["ascend"], [])],
    "Citation III / VI / VII": [(["citation iii"], []), (["citation vi"], []), (["citation vii"], [])],
    "Citation II / Bravo": [(["citation ii"], []), (["citation bravo"], []), (["bravo"], ["citation x"])],
    "Citation Encore": [(["encore"], [])],
    "Citation V / Ultra": [(["citation v"], ["vi", "vii"]), (["citation ultra"], []), (["ultra"], ["ultralong"])],
    # Embraer
    "Phenom 100": [(["phenom 100"], [])],
    "Phenom 300": [(["phenom 300"], [])],
    "Praetor 500": [(["praetor 500"], [])],
    "Praetor 600": [(["praetor 600"], [])],
    "Legacy 450": [(["legacy 450"], [])],
    "Legacy 500": [(["legacy 500"], [])],
    "Legacy 600": [(["legacy 600"], [])],
    "Legacy 650": [(["legacy 650"], [])],
    "Lineage 1000": [(["lineage 1000"], []), (["lineage"], [])],
    "EMB-120 Brasilia (VIP)": [(["brasilia"], []), (["emb-120"], [])],
    "ERJ-135 (VIP)": [(["erj-135"], []), (["erj 135"], [])],
    # Dassault
    "Falcon 6X": [(["falcon 6x"], [])],
    "Falcon 7X": [(["falcon 7x"], ["8x"])],
    "Falcon 8X": [(["falcon 8x"], [])],
    "Falcon 2000": [(["falcon 2000"], ["ex", "lx", "lxs", "dx", "s)", " 2000s", "2000lx", "2000ex", "2000s", "2000dx", "2000lxs"])],
    "Falcon 2000LXS": [(["2000lxs"], []), (["falcon 2000lxs"], [])],
    "Falcon 900": [(["falcon 900"], ["ex", "lx", "dx", "900b", "900c", "900ex", "900lx", "900dx", "msa"])],
    "Falcon 50": [(["falcon 50"], ["ex", "50-4", "50ex"])],
    "Falcon 10 / 100": [(["falcon 10"], []), (["falcon 100"], [])],
    "Falcon 20 / 200": [(["falcon 20"], ["falcon 200"]), (["falcon 200"], ["2000"]), (["mystere 20"], []), (["fan jet falcon"], [])],
    # Others
    "HondaJet HA-420": [(["hondajet"], []), (["ha-420"], [])],
    "Eclipse 500": [(["eclipse 500"], [])],
    "Eclipse 550": [(["eclipse 550"], [])],
    "Vision Jet SF50": [(["vision jet"], []), (["sf50"], [])],
    "SJ30": [(["sj30"], [])],
    "PC-24": [(["pc-24"], []), (["pc24"], [])],
    "Avanti": [(["avanti"], [])],
    "Premier I / IA": [(["premier"], [])],
    "King Air 350": [(["king air 350"], []), (["b300"], [])],
    "King Air 250": [(["king air 250"], [])],
    "Hawker 800XP": [(["hawker 800"], [])],
    "Hawker 850XP": [(["hawker 850"], [])],
    "Hawker 900XP": [(["hawker 900"], [])],
    "Hawker 4000": [(["hawker 4000"], [])],
    "Hawker 400XP": [(["hawker 400xp"], []), (["hawker 400"], ["4000"])],
    "CRJ (VIP / corporate)": [(["crj"], [])],
    "ACJ320 / ACJ319": [(["acj320"], []), (["acj319"], []), (["acj"], ["twotwenty", "two twenty", "a220"])],
    "BBJ (737)": [(["bbj"], ["787"]), (["737"], ["bbj 787"])],
    "BBJ 787": [(["bbj 787"], []), (["787"], ["757"])],
    "757 (VIP)": [(["757"], [])],
    "Westwind": [(["westwind"], [])],
    "Astra / G100": [(["astra"], []), (["g100"], [])],
    "SpaceJet / MU-300 Diamond": [(["spacejet"], []), (["mu-300"], []), (["diamond"], ["gulfstream"])],
    "328JET": [(["328jet"], []), (["328 jet"], []), (["dornier 328"], [])],
    "BAe 125 / HS-125": [(["bae 125"], []), (["hs-125"], []), (["hs125"], [])],
    "JetStar": [(["jetstar"], [])],
    "Sabreliner": [(["sabreliner"], [])],
    # Helis — unlikely in CSV
    "H125": [(["h125"], []), (["as350"], [])],
    "H135": [(["h135"], []), (["ec135"], [])],
    "H145": [(["h145"], []), (["ec145"], [])],
    "S-76": [(["s-76"], []), (["s76"], [])],
    "407": [(["bell 407"], [])],
    "429": [(["bell 429"], [])],
    "AW109": [(["aw109"], [])],
    "AW139": [(["aw139"], [])],
    "MD 500": [(["md 500"], []), (["md500"], [])],
}


def parse_catalog(html: str) -> list[dict]:
    m = re.search(r"const CATALOG = \[(.*?)\n  \];", html, re.S)
    if not m:
        raise SystemExit("CATALOG not found")
    planes = []
    for obj in re.finditer(r"\{([^{}]+)\}", m.group(1)):
        body = obj.group(1)
        dn = re.search(r'displayName:\s*"([^"]+)"', body)
        mf = re.search(r'manufacturer:\s*"([^"]+)"', body)
        sc = re.search(r'sizeClass:\s*"([^"]+)"', body)
        dis = bool(re.search(r"disabled:\s*true", body))
        if dn and mf:
            planes.append({
                "manufacturer": mf.group(1),
                "displayName": dn.group(1),
                "sizeClass": sc.group(1) if sc else "",
                "disabled": dis,
                "key": mf.group(1) + "|" + dn.group(1),
            })
    return planes


def is_junk_operator(op: str) -> bool:
    if not op or not op.strip():
        return True
    s = op.strip()
    low = s.lower()
    if low in JUNK_EXACT:
        return True
    if low in OEM_OPERATORS:
        return True
    # OEM substring catch
    for oem in (
        "gulfstream aerospace", "dassault aviation", "dassault falcon jet",
        "bombardier aerospace", "embraer executive", "cessna aircraft",
        "pilatus flugzeugwerke", "pilatus business aircraft", "textron aviation",
        "airbus canada",
    ):
        if oem in low:
            return True
    o = s.upper().replace(" ", "")
    if re.fullmatch(r"N[0-9]{1,5}[A-Z]{0,2}", o):
        return True
    if re.fullmatch(r"[A-Z0-9]{1,2}-[A-Z0-9]{2,5}", o):
        return True
    if len(s) <= 2:
        return True
    if re.fullmatch(r"[\W_]+", s):
        return True
    if sum(ch.isdigit() for ch in s) > len(s) * 0.6:
        return True
    # bare "Private …" patterns
    if low.startswith("private ") and len(s) < 20:
        return True
    return False



def extract_owner_from_notes(notes: str) -> str | None:
    """Pull a named LLC/company from notes when operator field is blank."""
    if not notes:
        return None
    # Find LLC/Inc/Ltd/Trust phrases; pick the longest plausible company name
    matches = re.finditer(
        r"\b([A-Z][A-Za-z0-9&.'\-]*(?:\s+[A-Z][A-Za-z0-9&.'\-]*){1,6}\s+"
        r"(?:LLC|L\.L\.C\.?|Inc\.?|Ltd\.?|Corp\.?|Corporation|Trust|LLP|GmbH|AG))\b",
        notes,
    )
    best = None
    for m in matches:
        cand = normalize_op(m.group(1))
        # Require at least 2 content words before the entity suffix
        words = cand.split()
        if len(words) < 3:
            continue
        if is_junk_operator(cand) or is_easy_fleet(cand):
            continue
        # Reject truncated fragments like "Air LLC" / "Aviation LLC"
        if words[0].lower() in {"air", "aviation", "jet", "flight", "aircraft", "the"}:
            continue
        if best is None or len(cand) > len(best):
            best = cand
    return best


def normalize_op(op: str) -> str:
    s = re.sub(r"\s+", " ", op.strip())
    # light cleanup of trailing corp noise for display consistency — keep as-is mostly
    return s


def _contains_token(hay: str, needle: str) -> bool:
    """Substring match that avoids falcon 20 ⊂ falcon 2000 style false hits."""
    if not needle:
        return True
    n = needle.lower()
    h = hay.lower()
    start = 0
    while True:
        i = h.find(n, start)
        if i < 0:
            return False
        before = h[i - 1] if i > 0 else ""
        after = h[i + len(n)] if i + len(n) < len(h) else ""
        # Allow match at edges or beside non-alnum; reject if glued to more alnum/digits
        ok_before = (not before) or (not before.isalnum())
        ok_after = (not after) or (not after.isalnum())
        # Special: trailing + for X+ etc. is part of needle already
        if ok_before and ok_after:
            return True
        # Also allow after to be '+' only when needle already ends with issues — handled above
        start = i + 1


def model_matches(model: str, rules: list[tuple[list[str], list[str]]]) -> bool:
    m = model.lower()
    for includes, excludes in rules:
        if all(_contains_token(m, inc) for inc in includes) and not any(_contains_token(m, ex) for ex in excludes):
            return True
    return False


def size_bucket(size_class: str) -> str:
    sc = (size_class or "").lower()
    if "heli" in sc:
        return "heli"
    if sc in ("light", "very light", "entry"):
        return "light"
    if "mid" in sc or sc in ("super-midsize", "midsize"):
        return "mid"
    if "large" in sc or "ultra" in sc or "heavy" in sc:
        return "large"
    if "turboprop" in sc:
        return "turboprop"
    return "other"


def load_rows() -> list[dict]:
    # Prefer current-status rows from both CSVs; CSV2 is mostly current subset.
    # Deduplicate by registration+model+operator.
    seen = set()
    rows = []
    for path in CSV_PATHS:
        if not path.exists():
            continue
        with open(path, newline="", encoding="utf-8", errors="replace") as f:
            for row in csv.DictReader(f):
                brand = (row.get("brand") or "").strip()
                model = (row.get("model") or "").strip()
                op = normalize_op(row.get("operator") or "")
                notes = (row.get("notes") or "").strip()
                if is_junk_operator(op):
                    from_notes = extract_owner_from_notes(notes)
                    if from_notes:
                        op = from_notes
                reg = (row.get("registration") or "").strip()
                status = (row.get("status") or "").strip().lower()
                if not model:
                    continue
                key = (reg, model.lower(), op.lower())
                if key in seen:
                    continue
                seen.add(key)
                rows.append({
                    "brand": brand,
                    "model": model,
                    "operator": op,
                    "registration": reg,
                    "status": status,
                    "current": status == "current" or status == "",
                })
    return rows


def main() -> None:
    planes = parse_catalog(HTML.read_text(encoding="utf-8"))
    rows = load_rows()
    print(f"catalog={len(planes)} rows={len(rows)}")

    # For each type, collect operator counts (prefer current)
    type_ops: dict[str, collections.Counter] = {}
    type_ops_current: dict[str, collections.Counter] = {}
    type_meta: dict[str, dict] = {}

    for p in planes:
        if p["disabled"]:
            continue
        rules = TYPE_RULES.get(p["displayName"])
        if not rules:
            # fallback: try displayName tokens in model
            tokens = re.findall(r"[A-Za-z0-9+]+", p["displayName"])
            tokens = [t.lower() for t in tokens if len(t) > 1 and t.lower() not in ("the", "and", "vip")]
            rules = [(tokens[:2] if len(tokens) >= 2 else tokens, [])] if tokens else []
        cops = collections.Counter()
        cops_cur = collections.Counter()
        matched_models = set()
        for row in rows:
            if not model_matches(row["model"], rules):
                continue
            matched_models.add(row["model"])
            op = row["operator"]
            if is_junk_operator(op):
                continue
            cops[op] += 1
            if row["status"] == "current":
                cops_cur[op] += 1
        type_ops[p["key"]] = cops
        type_ops_current[p["key"]] = cops_cur
        type_meta[p["key"]] = {
            "displayName": p["displayName"],
            "manufacturer": p["manufacturer"],
            "sizeClass": p["sizeClass"],
            "bucket": size_bucket(p["sizeClass"]),
            "matchedModels": sorted(matched_models)[:12],
            "usableOps": len(cops),
            "usableCurrent": len(cops_cur),
        }

    # Build published payload
    types_out = {}
    used_operators = set()
    coverage = []

    for p in planes:
        if p["disabled"]:
            continue
        key = p["key"]
        # Prefer current-status operators; fall back to all usable
        primary = type_ops_current[key]
        all_ops = type_ops[key]
        # Prefer current; merge all when current pool is thin (<3 distinct or <5 sightings)
        if len(primary) < 3 or sum(primary.values()) < 5:
            merged = all_ops
        else:
            merged = primary

        # Require at least one solid operator with count>=1 and preferably not ultra-rare alone
        if not merged:
            continue

        # Split named owners/LLCs vs easy fleet brands; prefer named for correct answers
        named = [(op, c) for op, c in merged.items() if operator_tier(op) == "named"]
        easy = [(op, c) for op, c in merged.items() if operator_tier(op) == "easy"]
        named_ranked = [op for op, c in sorted(named, key=lambda x: operator_score(x[0], x[1]))]
        easy_ranked = [op for op, c in sorted(easy, key=lambda x: (-x[1], x[0].lower()))]

        # Correct-answer pool: named/LLC first; fall back to easy fleets only if none
        if named_ranked:
            answers = named_ranked[:8]
            easy_for_type = easy_ranked[:6]
        else:
            answers = easy_ranked[:8]
            easy_for_type = easy_ranked[8:14]

        if not answers:
            continue

        entry = {
            "answers": answers,
            "bucket": size_bucket(p["sizeClass"]),
        }
        if easy_for_type:
            entry["easy"] = easy_for_type
        # Pin known photo airframe owners to the front of the answer pool
        for pinned in PINNED_TYPE_OPERATORS.get(key, []):
            if pinned not in entry["answers"]:
                entry["answers"] = [pinned] + entry["answers"]
            else:
                entry["answers"] = [pinned] + [a for a in entry["answers"] if a != pinned]
            entry["answers"] = entry["answers"][:8]
        types_out[key] = entry
        used_operators.update(answers)
        used_operators.update(easy_for_type)
        top = answers[0]
        coverage.append((key, len(answers), top, merged[top],
                         sum(1 for a in answers if operator_tier(a) == "named")))

    # Distractor pools by bucket from all used + other frequent non-OEM operators
    # Collect global frequent operators from current rows
    global_ops = collections.Counter()
    for row in rows:
        if row["status"] not in ("current", ""):
            continue
        op = row["operator"]
        if is_junk_operator(op):
            continue
        global_ops[op] += 1

    # ensure distractor pool has operators beyond type answers
    for op, c in global_ops.most_common(400):
        if c >= 2:
            used_operators.add(op)

    # Bucket operators by which types they appear with most
    bucket_ops: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for p in planes:
        if p["disabled"] or p["key"] not in types_out:
            continue
        b = types_out[p["key"]]["bucket"]
        for op in types_out[p["key"]]["answers"]:
            bucket_ops[b][op] += 1
        # also add other ops from that type's full counter
        for op, c in type_ops[p["key"]].most_common(15):
            bucket_ops[b][op] += c

    # Fold type-level easy fleets into bucket distractors
    for p in planes:
        if p["disabled"] or p["key"] not in types_out:
            continue
        b = types_out[p["key"]]["bucket"]
        for op in types_out[p["key"]].get("easy") or []:
            bucket_ops[b][op] += 5  # boost easy brands as distractors

    distractors = {}
    for b, ctr in bucket_ops.items():
        # Prefer easy fleets early in distractor lists, then frequent named
        ops = list(ctr.keys())
        ops.sort(key=lambda op: (0 if is_easy_fleet(op) else 1, -ctr[op], op.lower()))
        distractors[b] = ops[:80]
    any_ops = [op for op, c in global_ops.most_common(200) if c >= 2]
    any_ops.sort(key=lambda op: (0 if is_easy_fleet(op) else 1, -global_ops[op], op.lower()))
    distractors["any"] = any_ops[:120]

    # Only publish operators that appear in answers or distractor lists
    publish_ops = set()
    for t in types_out.values():
        publish_ops.update(t["answers"])
        publish_ops.update(t.get("easy") or [])
    for lst in distractors.values():
        publish_ops.update(lst)

    named_answer_types = sum(
        1 for t in types_out.values()
        if t["answers"] and operator_tier(t["answers"][0]) == "named"
    )
    payload = {
        "meta": {
            "note": "Compact operator/owner labels for Name That Jet bonus. Named owners/LLCs preferred as correct answers; easy fleet brands as distractors/fallback. Quiz types only — no full fleet dump, no raw CSV.",
            "typesCovered": len(types_out),
            "namedPreferredTypes": named_answer_types,
            "operatorsPublished": len(publish_ops),
            "question": "Who owns / operates this type?",
        },
        "types": types_out,
        "distractors": distractors,
    }

    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT} types={len(types_out)} ops={len(publish_ops)} bytes={OUT.stat().st_size}")
    print("\nCoverage:")
    for row in sorted(coverage, key=lambda x: -x[3]):
        key, n, top, cnt = row[0], row[1], row[2], row[3]
        named_n = row[4] if len(row) > 4 else "?"
        print(f"  {n:2d} ans ({named_n} named) top={cnt:4d}× {top[:40]:40s}  {key}")
    missing = [p["key"] for p in planes if not p["disabled"] and p["key"] not in types_out]
    print(f"\nNo coverage ({len(missing)}):")
    for k in missing:
        meta = type_meta.get(k, {})
        print(f"  {k}  models={meta.get('matchedModels', [])[:3]} ops={meta.get('usableOps')}")


if __name__ == "__main__":
    main()
