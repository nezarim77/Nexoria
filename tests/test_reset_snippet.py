import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app
import json

with app.test_client() as c:
    r1 = c.post('/reset')
    j1 = r1.get_json(silent=True)
    print('NO_BODY', r1.status_code, json.dumps(j1, ensure_ascii=False))

    r2 = c.post('/reset', json={'confirm': True})
    j2 = r2.get_json(silent=True)
    print('WITH_CONFIRM', r2.status_code, json.dumps(j2, ensure_ascii=False))
