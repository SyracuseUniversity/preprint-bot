from fastapi import APIRouter, HTTPException
from typing import List
from schemas import EmbeddingCreate, EmbeddingUpdate, EmbeddingResponse
from database import get_db_pool

router = APIRouter(prefix="/embeddings", tags=["embeddings"])

@router.post("/", response_model=EmbeddingResponse, status_code=201)
async def create_embedding(embedding: EmbeddingCreate):
    pool = await get_db_pool()
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO embeddings (paper_id, section_id, embedding, type, model_name)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, paper_id, section_id, type, model_name, created_at
                """,
                embedding.paper_id, embedding.section_id, embedding.embedding,
                embedding.type.value, embedding.model_name
            )
            return dict(row)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[EmbeddingResponse])
async def get_embeddings():
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, paper_id, section_id, type, model_name, created_at FROM embeddings")
        return [dict(row) for row in rows]

@router.get("/{embedding_id}", response_model=EmbeddingResponse)
async def get_embedding(embedding_id: int):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, paper_id, section_id, type, model_name, created_at FROM embeddings WHERE id = $1",
            embedding_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Embedding not found")
        return dict(row)

@router.get("/paper/{paper_id}", response_model=List[EmbeddingResponse])
async def get_embeddings_by_paper(paper_id: int):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, paper_id, section_id, type, model_name, created_at FROM embeddings WHERE paper_id = $1",
            paper_id
        )
        return [dict(row) for row in rows]

@router.put("/{embedding_id}", response_model=EmbeddingResponse)
async def update_embedding(embedding_id: int, embedding: EmbeddingUpdate):
    pool = await get_db_pool()
    
    if embedding.embedding is None:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """UPDATE embeddings SET embedding = $1 
               WHERE id = $2 
               RETURNING id, paper_id, section_id, type, model_name, created_at""",
            embedding.embedding, embedding_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Embedding not found")
        return dict(row)

@router.delete("/{embedding_id}", status_code=204)
async def delete_embedding(embedding_id: int):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM embeddings WHERE id = $1", embedding_id)
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Embedding not found")
