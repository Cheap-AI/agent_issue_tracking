from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from practice.document_store import add_document, init_db, list_documents, search_documents

app = FastAPI(title="Document Store")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3002",
        "http://127.0.0.1:3002",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
init_db()


class DocumentCreate(BaseModel):
    title: str
    content: str


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Document store is running"}


@app.post("/documents", status_code=201)
def create_document(payload: DocumentCreate) -> dict[str, object]:
    doc_id = add_document(payload.title, payload.content)
    return {"id": doc_id, "title": payload.title, "content": payload.content}


@app.get("/documents")
def get_documents() -> list[dict[str, object]]:
    return list_documents()


@app.get("/search")
def search_documents_api(q: str) -> list[dict[str, object]]:
    return search_documents(q)
