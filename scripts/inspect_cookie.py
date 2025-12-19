from app import app
import inspect
with app.test_client() as client:
    print('set_cookie signature:', inspect.signature(client.set_cookie))
    print(client.set_cookie.__doc__)
