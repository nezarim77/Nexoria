from flask import Flask, render_template, jsonify, request, redirect, url_for, send_from_directory
import json
import random
import os

BASE_DIR = os.path.dirname(__file__)
CARDS_FILE = os.path.join(BASE_DIR, 'cards.json')
USER_FILE = os.path.join(BASE_DIR, 'user_data.json')

app = Flask(__name__)

# ======================================================
# CONSTANTS
# ======================================================

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

# ======================================================
# LOAD CARDS (READ ONLY)
# ======================================================
def load_cards():
    with open(CARDS_FILE, 'r', encoding='utf-8') as f:
        cards = json.load(f)

    assigned = [c for c in cards if c.get('image')]
    if len(assigned) < 10:
        cards_dir = os.path.join(BASE_DIR, 'static', 'public', 'cards')
        try:
            imgs = [
                fn for fn in os.listdir(cards_dir)
                if os.path.isfile(os.path.join(cards_dir, fn))
            ]
        except Exception:
            imgs = []

        used_imgs = [
            os.path.basename(c['image'])
            for c in cards if c.get('image')
        ]
        available_imgs = [i for i in imgs if i not in used_imgs]
        no_image_cards = [c for c in cards if not c.get('image')]

        needed = 10 - len(assigned)
        assign_count = min(needed, len(available_imgs), len(no_image_cards))

        if assign_count > 0:
            random.shuffle(available_imgs)
            selected_imgs = random.sample(available_imgs, assign_count)
            selected_cards = random.sample(no_image_cards, assign_count)

            for c, img in zip(selected_cards, selected_imgs):
                c['image'] = f'public/cards/{img}'
            # ❌ TIDAK DISIMPAN KE FILE

    return cards

# ======================================================
# USER (FILE BASED)
# ======================================================
def load_user():
    try:
        if not os.path.exists(USER_FILE):
            initial_user = {"coins": 100000, "owned": [], "tickets": 0}
            try:
                with open(USER_FILE, 'w', encoding='utf-8') as f:
                    json.dump(initial_user, f, indent=2)
            except Exception as e:
                app.logger.warning('Could not write initial user_data.json: %s; using in-memory copy', e)
            return initial_user
        with open(USER_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        app.logger.exception('Failed to load user data; returning default')
        return {"coins": 100000, "owned": [], "tickets": 0}

def save_user(user):
    try:
        with open(USER_FILE, 'w', encoding='utf-8') as f:
            json.dump(user, f, indent=2)
    except Exception as e:
        app.logger.warning('Could not save user_data.json: %s', e)

# ======================================================
# GACHA LOGIC
# ======================================================
def choose_rarity(pulls=1):
    probs = [
        ('D', 50),
        ('C', 25),
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
        return [random.choice(cards) for _ in range(count)]
    return [random.choice(pool) for _ in range(count)]

# ======================================================
# ROUTES
# ======================================================
@app.route('/')
def lobby():
    user = load_user()
    return render_template(
        'lobby.html',
        coins=user.get('coins', 0),
        tickets=user.get('tickets', 0)
    )

@app.route('/gacha')
def gacha():
    user = load_user()
    return render_template(
        'gacha.html',
        coins=user.get('coins', 0),
        tickets=user.get('tickets', 0)
    )

@app.route('/pull', methods=['POST'])
def pull():
    data = request.json or {}
    count = int(data.get('count', 1))
    cost_per = 100
    total_cost = cost_per * count

    user = load_user()
    if user['coins'] < total_cost:
        return jsonify({'ok': False, 'error': 'Not enough coins'}), 400

    cards = load_cards()
    rarities = choose_rarity(count)
    results = []

    for r in rarities:
        card = pick_cards_by_rarity(cards, r, 1)[0]
        result = dict(card)

        if card['id'] in user['owned']:
            reward = TICKET_REWARDS.get(card['rarity'], 0)
            user['tickets'] += reward
            result['duplicate'] = True
            result['tickets_awarded'] = reward
        else:
            user['owned'].append(card['id'])
            result['duplicate'] = False
            result['tickets_awarded'] = 0

        results.append(result)

    user['coins'] -= total_cost
    save_user(user)

    return jsonify({
        'ok': True,
        'results': results,
        'coins': user['coins'],
        'tickets': user['tickets']
    })

@app.route('/deck')
def deck():
    cards = load_cards()
    user = load_user()
    owned = set(user['owned'])

    rarity_order = ['UR', 'SSS', 'SS', 'S', 'A', 'B', 'C', 'D']
    grouped = []

    for r in rarity_order:
        group = [c for c in cards if c['rarity'] == r]
        if group:
            grouped.append((r, group))

    return render_template(
        'deck.html',
        grouped_cards=grouped,
        owned=owned,
        coins=user['coins'],
        tickets=user['tickets']
    )

@app.route('/shop')
def shop():
    user = load_user()
    return render_template(
        'shop.html',
        coins=user['coins'],
        tickets=user['tickets'],
        boxes=BOXES
    )

@app.route('/buy', methods=['POST'])
def buy():
    data = request.json or {}
    rarity = data.get('rarity')

    if rarity not in BOXES:
        return jsonify({'ok': False, 'error': 'Invalid rarity'}), 400

    user = load_user()
    cost = BOXES[rarity]['cost']

    if user['tickets'] < cost:
        return jsonify({'ok': False, 'error': 'Not enough tickets'}), 400

    cards = load_cards()
    pool = [
        c for c in cards
        if c['rarity'] == rarity and c['id'] not in user['owned']
    ]

    if not pool:
        return jsonify({'ok': False, 'error': 'No unowned cards left'}), 400

    card = random.choice(pool)
    user['tickets'] -= cost
    user['owned'].append(card['id'])
    save_user(user)

    return jsonify({
        'ok': True,
        'card': card,
        'tickets': user['tickets']
    })

@app.route('/reset', methods=['POST'])
def reset():
    # require explicit JSON confirmation to avoid accidental resets
    data = request.get_json(silent=True) or {}
    app.logger.info('Reset called: remote=%s referrer=%s user_agent=%s data=%s', request.remote_addr, request.referrer, request.headers.get('User-Agent'), data)
    if data.get('confirm') is not True:
        return jsonify({'ok': False, 'error': 'Missing confirmation'}), 400

    user = {
        "coins": 100000,
        "owned": [],
        "tickets": 0
    }
    try:
        save_user(user)
    except Exception as e:
        app.logger.exception("Failed to reset user data")
        return jsonify({'ok': False, 'error': 'Failed to save user data', 'detail': str(e)}), 500
    return jsonify({'ok': True})

# ======================================================
# STATIC & DEBUG
# ======================================================
@app.route('/static/public/assets/<path:filename>')
def public_asset(filename):
    assets_dir = os.path.join(BASE_DIR, 'static', 'public', 'assets')
    return send_from_directory(assets_dir, filename)

@app.route('/_debug/fs')
def debug_fs():
    return jsonify({
        "ok": True,
        "base_dir": BASE_DIR,
        "cards_json_exists": os.path.exists(CARDS_FILE),
        "user_cache": USER_CACHE
    })

if __name__ == '__main__':
    app.run(debug=True)
