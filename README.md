# DigimonTCGPackOpeningSimulator
This is a simulator to open Digimon TCG packs, similar to YuGiOh Master Duel.
For more info visit the itch page for the project! https://melon-dev.itch.io/dcg-pack-opening-simulator

## Card art

No card art (binaries) is committed to this repo - Digimon TCG card art is
Bandai-owned IP, and binary images would also bloat repo size. Instead, card
art is fetched at runtime from the [digimon-card-app](https://github.com/lighttaker21/digimon-card-app)
project, which has real card art checked in at
`src/assets/images/cards/{CARD_ID}.webp`, and (since digimon-card-app commit
`903797c9`) a parallel raw-PNG export at
`src/assets/images/cards-png/{CARD_ID}.png` for non-webp consumers like this
project.

`Assets/_MainAssets/Scripts/CardImageLoader.cs` implements this: given a card
id (the `CardVariable` asset's own name, e.g. `BT17-001`), it downloads the
PNG art from `raw.githubusercontent.com` and caches a copy on disk under
`Application.persistentDataPath/CardImageCache/` so only the first run per
machine needs the network. It's wired into the existing startup image-load
flow in `TEMPLoadEveryImageStartup.cs` as a fallback when no local file is
found.

**Caveat:** the PNG export only exists for cards (re-)scraped by
digimon-card-app after commit `903797c9`. Cards whose wiki scrape predates
that commit won't have a `cards-png/{id}.png` file until digimon-card-app's
next scheduled refresh (its GitHub Action runs every 3 days, or can be
triggered manually) re-downloads them - until then, art for those specific
cards will fail to load and log an error.
