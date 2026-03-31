# UDX Test Scripts

This folder contains automated scripts to verify the functionality of both the Backend API and the Android Application.

## Folder Structure

- `backend/`: Python scripts to test API endpoints.
- `android/`: ADB-based scripts to verify app installation and state.

## How to Run

### Backend API Tests

Ensure the backend server is running, then execute:

```bash
cd tests/backend
python test_api.py
```

*Note: Requires `requests` library (`pip install requests`)*

### Android ADB Tests

Ensure an emulator or physical device is connected via ADB, then execute:

```bash
cd tests/android
python test_adb.py
```

*Note: Requires `adb` to be in your system PATH.*
