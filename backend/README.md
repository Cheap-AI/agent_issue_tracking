# Backend

FastAPI backend with SQLAlchemy ORM.

## Install

python -m pip install -r requirements.txt

## Run

cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

## API

- GET `/` - health check
- GET `/items/` - list items
- POST `/items/` - create item
