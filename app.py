from flask import Flask, render_template, jsonify, request, redirect, url_for, send_from_directory
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
            try:
                with open(CARDS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(cards, f, indent=2, ensure_ascii=False)
            except Exception:
                # On serverless platforms writing to disk may fail; log and continue without persisting
                app.logger.exception("Failed to persist card image assignments; continuing without saving")

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

    try:
        cards = load_cards()
    except Exception as e:
        app.logger.exception('Failed to load cards during pull')
        return jsonify({'ok': False, 'error': 'Failed to load cards', 'detail': str(e)}), 500

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


# Serve assets explicitly for hosting environments that don't expose Flask's static folder
@app.route('/static/public/assets/<path:filename>')
def public_asset(filename):
    assets_dir = os.path.join(BASE_DIR, 'static', 'public', 'assets')
    try:
        # Log basic context
        app.logger.info('public_asset request: %s ; assets_dir=%s', filename, assets_dir)
        if not os.path.isdir(assets_dir):
            app.logger.error('Assets dir missing: %s', assets_dir)
            return ('', 404)
        file_path = os.path.join(assets_dir, filename)
        exists = os.path.exists(file_path)
        app.logger.info('Requested file path: %s ; exists=%s', file_path, exists)
        if not exists:
            try:
                listing = os.listdir(assets_dir)
                app.logger.error('Assets dir listing: %s', listing)
            except Exception:
                app.logger.exception('Failed to list assets dir')
            return ('', 404)
        return send_from_directory(assets_dir, filename)
    except Exception:
        app.logger.exception('Failed to serve public asset: %s', filename)
        return ('', 404)


@app.route('/_debug/fs', methods=['GET'])
def debug_fs():
    """Diagnostic endpoint: reports presence and read status of key files and folders."""
    try:
        assets_dir = os.path.join(BASE_DIR, 'static', 'public', 'assets')
        checks = {
            'cwd': os.getcwd(),
            'base_dir': BASE_DIR,
            'assets_dir_exists': os.path.isdir(assets_dir),
            'assets_listing': None,
            'cards_json_exists': os.path.exists(CARDS_FILE),
            'cards_read_error': None,
            'user_json_exists': os.path.exists(USER_FILE),
            'user_read_error': None,
        }
        try:
            if os.path.isdir(assets_dir):
                checks['assets_listing'] = os.listdir(assets_dir)
        except Exception as e:
            checks['assets_listing'] = f'error: {e}'
        try:
            if checks['cards_json_exists']:
                with open(CARDS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        checks['cards_sample'] = data[:3]
                    else:
                        checks['cards_sample'] = 'not a list'
        except Exception as e:
            checks['cards_read_error'] = str(e)
        try:
            if checks['user_json_exists']:
                with open(USER_FILE, 'r', encoding='utf-8') as f:
                    checks['user'] = json.load(f)
        except Exception as e:
            checks['user_read_error'] = str(e)

        return jsonify({'ok': True, 'checks': checks})
    except Exception:
        app.logger.exception('Debug FS failed')
        return jsonify({'ok': False, 'error': 'debug failed'}), 500


@app.route('/_debug/fs-write', methods=['POST'])
def debug_fs_write():
    """Diagnostic endpoint: tests whether the process can write to disk."""
    testfile = os.path.join(BASE_DIR, 'tmp_test_write.txt')
    try:
        with open(testfile, 'w', encoding='utf-8') as f:
            f.write('ok')
        os.remove(testfile)
        return jsonify({'ok': True, 'write_ok': True})
    except Exception as e:
        app.logger.exception('FS write test failed')
        return jsonify({'ok': False, 'write_error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
