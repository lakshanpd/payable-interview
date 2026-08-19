# Setup

## Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser  # optional, for /admin/
python manage.py runserver         # http://localhost:8000
```

Run the test suite:

```bash
python manage.py test apps
```

There's no seed data — a fresh `migrate` gives you an empty database with
no accounts. Create one through the mobile app's Sign Up screen (or
`POST /api/auth/register`).

## Mobile app

```bash
cd mobile
npm install

# Point the app at your backend — edit src/services/config.ts:
#   - iOS simulator:      http://localhost:8000/api
#   - Android emulator:   http://10.0.2.2:8000/api
#   - physical device:    http://<your-machine-LAN-IP>:8000/api
#     (and run the backend with: python manage.py runserver 0.0.0.0:8000)

npm start
```

Then press `i` (iOS simulator), `a` (Android emulator), or scan the QR
code in Expo Go on a physical device.
