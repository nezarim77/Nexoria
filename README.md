# Nexoria — Gacha Card Web Game (Python + Flask)

Simple local web-based gacha card game prototype named "Nexoria".

Features implemented:
- Lobby with menu: Gacha, Deck, Shop, Reset
- Gacha page: pull 1x or 10x (uses dummy card assets)
- Deck page: shows 20 dummy cards; unknown cards shown as question marks
- Shop page: buy a box to get a card (uses coins)
- Reset: reset user data to start over

Quick start (Windows PowerShell):

```powershell
python -m pip install -r requirements.txt
python app.py

# open http://127.0.0.1:5000 in your browser
```

Notes:
- I used a simple JSON file for persistence (`user_data.json`).
- Card images are placeholders; you can replace them later by putting images and updating `cards.json`.

Next steps (I can do on request):
- Add real card art assets and thumbnails
- Improve gacha probabilities, pity, animations
- Add login/multi-user support with a database
