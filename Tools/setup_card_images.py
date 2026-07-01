"""
setup_card_images.py — One-time (and re-runnable) card art setup for the Unity pack opener.

HOW IT WORKS
------------
digimon-card-app (https://github.com/lighttaker21/digimon-card-app) has all
Digimon TCG card art checked in as .webp files. Unity 2021.3.5f1 cannot decode
WebP, so this script converts those webp files to PNG on your local machine and
drops them into Assets/Images/ — the folder Unity's existing ImageGetData.cs
already knows how to load from.

Assets/Images/ is gitignored (no binaries go into git). This script is the only
thing you need to run before opening the project in Unity.

NOTE FOR NON-TECHNICAL USERS
-----------------------------
You don't need to run this yourself — just ask Claude to "run the card image
setup" (and "run the set sync" whenever digimon-card-app adds new sets) and it
will handle both. If you do want to run it manually, see USAGE below.

USAGE
-----
    # from the DigimonTCGPackOpeningSimulator repo root:
    python Tools/setup_card_images.py

    # if digimon-card-app is not in the default sibling location:
    python Tools/setup_card_images.py --card-app-path /path/to/digimon-card-app

    # dry run — see what would be converted without writing anything:
    python Tools/setup_card_images.py --dry-run

REQUIREMENTS
------------
    pip install pillow

The digimon-card-app repo must be cloned locally (a shallow clone is fine):
    git clone --depth 1 https://github.com/lighttaker21/digimon-card-app
"""

import argparse
import os
import re
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("ERROR: Pillow is not installed. Run:  pip install pillow")


def is_base_english_art(filename: str) -> bool:
    """Return True for base English art files (no -J, _P*, -Sample suffixes)."""
    stem = Path(filename).stem
    if stem.endswith("-J"):
        return False
    if re.search(r"_P\d+", stem):
        return False
    if "-Sample" in stem:
        return False
    return True


def convert_webp_to_png(webp_path: Path, png_path: Path, dry_run: bool) -> bool:
    if dry_run:
        print(f"  [dry-run] {webp_path.name} -> {png_path.name}")
        return True
    try:
        with Image.open(webp_path) as img:
            img.save(png_path, "PNG")
        return True
    except Exception as e:
        print(f"  ERROR converting {webp_path.name}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Convert digimon-card-app webp card art to PNG for Unity.")
    parser.add_argument(
        "--card-app-path",
        default=None,
        help="Path to local digimon-card-app clone. Defaults to ../digimon-card-app relative to this script.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print what would be done without writing files.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent  # DigimonTCGPackOpeningSimulator/
    card_app_root = Path(args.card_app_path).resolve() if args.card_app_path else (repo_root.parent / "digimon-card-app")

    webp_src = card_app_root / "src" / "assets" / "images" / "cards"
    png_dst = repo_root / "Assets" / "Images"

    if not webp_src.exists():
        sys.exit(
            f"ERROR: card art source not found at {webp_src}\n"
            f"Clone digimon-card-app first:\n"
            f"  git clone --depth 1 https://github.com/lighttaker21/digimon-card-app"
        )

    if not args.dry_run:
        png_dst.mkdir(parents=True, exist_ok=True)

    webp_files = [f for f in webp_src.iterdir() if f.suffix == ".webp" and is_base_english_art(f.name)]
    webp_files.sort()

    print(f"Source:      {webp_src}")
    print(f"Destination: {png_dst}")
    print(f"Cards found: {len(webp_files)}")
    if args.dry_run:
        print("(dry run — no files will be written)")
    print()

    converted = skipped = failed = 0
    for webp_path in webp_files:
        card_id = webp_path.stem  # e.g. "BT17-001"
        png_path = png_dst / f"{card_id}.png"

        if png_path.exists():
            skipped += 1
            continue

        if convert_webp_to_png(webp_path, png_path, args.dry_run):
            converted += 1
            if not args.dry_run:
                print(f"  converted: {card_id}")
        else:
            failed += 1

    print()
    print(f"Done.  converted={converted}  skipped(already exist)={skipped}  failed={failed}")
    if failed:
        print("Re-run the script to retry failed files.")


if __name__ == "__main__":
    main()
