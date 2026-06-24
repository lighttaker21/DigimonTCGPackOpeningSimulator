# DigimonTCGPackOpeningSimulator
This is a simulator to open Digimon TCG packs, similar to YuGiOh Master Duel.
For more info visit the itch page for the project! https://melon-dev.itch.io/dcg-pack-opening-simulator

## Card art

No card art (binaries) is committed to this repo - Digimon TCG card art is
Bandai-owned IP, and binary images would also bloat repo size. Instead, card
art is fetched at runtime from the [digimon-card-app](https://github.com/lighttaker21/digimon-card-app)
project, which has real card art checked in at
`src/assets/images/cards/{CARD_ID}.webp`.

`Assets/_MainAssets/Scripts/CardImageLoader.cs` implements this: given a card
id (the `CardVariable` asset's own name, e.g. `BT17-001`), it downloads the
art from `raw.githubusercontent.com`, decodes it, and caches a PNG copy on
disk under `Application.persistentDataPath/CardImageCache/` so only the
first run per machine needs the network. It's wired into the existing
startup image-load flow in `TEMPLoadEveryImageStartup.cs` as a fallback when
no local file is found.

**Caveat:** digimon-card-app stores art as `.webp`, which Unity's built-in
image APIs cannot decode. WebP decoding is currently a documented blocker in
`CardImageLoader.cs` (throws a clear error rather than failing silently) -
see that file's header comment for the two recommended follow-ups (publish
PNG/JPG copies, or vendor a verified WebP decoder).
