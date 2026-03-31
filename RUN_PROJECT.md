# UDX Project - How to Run

This document describes how to run both the frontend and backend servers for the UDX project.

## Prerequisites

- **Node.js** (v18+) with npm — download from https://nodejs.org/
- **Python** (v3.9+) — already installed on your system (v3.14.0 detected)

## Backend Setup & Run

### 1. Install Backend Dependencies

```powershell
cd "C:\Users\user\Downloads\UDX (2) 2\UDX (2)"
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
```

**Note:** If PowerShell execution policy blocks the venv activation script, use the direct python path as shown above.

### 2. Configure Environment (Optional)

Set these environment variables if you need specific features:

```powershell
# Use SQLite for local development (default, no setup needed):
$env:DATABASE_URL = "sqlite:///./backend_udx.db"

# Required for Google OAuth:
$env:GOOGLE_CLIENT_ID = "your-google-client-id"
$env:GOOGLE_CLIENT_SECRET = "your-google-client-secret"

# Required for weather features:
$env:OPENWEATHER_API_KEY = "your-openweather-api-key"

# Optional security overrides:
$env:SECRET_KEY = "your-dev-secret"
$env:ALGORITHM = "HS256"
$env:ACCESS_TOKEN_EXPIRE_MINUTES = "30"
```

### 3. Start the Backend Server

```powershell
cd "C:\Users\user\Downloads\UDX (2) 2\UDX (2)"
python -m uvicorn backend.main:app --reload --port 8000
```

The backend will start on **http://127.0.0.1:8000**

- API documentation: **http://localhost:8000/docs** (Swagger UI)
- OpenAPI schema: **http://localhost:8000/openapi.json**

## Frontend Setup & Run

### 1. Install Frontend Dependencies

```powershell
cd "C:\Users\user\Downloads\UDX (2) 2\UDX (2)"
npm install
```

### 2. Start the Development Server

```powershell
npm run dev
```

The frontend will start on **http://localhost:5173** (or another port if 5173 is taken; check console output).

### 3. Build for Production

```powershell
npm run build
```

Output goes to `build/` directory.

## Running Both Servers Together

**Option 1: Two PowerShell Windows (Recommended)**

1. **Terminal 1 – Backend:**
   ```powershell
   cd "C:\Users\user\Downloads\UDX (2) 2\UDX (2)"
   python -m uvicorn backend.main:app --reload --port 8000
   ```

2. **Terminal 2 – Frontend:**
   ```powershell
   cd "C:\Users\user\Downloads\UDX (2) 2\UDX (2)"
   npm run dev
   ```

**Option 2: Single Window with Background Processes**

```powershell
cd "C:\Users\user\Downloads\UDX (2) 2\UDX (2)"

# Start backend in background
$backendJob = Start-Job -ScriptBlock {
    cd "C:\Users\user\Downloads\UDX (2) 2\UDX (2)"
    python -m uvicorn backend.main:app --reload --port 8000
}

# Start frontend
npm run dev

# To stop the backend job later:
# Stop-Job $backendJob
# Remove-Job $backendJob
```

## Project Structure

```
UDX (2)/
├── backend/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── models.py               # SQLAlchemy ORM models
│   ├── schemas.py              # Pydantic request/response schemas
│   ├── database.py             # Database configuration (SQLite default)
│   └── requirements.txt         # Python dependencies
├── src/
│   ├── main.tsx                # React entry point
│   ├── App.tsx                 # Main App component
│   ├── api.ts                  # Frontend API client
│   └── components/             # React components
├── package.json                # Frontend dependencies & scripts
├── tsconfig.json               # TypeScript configuration
└── vite.config.ts              # Vite build configuration
```

## Key Features

### Backend (FastAPI on port 8000)
- User authentication with JWT tokens
- Google OAuth2 integration
- Product management (seller) & browsing (buyer)
- Shopping cart & order management
- Real-time messaging/chat
- Weather API integration
- SQLite database (local dev) / PostgreSQL (production)

### Frontend (Vite + React on port 5173)
- Responsive UI with Radix UI components
- Role-based access (buyer/seller)
- Multi-step forms & authentication flows
- Real-time chat interface
- Market trends & product search
- Language selection & translation support

## Troubleshooting

### Backend won't start: `ModuleNotFoundError`
✅ **Fixed** – The project uses relative imports for `backend/` modules.

### Backend won't start: `UnicodeDecodeError`
✅ **Fixed** – Default database changed to SQLite (`sqlite:///./backend_udx.db`)

### npm: command not found
- Install Node.js from https://nodejs.org/
- Add Node to your system PATH

### Python not found
- Ensure Python is installed: `python --version`
- If using venv, activate it before running pip commands

### Port already in use
- Backend: change `--port 8000` to another port (e.g., `--port 8001`)
- Frontend: Vite will auto-increment if 5173 is taken

## Environment File (.env)

You can create a `.env` file in the project root for automatic loading:

```
DATABASE_URL=sqlite:///./backend_udx.db
SECRET_KEY=your-dev-secret
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
OPENWEATHER_API_KEY=your-api-key
```

The backend uses `python-dotenv` to load this automatically.

## API Endpoints (Sample)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/users/` | Create new user |
| `POST` | `/token` | Login (returns JWT) |
| `GET` | `/users/me` | Get current user |
| `GET` | `/products/` | List all products |
| `POST` | `/products/` | Create product (seller only) |
| `GET` | `/orders/` | List user's orders |
| `POST` | `/orders/` | Create order |
| `GET` | `/chats/` | Get user's chats |
| `POST` | `/chats/{chat_id}/messages` | Send message |
| `GET` | `/weather?lat=40&lon=-74` | Get weather data |

Full API docs available at **http://localhost:8000/docs**

## Next Steps

1. Run the backend: `python -m uvicorn backend.main:app --reload --port 8000`
2. Run the frontend: `npm run dev`
3. Open **http://localhost:5173** in your browser
4. Test the API at **http://localhost:8000/docs**

Enjoy!
