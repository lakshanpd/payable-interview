# CircleFund

A rotating-savings-circle ("ROSCA"/chama/tanda/ajo) app: up to 4 members
pay a fixed contribution into a shared pot every round, and each round's
pot pays out to one member in turn until everyone has been paid once.

This repo contains:

- `backend/` — Django 5 + Django REST Framework + SimpleJWT, SQLite
- `mobile/` — Expo (React Native) + React Navigation + Axios + AsyncStorage
- `postman-test.json` — a Postman collection covering the full API flow (register 5 users, create a circle, join it, fetch details, contribute, approve)

## Setup

### Backend

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

### Mobile app

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

## API Endpoints

| Method | Path                          | Auth | Description                                   |
|--------|-------------------------------|------|------------------------------------------------|
| POST   | `/api/auth/register`          | No   | Create a user account                          |
| POST   | `/api/auth/login`              | No   | Log in with email + password, get JWT pair     |
| POST   | `/api/auth/token/refresh`      | No   | Exchange a refresh token for a new access token|
| POST   | `/api/circles`                 | Yes  | Create a circle (caller becomes admin, position 1, first round auto-created) |
| POST   | `/api/circles/join`            | Yes  | Join a circle by invite code                   |
| GET    | `/api/circles/{id}`            | Yes  | Circle info, member list, current round, per-member contribution status (members only) |
| GET    | `/api/rounds/{id}`             | Yes  | A single round with its contributions (circle members only) |
| POST   | `/api/rounds/{id}/contribute`  | Yes  | Pay into the round's pot                        |
| POST   | `/api/rounds/{id}/approve`     | Yes  | Approve payout and close the round (circle admin only) |

All endpoints except register/login/token-refresh require
`Authorization: Bearer <access_token>`.

## Architecture Decisions

- **Custom `User` model** (`apps.users.User`, extends `AbstractUser`) with
  a unique `email`, so login can be keyed on email while `username` stays
  available for Django internals and display.
- **Service layer** (`apps/*/services.py`) holds all business logic —
  invite code generation, membership rules, round rotation, penalty/payout
  math, and every locking decision. Views only translate HTTP ⇄
  serializers ⇄ service calls; they don't contain business rules. This
  keeps the rules unit-testable without spinning up HTTP, and keeps a
  second entry point (e.g. an admin action, a management command, a
  Celery task) trivial to add later without duplicating logic.
- **`ServiceError`** (`apps/common/exceptions.py`) is a plain Python
  exception the service layer raises for business-rule violations (already
  contributed, round not open, not the admin, etc.), carrying an HTTP
  status code. A single DRF exception handler turns it into a consistent
  `{"detail": ..., "code": ...}` JSON error response, so services stay
  independent of DRF/HTTP and views don't need `try/except` scattered
  through them.
- **Money is stored as plain integers** everywhere (`PositiveIntegerField`),
  matching the assessment's own examples (`5000`, `150`, `5150`). No
  currency subunit conversion is applied — see "Assumptions" below.
- **`Round.contribution_amount` is a snapshot**, copied from
  `Circle.contribution_amount` at round-creation time, so changing a
  circle's contribution amount can never rewrite what's owed on an
  already-open round.
- **Recipient rotation** is computed, not stored as mutable "next
  recipient" state: `RoundService._next_unpaid_member` finds the
  lowest-position member who has never been the `payout_recipient` of a
  `COMPLETED` round. This makes the rotation self-healing — there's no
  separate counter that could drift out of sync with actual round history.
- **A DRF `permissions.py` per app** (`IsCircleMember`,
  `IsCircleAdmin`, `IsRoundCircleMember`) enforces membership/admin checks
  at the view layer as belt-and-suspenders; the service layer re-checks
  the same rules independently (via `ServiceError`) so the invariant holds
  even if a view forgets to wire up a permission class.

## Concurrency Strategy

Three invariants have to hold under concurrent requests, with **no
in-memory flags or locks** (those don't work across multiple server
processes, and this design is meant to generalize beyond a single
`runserver` process):

1. A member can contribute to a round **at most once**.
2. A round can be approved **at most once**, creating **at most one**
   follow-on round.
3. A circle can have **at most one `OPEN` round** at a time, and can't
   exceed `max_members`.

Every mutating service method (`CircleService.join_circle`,
`RoundService.contribute`, `RoundService.approve_round`) follows the same
pattern:

```python
with transaction.atomic():
    row = Model.objects.select_for_update().get(...)   # lock
    # ... re-check invariants against the now-locked row ...
    # ... mutate + save ...
```

`select_for_update()` takes a real row lock on Postgres/MySQL: a second
concurrent request for the same row blocks at the database until the
first transaction commits or rolls back, then re-reads the now-current
state — so the "already contributed" / "not pending approval" checks can
never be stale.

**Why this also works on SQLite** (this project's database): SQLite has
no row-level locking, so `select_for_update()` compiles to a plain
`SELECT` there (Django's supported behavior for backends without the
feature). To still get real serialization, `config/settings.py` sets:

```python
DATABASES = {"default": {..., "OPTIONS": {"transaction_mode": "IMMEDIATE"}}}
```

which makes every `atomic()` block open with `BEGIN IMMEDIATE` instead of
a deferred transaction. `BEGIN IMMEDIATE` takes SQLite's write lock
*immediately*, before any statement runs — so a second concurrent
transaction blocks at `BEGIN` until the first one finishes, reproducing
the same "one writer at a time, always re-reading fresh state" guarantee
`select_for_update()` gives on Postgres. The two mechanisms are
complementary: the code is portable to Postgres/MySQL as-is, and correct
on SQLite today.

**Belt-and-suspenders at the schema level**, in case application logic is
ever bypassed (a bulk import, a bug, a future direct-SQL migration):

- `UniqueConstraint(circle, user)` and `(circle, position)` on
  `CircleMember` — no double-joins, no duplicate positions.
- `UniqueConstraint(round, member)` on `Contribution` — no duplicate
  contributions, enforced even if the locking above were somehow skipped.
- A **partial unique index** `UniqueConstraint(circle, condition=Q(status="OPEN"))`
  on `Round` — the database itself refuses to ever hold two `OPEN` rounds
  for one circle.

This is exercised by real multi-threaded tests (not mocks) in
`apps/rounds/tests/test_rounds.py::ConcurrencyTests`, using
`TransactionTestCase` (required — a plain `TestCase` wraps the whole test
in one rolled-back transaction, which would hide races entirely) and
`threading.Barrier` to force two threads to hit the same round at the
same instant.

## Penalty & Payout Math

All monetary math uses `decimal.Decimal`, never `float`, per the spec:

```python
penalty = Decimal(amount) * Decimal(penalty_rate) / Decimal(100)
penalty = int(penalty.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

payout = Decimal(total_collected) * Decimal("0.99")
payout = int(payout.quantize(Decimal("1"), rounding=ROUND_FLOOR))
```

Verified against the spec's own examples:

- `5000 * 3% = 150.00` → penalty `150`, total `5150`
- `3333 * 3% = 99.99` → rounds up (`ROUND_HALF_UP`) → penalty `100`, total `3433`

## Assumptions

- **Currency units**: all amounts (`contribution_amount`, `penalty`,
  `total_paid`, `payout_amount`) are stored and returned as plain
  integers with no implicit subunit (cents) conversion, matching the
  spec's own examples exactly (`contribution_amount: 5000` → penalty
  `150`). If a real currency subunit convention is needed, the API
  contract doesn't change — only how the mobile client formats the number
  for display.
- **`penalty_rate`** is an admin-supplied whole percent (e.g. `3` = 3%),
  defaulting to `3` when not provided at circle creation, since the spec
  doesn't fix a default.
- **Round deadline**: not specified by the assessment, so each round gets
  a 7-day deadline from creation (`ROUND_DURATION` in
  `apps/rounds/services.py`).
- **Login identity**: the mobile Login screen asks for email (per spec),
  so `POST /api/auth/login` authenticates by email; `username` is still
  required at registration and used for display (circle member lists,
  etc.).
- **A circle with only its admin and no other members**: the "all
  non-recipient members contributed" check is vacuously true (there's
  no one else who owes money), so such a round becomes eligible for
  approval immediately. This wasn't specified, but felt more useful than
  a round that can never progress.
- **`APPEND_SLASH = False`**: the spec's endpoints have no trailing slash
  (`POST /api/circles`, not `/api/circles/`). Django's default
  `APPEND_SLASH` behavior 301-redirects such requests, which silently
  drops the POST body — so it's disabled, and URLs are defined to match
  the spec exactly.
- **Password validation**: Django's `CommonPasswordValidator` is
  intentionally left out of `AUTH_PASSWORD_VALIDATORS` — it would reject
  ordinary demo/test passwords like `password123` (used throughout the
  included Postman collection). `MinimumLengthValidator` (8 chars),
  `UserAttributeSimilarityValidator`, and `NumericPasswordValidator` are
  still active.

## Testing

35 tests in `backend/apps/*/tests/`, run with `python manage.py test apps`:

- **Auth**: registration (success, duplicate email, duplicate username),
  login (success, wrong password, unknown email)
- **Circles**: circle creation (admin at position 1, invite code
  uniqueness, first round auto-created), joining (sequential positions,
  duplicate join rejected, invalid code, 5th member rejected), circle
  detail (membership required)
- **Rounds**: penalty calculation (exact and half-up rounding), payout
  calculation, on-time vs. late contributions, recipient-can't-contribute,
  duplicate-contribution rejection, round auto-closing (all contributed,
  or deadline passed), admin-only approval, double-approval rejection,
  round rotation across all 4 positions, no round created once everyone's
  been paid
- **Concurrency**: real multi-threaded tests for simultaneous
  contributions and double approval (`TransactionTestCase` +
  `threading.Barrier`)

The whole flow (register → login → create circle → join × 3 → get
details → get round → contribute × 3 → reject non-admin approval →
approve → payout math → reject double-approval) was also manually
verified end-to-end against a running server using `postman-test.json`'s
requests.
