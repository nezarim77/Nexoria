from flask import (
    Flask, render_template, jsonify, request,
    redirect, url_for, send_from_directory, make_response
)
from itsdangerous import URLSafeSerializer
import json
import random
import os
import uuid

# ======================================================
# BASIC SETUP
# ======================================================

BASE_DIR = os.path.dirname(__file__)
CARDS_FILE = os.path.join(BASE_DIR, 'cards.json')

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'nexoria-secret-key')

serializer = URLSafeSerializer(app.secret_key, salt="user-data")

# ======================================================
# USER (COOKIE BASED – VERCEL SAFE)
# ======================================================

DEFAULT_USER = {
    "coins": 100000,
    "owned": [],
    "tickets": 0
}

def get_user():
    uid = request.cookies.get('uid')
    data = request.cookies.get('user_data')

    if uid and data:
        try:
            user = serializer.loads(data)
            return uid, user
        except Exception:
            pass

    # user baru
    uid = uuid.uuid4().hex
    return uid, DEFAULT_USER.copy()

def save_user_response(resp, uid, user):
    resp.set_cookie(
        'uid',
        uid,
        max_age=60 * 60 * 24 * 365 * 5,
        httponly=True,
        samesite='Lax'
    )
    resp.set_cookie(
        'user_data',
        serializer.dumps(user),
        max_age=60 * 60 * 24 * 365 * 5,
        httponly=True,
        samesite='Lax'
    )
    return resp

# ======================================================
# CONSTANTS
# ======================================================

TICKET_REWARDS = {
    'D': 0,
    'C': 0,
    'B': 50,
    'A': 100,
    'S': 300,
    'SS': 1000,
    'SSS': 4000,
    'UR': 10000,
}

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
            for c, img in zip(
                random.sample(no_image_cards, assign_count),
                random.sample(available_imgs, assign_count)
            ):
                c['image'] = f'public/cards/{img}'

    return cards

# ======================================================
# GACHA LOGIC
# ======================================================

def choose_rarity(pulls=1):
    probs = [
        ('D', 0),
        ('C', 0),
        ('B', 65),
        ('A', 25),
        ('S', 5),
        ('SS', 1),
        ('SSS', 0.1),
        ('UR', 0.01),
    ]
    labels = [r for r, _ in probs]
    weights = [w for _, w in probs]
    return random.choices(labels, weights=weights, k=pulls)

def pick_cards_by_rarity(cards, rarity):
    pool = [c for c in cards if c['rarity'] == rarity]
    return random.choice(pool if pool else cards)

# ======================================================
# ROUTES
# ======================================================

@app.route('/')
def lobby():
    uid, user = get_user()
    resp = make_response(render_template(
        'lobby.html',
        coins=user['coins'],
        tickets=user['tickets']
    ))
    return save_user_response(resp, uid, user)

@app.route('/gacha')
def gacha():
    uid, user = get_user()
    resp = make_response(render_template(
        'gacha.html',
        coins=user['coins'],
        tickets=user['tickets']
    ))
    return save_user_response(resp, uid, user)

@app.route('/deck')
def deck():
    uid, user = get_user()
    cards = load_cards()
    owned = set(user['owned'])

    rarity_order = ['UR', 'SSS', 'SS', 'S', 'A', 'B', 'C', 'D']
    grouped = [(r, [c for c in cards if c['rarity'] == r]) for r in rarity_order]

    resp = make_response(render_template(
        'deck.html',
        grouped_cards=grouped,
        owned=owned,
        coins=user['coins'],
        tickets=user['tickets']
    ))
    return save_user_response(resp, uid, user)

@app.route('/shop')
def shop():
    uid, user = get_user()
    resp = make_response(render_template(
        'shop.html',
        coins=user['coins'],
        tickets=user['tickets'],
        boxes=BOXES
    ))
    return save_user_response(resp, uid, user)

@app.route('/pull', methods=['POST'])
def pull():
    data = request.json or {}
    count = int(data.get('count', 1))
    total_cost = count * 100

    uid, user = get_user()

    if user['coins'] < total_cost:
        return jsonify({'ok': False, 'error': 'Not enough coins'}), 400

    cards = load_cards()
    results = []

    for r in choose_rarity(count):
        card = pick_cards_by_rarity(cards, r)
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

    resp = jsonify({
        'ok': True,
        'results': results,
        'coins': user['coins'],
        'tickets': user['tickets']
    })
    return save_user_response(resp, uid, user)

@app.route('/buy', methods=['POST'])
def buy():
    data = request.json or {}
    rarity = data.get('rarity')

    if rarity not in BOXES:
        return jsonify({'ok': False, 'error': 'Invalid rarity'}), 400

    uid, user = get_user()
    cost = BOXES[rarity]['cost']

    if user['tickets'] < cost:
        return jsonify({'ok': False, 'error': 'Not enough tickets'}), 400

    cards = load_cards()
    pool = [c for c in cards if c['rarity'] == rarity and c['id'] not in user['owned']]

    if not pool:
        return jsonify({'ok': False, 'error': 'No unowned cards left'}), 400

    card = random.choice(pool)
    user['tickets'] -= cost
    user['owned'].append(card['id'])

    resp = jsonify({
        'ok': True,
        'card': card,
        'tickets': user['tickets']
    })
    return save_user_response(resp, uid, user)

@app.route('/reset', methods=['POST'])
def reset():
    data = request.json or {}
    if data.get('confirm') is not True:
        return jsonify({'ok': False}), 400

    uid = request.cookies.get('uid') or uuid.uuid4().hex
    user = DEFAULT_USER.copy()

    resp = jsonify({'ok': True})
    return save_user_response(resp, uid, user)

# ======================================================
# STATIC
# ======================================================

@app.route('/static/public/assets/<path:filename>')
def public_asset(filename):
    assets_dir = os.path.join(BASE_DIR, 'static', 'public', 'assets')
    return send_from_directory(assets_dir, filename)

# ======================================================
# LOCAL DEV
# ======================================================

if __name__ == '__main__':
    app.run(debug=True)
