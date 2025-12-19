#!/usr/bin/env python3
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app
import re
import json


def extract_uid_from_set_cookie(resp):
    sc = resp.headers.get('Set-Cookie') or ''
    m = re.search(r'uid=([^;]+)', sc)
    return m.group(1) if m else None


def print_user_file(uid):
    path = os.path.join(os.path.dirname(__file__), '..', 'user_data', f'{uid}.json')
    path = os.path.abspath(path)
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print('User file:', path)
            print(json.dumps(data, indent=2))
        except Exception as e:
            print('Could not read user file:', e)
    else:
        print('User file does not exist:', path)


if __name__ == '__main__':
    with app.test_client() as client:
        print('== GET / (first)')
        r1 = client.get('/')
        print('Status:', r1.status_code)
        print('Set-Cookie header:', r1.headers.get('Set-Cookie'))
        uid = extract_uid_from_set_cookie(r1)
        print('Extracted uid from Set-Cookie:', uid)
        print_user_file(uid)

        html = r1.get_data(as_text=True)
        m = re.search(r'<span id="coins">.*?(\d+)\s*</span>', html, re.S)
        if m:
            print('Coins on page:', m.group(1))
        else:
            print('Could not find coins in page HTML')

        print('\n== POST /pull count=1')
        r2 = client.post('/pull', json={'count': 1})
        print('Status:', r2.status_code)
        try:
            j = r2.get_json()
        except Exception:
            j = None
        print('JSON response:', json.dumps(j, indent=2))
        print('Set-Cookie header on POST:', r2.headers.get('Set-Cookie'))
        print_user_file(uid)

        print('\n== GET / (after pull)')
        r3 = client.get('/')
        print('Status:', r3.status_code)
        html3 = r3.get_data(as_text=True)
        m3 = re.search(r'<span id="coins">.*?(\d+)\s*</span>', html3, re.S)
        if m3:
            print('Coins on page after pull:', m3.group(1))
        else:
            print('Could not find coins in page HTML after pull')

        if j and 'coins' in j:
            print('Coins from pull response:', j['coins'])
