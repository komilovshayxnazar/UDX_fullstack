# UDX Backend

This is the FastAPI backend for the UDX application.

## Setup

1.  Make sure you have Python 3.10+ installed.
2.  Create a virtual environment:
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Running the Server

Start the development server:

```bash
uvicorn main:app --reload
```

The server will start at `http://127.0.0.1:8000`.

## API Documentation

Once the server is running, visit:
-   Swagger UI: `http://127.0.0.1:8000/docs`
-   ReDoc: `http://127.0.0.1:8000/redoc`
