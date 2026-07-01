# DigimonTCGPackOpeningSimulator
This is a simulator to open Digimon TCG packs, similar to YuGiOh Master Duel.
For more info visit the itch page for the project! https://melon-dev.itch.io/dcg-pack-opening-simulator

## How to run

1. **Install Unity Hub** from https://unity.com/download, then install Unity Editor **2021.3.5f1** (Unity Hub will offer to install the right version automatically when you open the project).

2. **Clone this repo** (branch `claude/quirky-lamport-s1vlvi`) and also clone [digimon-card-app](https://github.com/lighttaker21/digimon-card-app) **as a sibling folder** next to it:
   ```
   git clone --depth 1 https://github.com/lighttaker21/digimon-card-app
   git clone https://github.com/lighttaker21/DigimonTCGPackOpeningSimulator
   cd DigimonTCGPackOpeningSimulator
   git checkout claude/quirky-lamport-s1vlvi
   ```
   Your folder layout should look like:
   ```
   /some-folder/
     digimon-card-app/
     DigimonTCGPackOpeningSimulator/
   ```

3. **Convert card images** (one-time setup — requires Python 3 and Pillow):
   ```
   pip install pillow
   python Tools/setup_card_images.py
   ```
   This converts ~4,300 card art files from digimon-card-app's webp format to PNG and places them in `Assets/Images/` locally (not committed to git). Takes a minute or two. Re-run it whenever new sets are added.

4. **Open the project in Unity Hub** — point it at the `DigimonTCGPackOpeningSimulator` folder. Hit Play.

## Keeping sets up to date

When digimon-card-app adds new sets (it updates automatically every few days from the Digimon Card Game Wiki), just ask Claude to:
- **"Run the set sync"** — adds new set/card data to the Unity project via `Tools/sync_sets.py`
- **"Run the card image setup"** — converts any new card art via `Tools/setup_card_images.py`

## Card art

No card art binaries are committed to this repo (Bandai-owned IP + repo size). Instead, `Tools/setup_card_images.py` converts card art from a local [digimon-card-app](https://github.com/lighttaker21/digimon-card-app) clone into `Assets/Images/` on your machine. Unity's existing `ImageGetData.cs` loads from there at startup; `CardImageLoader.cs` is a network fallback for any cards not yet converted locally.
