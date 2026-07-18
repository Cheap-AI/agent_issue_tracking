from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .database import SessionLocal, engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Backend API")

@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "FastAPI backend is running"}

@app.post("/items/", response_model=schemas.Item)
def create_item(item: schemas.ItemCreate, db: Session = Depends(get_db)) -> schemas.Item:
    return crud.create_item(db=db, item=item)

@app.get("/items/", response_model=list[schemas.Item])
def read_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> list[schemas.Item]:
    return crud.get_items(db=db, skip=skip, limit=limit)
