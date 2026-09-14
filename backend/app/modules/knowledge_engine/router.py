from fastapi import APIRouter
from pydantic import BaseModel
from app.modules.knowledge_engine.retriever import retrieve, add_chunk
from app.shared.schemas.models import KnowledgeChunk

router = APIRouter(prefix="/knowledge", tags=["knowledge_engine"])


@router.get("/search")
async def search_knowledge(q: str, top_k: int = 3):
    chunks = await retrieve(q, top_k=top_k)
    return [
        {
            "id": c.id,
            "source": c.source,
            "source_type": c.source_type,
            "content": c.content[:300],
        }
        for c in chunks
    ]


class IngestRequest(BaseModel):
    source: str
    source_type: str
    content: str


@router.post("/ingest")
async def ingest_document(req: IngestRequest):
    chunk = KnowledgeChunk(source=req.source, source_type=req.source_type, content=req.content)
    await add_chunk(chunk)
    return {"status": "ingested", "chunk_id": chunk.id, "source": chunk.source}
