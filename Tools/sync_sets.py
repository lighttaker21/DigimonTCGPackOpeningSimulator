#!/usr/bin/env python3
"""
sync_sets.py - Digimon TCG set/card sync tool

WHAT THIS DOES
---------------
This script keeps the Unity pack-opening-simulator's set data in sync with
the canonical Digimon card database maintained in the `digimon-card-app`
repo. It:

  1. Reads the canonical set order from
     `<digimon-card-app>/src/models/data/release-order.data.ts`
     (the `ReleaseOrder` array, newest set first).
  2. Reads the full card list from
     `<digimon-card-app>/src/assets/cardlists/PreparedDigimonCardsENG.json`.
  3. Looks at what sets already exist in this Unity project under
     `Assets/_MainAssets/ScriptableCreationFiles/SetFiles/` and
     `Assets/_MainAssets/ScriptableCreationFiles/CardFiles/`.
  4. For every set in ReleaseOrder that the Unity project does NOT yet have,
     generates:
       - `CardFiles/Files <SET>/<CARDNUMBER>.asset` (+ .meta) for every card
         in that set, using the same YAML structure/schema as existing
         `CardVariable` assets (see Assets/_MainAssets/Scripts/CardVariable.cs).
       - `SetFiles/Set<SET>.asset` (+ .meta) referencing all of that set's
         cards, using the same YAML structure as existing `CardSet` assets
         (see Assets/_MainAssets/Scripts/CardSet.cs).
     New GUIDs are generated fresh (random UUID4, hyphens stripped, lower-
     case hex - the exact format Unity itself uses) - existing GUIDs are
     never reused or altered.

  This script does NOT touch card art / Sprites. Newly generated
  CardVariable assets leave `cardImage: {fileID: 0}` (no image) and the
  generated SetFiles' `SetCover` points at the first card in the set as a
  placeholder. A `// TODO` style note is included in this docstring/README
  rather than in the YAML (Unity .asset files have no comment syntax), but
  see the printed summary at the end of a run for which sets still need
  card art imported manually.

  This script also does NOT add new sets to Master Packs / color packs /
  Secret Packs / Promo Packs - those are curated/themed collections and
  adding new cards to them is a deliberate design decision, not a
  mechanical sync.

HOW TO RUN
----------
    cd DigimonTCGPackOpeningSimulator
    python3 Tools/sync_sets.py [--card-app-path ../digimon-card-app] [--dry-run]

Defaults to a sibling checkout at `../digimon-card-app` relative to this
Unity repo's root. Use --dry-run to see what WOULD be generated without
writing any files. Use --only BT26,EX13 to restrict to specific set codes
(useful for processing one set at a time / reviewing diffs incrementally).

IMPORTANT - FOR THE PROJECT OWNER (non-technical users)
---------------------------------------------------------
You do not need to run this script yourself. Whenever digimon-card-app
publishes a new Digimon TCG set, just open a chat with Claude and ask:

    "Run the set sync"

Claude will pull the latest digimon-card-app data, run this script, review
the generated assets, and commit/push the result for you. There is no need
to learn Python or touch the command line.
"""

import argparse
import json
import os
import re
import sys
import uuid
from pathlib import Path


# ---------------------------------------------------------------------------
# Schema constants - mirror Assets/_MainAssets/Scripts/CardVariable.cs and
# Assets/_MainAssets/Scripts/CardSet.cs exactly. If those C# files change,
# update these tables to match.
# ---------------------------------------------------------------------------

CARDVARIABLE_SCRIPT_GUID = "3e146e65c551e2a4ca06e83ebab3f59f"
CARDSET_SCRIPT_GUID = "ba36c1ad7f18a824d848046070f9642f"

# CardVariable.CardRarity enum order
RARITY_MAP = {
    "C": 0,    # Common
    "U": 1,    # Uncommon
    "R": 2,    # Rare
    "SR": 3,   # SuperRare
    "SEC": 4,  # SecretRare
    "P": 5,    # Promo
    # "LimitedPack" (6) and "AlternateArt" (7) have no direct source-data
    # equivalent; UR ("Ultra Rare", used by some newer sets) maps to
    # SecretRare as the closest existing bucket.
    "UR": 4,
}

# CardVariable.CardColor / SecondCardColor enum order.
# NOTE: CardColor (color1) has no "None" entry (index 0 = Red), while
# SecondCardColor (color2) has "None" at index 0 then the same 7 colors
# shifted by one. We special-case color2 below.
COLOR1_MAP = {
    "Red": 0,
    "Blue": 1,
    "Yellow": 2,
    "Green": 3,
    "Black": 4,
    "Purple": 5,
    "White": 6,
}
COLOR2_MAP = {
    "None": 0,
    "Red": 1,
    "Blue": 2,
    "Yellow": 3,
    "Green": 4,
    "Black": 5,
    "Purple": 6,
    "White": 7,
}

# CardVariable.CardType (field name is "cardCatagory", a typo baked into the
# existing schema - preserved here for compatibility).
CARDTYPE_MAP = {
    "Digimon": 0,
    "Digi-Egg": 1,
    "Tamer": 2,
    "Option": 3,
    "Digimon/Option": 0,  # rare hybrid cards; treat as Digimon
}


def to_int(value, default=0):
    if value is None:
        return default
    s = str(value).strip()
    if s in ("", "-"):
        return default
    m = re.search(r"-?\d+", s)
    return int(m.group()) if m else default


def gen_guid():
    """Generate a fresh Unity-style GUID: 32 lowercase hex chars, no dashes."""
    return uuid.uuid4().hex


# ---------------------------------------------------------------------------
# digimon-card-app readers
# ---------------------------------------------------------------------------

def read_release_order(card_app_path: Path):
    ts_path = card_app_path / "src" / "models" / "data" / "release-order.data.ts"
    text = ts_path.read_text(encoding="utf-8")
    m = re.search(r"ReleaseOrder\s*[:=].*?\[(.*?)\]", text, re.S)
    if not m:
        raise RuntimeError(f"Could not find ReleaseOrder array in {ts_path}")
    body = m.group(1)
    codes = re.findall(r"['\"]([A-Za-z0-9]+)['\"]", body)
    return codes


def read_card_data(card_app_path: Path):
    json_path = card_app_path / "src" / "assets" / "cardlists" / "PreparedDigimonCardsENG.json"
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


def normalize_set_code(code: str) -> str:
    """digimon-card-app's release-order.data.ts uses zero-padded codes for
    some EX sets (EX05, EX06, EX07, EX09) while the actual cardNumber
    prefixes in the card-list JSON are NOT zero-padded (EX5, EX6, EX7, EX9).
    Strip a single leading zero from the numeric part so set lookups match
    the real card data. Unity's own asset naming also has no zero-padding
    (e.g. "EX5", not "EX05"), so this normalized form is what gets used for
    Unity file/folder names too."""
    m = re.match(r"^([A-Za-z]+)0*(\d+)$", code)
    if not m:
        return code
    return f"{m.group(1)}{m.group(2)}"


def cards_for_set(all_cards, set_code):
    """Return cards belonging to `set_code`, sorted by card number, de-duped
    by base card number (skip parallel/alt-art variants like BT23-001_P1)."""
    prefix = normalize_set_code(set_code) + "-"
    matches = [c for c in all_cards if str(c.get("cardNumber", "")).startswith(prefix)]
    seen = {}
    for c in matches:
        num = str(c.get("cardNumber", ""))
        base = num.split("_")[0]
        if base not in seen:
            seen[base] = c
    def sort_key(c):
        n = str(c.get("cardNumber", "")).split("_")[0]
        m = re.search(r"-(\d+)", n)
        return int(m.group(1)) if m else 0
    return sorted(seen.values(), key=sort_key)


# ---------------------------------------------------------------------------
# Unity project inspection
# ---------------------------------------------------------------------------

# A handful of existing Unity sets use legacy/non-standard folder or file
# names that don't match the "Set<CODE>" / "Files <CODE>" convention used
# everywhere else. Map those onto the set code they actually represent so
# the sync tool doesn't try to regenerate them.
LEGACY_SET_ALIASES = {
    "RB1": "RB Cards",  # SetRebootBooster1.asset / "Files RB Cards"
}


def existing_set_codes(unity_root: Path):
    """Best-effort detection of which ReleaseOrder set codes already have
    Unity assets, by checking for a CardFiles/Files <CODE> directory or a
    SetFiles/Set<CODE>.asset file."""
    set_files = unity_root / "Assets/_MainAssets/ScriptableCreationFiles/SetFiles"
    card_files = unity_root / "Assets/_MainAssets/ScriptableCreationFiles/CardFiles"
    starter_files = unity_root / "Assets/_MainAssets/ScriptableCreationFiles/Starter Deck Files"

    existing = set()
    if set_files.exists():
        for p in set_files.glob("Set*.asset"):
            existing.add(p.stem[len("Set"):])
    if card_files.exists():
        for p in card_files.glob("Files *"):
            code = p.name[len("Files "):].strip()
            existing.add(code)
    if starter_files.exists():
        for p in starter_files.glob("*.asset"):
            existing.add(p.stem)
    for canonical_code, legacy_folder in LEGACY_SET_ALIASES.items():
        if (card_files / f"Files {legacy_folder}").exists():
            existing.add(canonical_code)
    return existing


# ---------------------------------------------------------------------------
# Asset generation
# ---------------------------------------------------------------------------

CARDVARIABLE_TEMPLATE = """%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!114 &11400000
MonoBehaviour:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  m_GameObject: {{fileID: 0}}
  m_Enabled: 1
  m_EditorHideFlags: 0
  m_Script: {{fileID: 11500000, guid: {script_guid}, type: 3}}
  m_Name: {name}
  m_EditorClassIdentifier: 
  cardImage: {{fileID: 0}}
  setNumber: {set_number}
  CardName: {card_name}
  hasAnAltArt: 0
  rarity: {rarity}
  secretPackRarity: 0
  color1: {color1}
  color2: {color2}
  cardCatagory: {card_type}
  playCost: {play_cost}
  DPOfCard: {dp}
  cardLevel: {level}
  secretPackToUnlock: []
  amountOwned: 0
  amountInCurrentDeck: 0
"""

META_TEMPLATE = """fileFormatVersion: 2
guid: {guid}
NativeFormatImporter:
  externalObjects: {{}}
  mainObjectFileID: 11400000
  userData: 
  assetBundleName: 
  assetBundleVariant: 
"""

CARDSET_TEMPLATE_HEADER = """%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!114 &11400000
MonoBehaviour:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  m_GameObject: {{fileID: 0}}
  m_Enabled: 1
  m_EditorHideFlags: 0
  m_Script: {{fileID: 11500000, guid: {script_guid}, type: 3}}
  m_Name: {name}
  m_EditorClassIdentifier: 
  ListOfCardsInSet:
"""

CARDSET_TEMPLATE_FOOTER = """  SetName: {set_name}
  SetDescription: 
  SetCover: {{fileID: 11400000, guid: {cover_guid}, type: 2}}
  SecretPack: 0
  PromoPack: 0
  hasBeenUnlocked: 0
  hasBeenCompleted: 0
  isRebootBooster: 0
  KeyCards: []
"""


def yaml_quote(s: str) -> str:
    s = "" if s is None else str(s)
    if s == "":
        return ""
    if re.search(r'^[\'"\[\]{}#&*!|>%@`,]|:\s|\s#', s) or s.strip() != s:
        return "'" + s.replace("'", "''") + "'"
    return s


def build_card_yaml(set_code: str, card: dict):
    card_number = str(card.get("cardNumber") or card.get("id") or "").split("_")[0]
    name = card.get("name", {}).get("english") or "Unknown"
    set_number = to_int(re.search(r"-(\d+)", card_number).group(1)) if re.search(r"-(\d+)", card_number) else 0

    rarity_code = (card.get("rarity") or "C").strip()
    rarity = RARITY_MAP.get(rarity_code, 0)

    color_field = card.get("color") or "Red"
    colors = [c.strip() for c in str(color_field).split("/") if c.strip()]
    color1_name = colors[0] if colors else "Red"
    color2_name = colors[1] if len(colors) > 1 else "None"
    color1 = COLOR1_MAP.get(color1_name, 0)
    color2 = COLOR2_MAP.get(color2_name, 0)

    card_type = CARDTYPE_MAP.get(card.get("cardType") or "Digimon", 0)
    play_cost = to_int(card.get("playCost"), 0)
    dp = to_int(card.get("dp"), 0)
    level_str = str(card.get("cardLv") or "")
    lvl_m = re.search(r"(\d+)", level_str)
    level = int(lvl_m.group(1)) if lvl_m else 0

    yaml_text = CARDVARIABLE_TEMPLATE.format(
        script_guid=CARDVARIABLE_SCRIPT_GUID,
        name=card_number,
        set_number=set_number,
        card_name=yaml_quote(name),
        rarity=rarity,
        color1=color1,
        color2=color2,
        card_type=card_type,
        play_cost=play_cost,
        dp=dp,
        level=level,
    )
    return card_number, yaml_text


def build_set_yaml(set_code: str, set_display_name: str, card_guids: list, cover_guid: str):
    header = CARDSET_TEMPLATE_HEADER.format(script_guid=CARDSET_SCRIPT_GUID, name=f"Set{set_code}")
    body_lines = [f"  - {{fileID: 11400000, guid: {g}, type: 2}}" for g in card_guids]
    footer = CARDSET_TEMPLATE_FOOTER.format(
        set_name=yaml_quote(set_display_name),
        cover_guid=cover_guid,
    )
    return header + "\n".join(body_lines) + "\n" + footer


def write_asset(path: Path, yaml_text: str, guid: str, dry_run: bool):
    if dry_run:
        print(f"  [dry-run] would write {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml_text, encoding="utf-8", newline="\n")
    meta_path = Path(str(path) + ".meta")
    meta_path.write_text(META_TEMPLATE.format(guid=guid), encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser(description="Sync Unity set/card assets from digimon-card-app.")
    parser.add_argument("--card-app-path", default=None,
                         help="Path to digimon-card-app checkout (default: ../digimon-card-app relative to this Unity repo)")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be generated without writing files")
    parser.add_argument("--only", default=None, help="Comma-separated set codes to restrict processing to (e.g. BT26,EX13)")
    args = parser.parse_args()

    unity_root = Path(__file__).resolve().parent.parent
    card_app_path = Path(args.card_app_path) if args.card_app_path else (unity_root.parent / "digimon-card-app")

    if not card_app_path.exists():
        print(f"ERROR: digimon-card-app checkout not found at {card_app_path}", file=sys.stderr)
        sys.exit(1)

    release_order = read_release_order(card_app_path)
    all_cards = read_card_data(card_app_path)
    existing = existing_set_codes(unity_root)

    missing = [code for code in release_order if code not in existing]
    if args.only:
        wanted = set(s.strip() for s in args.only.split(","))
        missing = [code for code in missing if code in wanted]

    print(f"ReleaseOrder has {len(release_order)} sets. Unity project already has {len(existing)} matched codes.")
    print(f"Missing sets to generate this run: {missing}")

    set_files_dir = unity_root / "Assets/_MainAssets/ScriptableCreationFiles/SetFiles"
    card_files_dir = unity_root / "Assets/_MainAssets/ScriptableCreationFiles/CardFiles"

    summary_no_art = []

    for raw_code in missing:
        set_code = normalize_set_code(raw_code)
        cards = cards_for_set(all_cards, raw_code)
        if not cards:
            print(f"  SKIP {raw_code}: no card data found in digimon-card-app for this set code.")
            continue
        if set_code in existing_set_codes(unity_root):
            print(f"  SKIP {raw_code}: normalizes to {set_code}, which already exists in Unity.")
            continue

        print(f"  Generating {raw_code} -> Unity code {set_code}: {len(cards)} cards")
        card_guids = []
        set_dir = card_files_dir / f"Files {set_code}"
        for card in cards:
            card_number, yaml_text = build_card_yaml(set_code, card)
            guid = gen_guid()
            asset_path = set_dir / f"{card_number}.asset"
            write_asset(asset_path, yaml_text, guid, args.dry_run)
            card_guids.append(guid)

        notes = cards[0].get("notes") or ""
        set_display_name = f"[{set_code}] {notes}" if notes and notes != "-" else set_code
        set_yaml = build_set_yaml(set_code, set_display_name, card_guids, card_guids[0] if card_guids else "0" * 32)
        set_guid = gen_guid()
        set_asset_path = set_files_dir / f"Set{set_code}.asset"
        write_asset(set_asset_path, set_yaml, set_guid, args.dry_run)

        summary_no_art.append(set_code)

    print()
    print("Done.")
    if summary_no_art:
        print("Card art was NOT imported for the following newly generated sets")
        print("(cardImage is left empty - fileID: 0). Import artwork separately:")
        for code in summary_no_art:
            print(f"  // TODO: card art not yet imported for set {code}")


if __name__ == "__main__":
    main()
