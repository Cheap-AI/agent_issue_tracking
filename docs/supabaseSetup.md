after database_url

python -m alembic upgrade head
python -m pytest tests/

# Activate venv if needed
.\.venv\Scripts\Activate.ps1

# Set up database
python -m alembic upgrade head

# Start backend (runs on http://127.0.0.1:8000)
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload