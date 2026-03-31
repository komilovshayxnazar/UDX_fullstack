# Quick PostgreSQL Setup Guide

## Current Status
✅ PostgreSQL@15 is installed and running
✅ All Python dependencies are installed
✅ Code is configured to use PostgreSQL

## Next Steps - Choose ONE option:

### Option 1: Quick Setup (Recommended)
Run these commands in your terminal:

```bash
# Navigate to backend directory
cd "/Users/shayxnazar/Downloads/Bank fayllar/UDX (2)/backend"

# Create database and user (you may be prompted for your system password)
psql postgres << 'EOF'
CREATE USER udx_user WITH PASSWORD 'udx_password';
CREATE DATABASE udx_db OWNER udx_user;
GRANT ALL PRIVILEGES ON DATABASE udx_db TO udx_user;
\q
EOF

# Test the connection
python3 test_db.py

# Start the application
uvicorn main:app --reload
```

### Option 2: Manual Setup
If the quick setup doesn't work, do this manually:

1. Open PostgreSQL:
   ```bash
   psql postgres
   ```

2. Run these SQL commands:
   ```sql
   CREATE USER udx_user WITH PASSWORD 'udx_password';
   CREATE DATABASE udx_db OWNER udx_user;
   GRANT ALL PRIVILEGES ON DATABASE udx_db TO udx_user;
   \q
   ```

3. Test and run:
   ```bash
   python3 test_db.py
   uvicorn main:app --reload
   ```

### Option 3: Use Docker PostgreSQL (Alternative)
If you prefer Docker:

```bash
# Start PostgreSQL in Docker
docker run --name udx-postgres \
  -e POSTGRES_USER=udx_user \
  -e POSTGRES_PASSWORD=udx_password \
  -e POSTGRES_DB=udx_db \
  -p 5432:5432 \
  -d postgres:15

# Test connection
python3 test_db.py

# Start application
uvicorn main:app --reload
```

## What's Been Done

✅ Updated `requirements.txt` with PostgreSQL driver (`psycopg2-binary`)
✅ Modified `database.py` to use PostgreSQL with connection pooling
✅ Created `.env` file with database credentials
✅ Created `.env.example` for reference
✅ Added `.gitignore` to protect sensitive files
✅ Updated `main.py` to load environment variables

## Configuration Files

- **`.env`**: Contains `DATABASE_URL=postgresql://udx_user:udx_password@localhost:5432/udx_db`
- **`database.py`**: Configured with PostgreSQL connection pooling
- **`requirements.txt`**: Includes `psycopg2-binary` and `python-dotenv`

## Verification

After setup, verify everything works:

```bash
# Test database connection
python3 test_db.py

# Start the application (this will create all tables automatically)
uvicorn main:app --reload

# Visit http://localhost:8000/docs to see the API documentation

# Seed test data
curl -X POST http://localhost:8000/dev/seed
```

## Troubleshooting

**If you get "password authentication failed":**
- Make sure you created the user with the correct password
- Check that `.env` has the correct credentials

**If you get "database does not exist":**
- Run: `createdb -U udx_user udx_db`
- Or create it in psql: `CREATE DATABASE udx_db OWNER udx_user;`

**If PostgreSQL is not running:**
```bash
brew services start postgresql@15
```

**To change the password:**
Update both:
1. PostgreSQL: `psql postgres -c "ALTER USER udx_user WITH PASSWORD 'new_password';"`
2. `.env` file: Update the `DATABASE_URL` with the new password
