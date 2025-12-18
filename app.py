from flask import Flask, render_template, jsonify, request, redirect, url_for
import json
import random
import os
import json



BASE_DIR = os.path.dirname(__file__)
CARDS_FILE = os.path.join(BASE_DIR, 'cards.json')
USER_FILE = os.path.join(BASE_DIR, 'user_data.json')

app = Flask(__name__)

# Ticket rewards for duplicates by rarity
TICKET_REWARDS = {
    'D': 1,
    'C': 4,
    'B': 20,
    'A': 50,
    'S': 150,
    'SS': 500,
    'SSS': 2000,
    'UR': 5000,
}

# Box definitions for shop (rarity -> label & ticket cost)
BOXES = {
    'UR': {'label': 'UR Box', 'cost': 10000},
    'SSS': {'label': 'SSS Box', 'cost': 4000},
    'SS': {'label': 'SS Box', 'cost': 1000},
    'S': {'label': 'S Box', 'cost': 300},
    'A': {'label': 'A Box', 'cost': 100},
    'B': {'label': 'B Box', 'cost': 40},
    'C': {'label': 'C Box', 'cost': 8},
    'D': {'label': 'D Box', 'cost': 3},
}


def load_cards():
    with open(CARDS_FILE, 'r', encoding='utf-8') as f:
        cards = json.load(f)

    # Ensure 10 cards have images assigned using files from static/public/cards
    assigned = [c for c in cards if c.get('image')]
    if len(assigned) < 10:
        cards_dir = os.path.join(BASE_DIR, 'static', 'public', 'cards')
        try:
            imgs = [fn for fn in os.listdir(cards_dir) if os.path.isfile(os.path.join(cards_dir, fn))]
        except Exception:
            imgs = []

        used_imgs = [os.path.basename(c['image']) for c in cards if c.get('image')]
        available_imgs = [i for i in imgs if i not in used_imgs]

        no_image_cards = [c for c in cards if not c.get('image')]
        needed = 10 - len(assigned)
        assign_count = min(needed, len(available_imgs), len(no_image_cards))
        if assign_count > 0:
            random.shuffle(available_imgs)
            selected_imgs = random.sample(available_imgs, assign_count)
            selected_cards = random.sample(no_image_cards, assign_count)
            for c, img in zip(selected_cards, selected_imgs):
                # store path relative to the `static` folder for url_for('static', filename=...)
                c['image'] = f'public/cards/{img}'

            # persist these assignments back to cards.json so they're stable
            with open(CARDS_FILE, 'w', encoding='utf-8') as f:
                json.dump(cards, f, indent=2, ensure_ascii=False)

    return cards


def load_user():
    if not os.path.exists(USER_FILE):
        with open(USER_FILE, 'w', encoding='utf-8') as f:
            json.dump({'coins': 900000, 'owned': [], 'tickets': 0}, f)
    with open(USER_FILE, 'r', encoding='utf-8') as f:
        user = json.load(f)
    # ensure tickets key exists for older users
    if 'tickets' not in user:
        user['tickets'] = 0
        with open(USER_FILE, 'w', encoding='utf-8') as f:
            json.dump(user, f, indent=2)
    return user


def save_user(user):
    try:
        with open(USER_FILE, 'w', encoding='utf-8') as f:
            json.dump(user, f, indent=2)
    except Exception as e:
        app.logger.exception("Failed to save user data")
        raise


def choose_rarity(pulls=1):
    probs = [
        ('D', 0.50),
        ('C', 0.25),
        ('B', 10),
        ('A', 1),
        ('S', 0.1),
        ('SS', 0.01),
        ('SSS', 0.001),
        ('UR', 0.0001),
    ]

    labels = [r for r, _ in probs]
    weights = [w for _, w in probs]

    return random.choices(labels, weights=weights, k=pulls)


def pick_cards_by_rarity(cards, rarity, count=1):
    pool = [c for c in cards if c['rarity'] == rarity]
    if not pool:
        # If there's no card for requested rarity, fallback to a card from the full pool.
        # This avoids IndexError and keeps pulls functional.
        return [random.choice(cards) for _ in range(count)]
    return [random.choice(pool) for _ in range(count)]


@app.route('/')
def lobby():
    user = load_user()
    return render_template('lobby.html', coins=user.get('coins', 0), tickets=user.get('tickets', 0))


@app.route('/gacha')
def gacha():
    user = load_user()
    return render_template('gacha.html', coins=user.get('coins', 0), tickets=user.get('tickets', 0))


@app.route('/pull', methods=['POST'])
def pull():
    data = request.json or {}
    count = int(data.get('count', 1))
    cost_per = 100
    total_cost = cost_per * count
    user = load_user()
    if user.get('coins', 0) < total_cost:
        return jsonify({'ok': False, 'error': 'Not enough coins'}), 400

    cards = load_cards()
    rarities = choose_rarity(count)
    results = []
    for r in rarities:
        picked = pick_cards_by_rarity(cards, r, 1)[0]
        picked_copy = dict(picked)
        # if the user already owns it, award tickets instead of giving duplicate card
        if picked['id'] in user.get('owned', []):
            tickets_awarded = TICKET_REWARDS.get(picked['rarity'].upper(), 0)
            user['tickets'] = user.get('tickets', 0) + tickets_awarded
            picked_copy['duplicate'] = True
            picked_copy['tickets_awarded'] = tickets_awarded
        else:
            user.setdefault('owned', []).append(picked['id'])
            picked_copy['duplicate'] = False
            picked_copy['tickets_awarded'] = 0
        results.append(picked_copy)

    # update user data (coins for pulling; tickets already adjusted for duplicates)
    user['coins'] -= total_cost
    try:
        save_user(user)
    except Exception as e:
        return jsonify({'ok': False, 'error': 'Failed to save user data', 'detail': str(e)}), 500
    return jsonify({'ok': True, 'results': results, 'coins': user['coins'], 'tickets': user.get('tickets', 0)})


@app.route('/deck')
def deck():
    cards = load_cards()
    user = load_user()
    owned = set(user.get('owned', []))
    # Group cards by rarity so the deck page shows rarities ordered from UR down to D
    # Define desired rarity order (top → bottom)
    rarity_order = ['UR', 'SSS', 'SS', 'S', 'A', 'B', 'C', 'D']
    grouped = []
    for r in rarity_order:
        group = [c for c in cards if c.get('rarity') == r]
        if group:
            grouped.append((r, group))
    return render_template('deck.html', grouped_cards=grouped, owned=owned, coins=user.get('coins', 0), tickets=user.get('tickets', 0))


@app.route('/shop')
def shop():
    user = load_user()
    # pass available boxes and tickets to the template
    return render_template('shop.html', coins=user.get('coins', 0), tickets=user.get('tickets', 0), boxes=BOXES)


@app.route('/buy', methods=['POST'])
def buy():
    data = request.json or {}
    # New shop: buy a box for a specific rarity using tickets
    rarity = data.get('rarity')
    user = load_user()
    cards = load_cards()
    if not rarity or rarity not in BOXES:
        return jsonify({'ok': False, 'error': 'Invalid box/rarity'}), 400

    cost = BOXES[rarity]['cost']
    if user.get('tickets', 0) < cost:
        return jsonify({'ok': False, 'error': 'Not enough tickets'}), 400

    # pick a card from the requested rarity that the user doesn't already own
    pool = [c for c in cards if c.get('rarity') == rarity and c['id'] not in user.get('owned', [])]
    if not pool:
        return jsonify({'ok': False, 'error': 'No unowned cards left in this rarity'}), 400

    card = random.choice(pool)
    user['tickets'] -= cost
    user.setdefault('owned', []).append(card['id'])
    try:
        save_user(user)
    except Exception as e:
        return jsonify({'ok': False, 'error': 'Failed to save user data', 'detail': str(e)}), 500
    return jsonify({'ok': True, 'card': card, 'tickets': user.get('tickets', 0)})


@app.route('/reset', methods=['POST'])
def reset():
    user = {'coins': 100000, 'owned': [], 'tickets': 0}
    try:
        save_user(user)
    except Exception as e:
        app.logger.exception("Failed to reset user data")
        return jsonify({'ok': False, 'error': 'Failed to save user data', 'detail': str(e)}), 500
    return jsonify({'ok': True})


if __name__ == '__main__':
    app.run(debug=True)
