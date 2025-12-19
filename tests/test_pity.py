#!/usr/bin/env python3
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app, serializer
import json


def make_user_cookie(client, data):
    # set uid and user_data cookies for test client via base environ (works in this test env)
    uid = 'testuser'
    ud = serializer.dumps(data)
    # attempt to use the test client's set_cookie API; fallback to environ if signature differs
    try:
        client.set_cookie('uid', uid)
        client.set_cookie('user_data', ud)
    except TypeError:
        client.environ_base['HTTP_COOKIE'] = f'uid={uid}; user_data="{ud}"'
    return uid


if __name__ == '__main__':
    with app.test_client() as client:
        print('== test: guarantee SSS when pity_sss>=200')
        user = {"coins":100000, "owned":[], "tickets":0, "pity_sss":200, "pity_ur":0}
        make_user_cookie(client, user)

        r = client.post('/pull', json={'count': 1})
        j = r.get_json()
        print('response:', json.dumps(j, indent=2))
        assert r.status_code == 200
        assert j['ok']
        # SSS from pity should be an unowned card (not a duplicate)
        assert any(c['rarity'] == 'SSS' and not c.get('duplicate', False) for c in j['results']), 'Expected at least one unowned SSS from pity'
        assert j['pity_sss'] == 0

        print('== test: guarantee UR when pity_ur>=500')
        user = {"coins":100000, "owned":[], "tickets":0, "pity_sss":0, "pity_ur":500}
        make_user_cookie(client, user)

        r = client.post('/pull', json={'count': 1})
        j = r.get_json()
        print('response:', json.dumps(j, indent=2))
        assert r.status_code == 200
        assert j['ok']
        # UR from pity should be an unowned card (not a duplicate)
        assert any(c['rarity'] == 'UR' and not c.get('duplicate', False) for c in j['results']), 'Expected unowned UR from pity'
        assert j['pity_ur'] == 0

        print('== test: both guarantees present in 10-pull')
        user = {"coins":100000, "owned":[], "tickets":0, "pity_sss":200, "pity_ur":500}
        make_user_cookie(client, user)

        r = client.post('/pull', json={'count': 10})
        j = r.get_json()
        print('response:', json.dumps(j, indent=2))
        assert r.status_code == 200
        assert j['ok']
        assert any(c['rarity'] == 'SSS' and not c.get('duplicate', False) for c in j['results']), 'Expected at least one unowned SSS from combined pity'
        assert any(c['rarity'] == 'UR' and not c.get('duplicate', False) for c in j['results']), 'Expected at least one unowned UR from combined pity'
        assert j['pity_sss'] == 0 and j['pity_ur'] == 0

        print('== test: increment pity when no SSS/UR obtained (deterministic)')
        # patch choose_rarity to always return low rarities so we won't accidentally hit SSS/UR
        from app import choose_rarity as original_choose
        app.choose_rarity = lambda pulls=1: ['A'] * pulls

        user = {"coins":100000, "owned":[], "tickets":0, "pity_sss":0, "pity_ur":0}
        make_user_cookie(client, user)

        r = client.post('/pull', json={'count': 3})
        j = r.get_json()
        print('response:', json.dumps(j, indent=2))
        assert r.status_code == 200
        assert j['ok']
        assert j['pity_sss'] == 3
        assert j['pity_ur'] == 3

        # restore
        app.choose_rarity = original_choose

        print('All pity tests passed.')
