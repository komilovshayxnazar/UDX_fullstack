# UDX Test Scripts

Automated scripts to verify the functionality of the Backend API and the Android Application.

## Folder Structure

```
tests/
├── backend/
│   ├── conftest.py          # Shared pytest fixtures (users, tokens, client)
│   ├── test_auth.py         # Authentication: login, registration, OAuth, OTP
│   ├── test_users.py        # User profile, password, role, 2FA, cards, wallet
│   ├── test_products.py     # Products, categories, price history, recommendations
│   ├── test_orders.py       # Order creation and listing
│   ├── test_chat.py         # Chat creation, messaging, mark-read
│   ├── test_contracts.py    # Contract lifecycle and access control
│   ├── test_security.py     # Auth hardening, input validation, idempotency, health
│   └── test_api.py          # Original smoke tests (health, products, weather)
└── android/
    └── test_adb.py          # ADB-based Android install/state tests
```

## Backend API Tests

### Prerequisites

```bash
pip install pytest httpx
```

### Running

Ensure the backend is running first:

```bash
python -m uvicorn backend.main:app --reload --port 8000
```

Then run the full suite:

```bash
cd tests/backend
pytest -v
```

Run a specific file:

```bash
pytest test_auth.py -v
pytest test_users.py -v
pytest test_products.py -v
pytest test_orders.py -v
pytest test_chat.py -v
pytest test_contracts.py -v
pytest test_security.py -v
```

Run a specific test class or test:

```bash
pytest test_auth.py::TestLogin -v
pytest test_auth.py::TestLogin::test_valid_credentials_return_jwt -v
```

### Environment Variables

| Variable  | Default                   | Description              |
|-----------|---------------------------|--------------------------|
| `API_URL` | `http://localhost:8000`   | Backend base URL         |

Override example:

```bash
API_URL=http://staging.example.com pytest -v
```

### Test Coverage Summary

| File                  | Area Covered                                              | Tests |
|-----------------------|-----------------------------------------------------------|-------|
| `test_auth.py`        | Login, registration, password rules, Google OAuth, OTP    | ~20   |
| `test_users.py`       | Profile CRUD, password/phone/role change, 2FA, cards, wallet | ~25 |
| `test_products.py`    | CRUD, filters, price history, interactions, recommendations, uploads | ~25 |
| `test_orders.py`      | Create order, total calc, listing, pagination, auth       | ~15   |
| `test_chat.py`        | Chat creation, dedup, messaging, history, mark-read, auth | ~20   |
| `test_contracts.py`   | Create, list, status updates, access control              | ~18   |
| `test_security.py`    | Token hardening, input validation, idempotency, weather   | ~20   |

## Android ADB Tests

Ensure an emulator or physical device is connected via ADB, then:

```bash
cd tests/android
python test_adb.py
```

*Requires `adb` in your system PATH.*
