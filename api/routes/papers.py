from fastapi import APIRouter, HTTPException
from typing import List
from schemas import PaperCreate, PaperUpdate, PaperResponse
from database import get_db_pool
import json

router = APIRouter(prefix="/papers", tags=["papers"])

@router.post("/", response_model=PaperResponse, status_code=201)
async def create_paper(paper: PaperCreate):
    pool = await get_db_pool()
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO papers (corpus_id, arxiv_id, title, abstract, metadata, file_path, source)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id, corpus_id, arxiv_id, title, abstract, metadata, file_path, source, created_at
                """,
                paper.corpus_id, paper.arxiv_id, paper.title, paper.abstract,
                json.dumps(paper.metadata) if paper.metadata else None,
                paper.file_path, paper.source.value
            )
            result = dict(row)
            if result['metadata']:
                result['metadata'] = json.loads(result['metadata'])
            return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[PaperResponse])
async def get_papers():
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, corpus_id, arxiv_id, title, abstract, metadata, file_path, source, created_at FROM papers"
        )
        results = []
        for row in rows:
            result = dict(row)
            if result['metadata']:
                result['metadata'] = json.loads(result['metadata'])
            results.append(result)
        return results

@router.get("/{paper_id}", response_model=PaperResponse)
async def get_paper(paper_id: int):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, corpus_id, arxiv_id, title, abstract, metadata, file_path, source, created_at FROM papers WHERE id = $1",
            paper_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Paper not found")
        result = dict(row)
        if result['metadata']:
            result['metadata'] = json.loads(result['metadata'])
        return result

@router.put("/{paper_id}", response_model=PaperResponse)
async def update_paper(paper_id: int, paper: PaperUpdate):
    pool = await get_db_pool()
    updates = []
    values = []
    idx = 1
    
    if paper.arxiv_id is not None:
        updates.append(f"arxiv_id = ${idx}")
        values.append(paper.arxiv_id)
        idx += 1
    if paper.title is not None:
        updates.append(f"title = ${idx}")
        values.append(paper.title)
        idx += 1
    if paper.abstract is not None:
        updates.append(f"abstract = ${idx}")
        values.append(paper.abstract)
        idx += 1
    if paper.metadata is not None:
        updates.append(f"metadata = ${idx}")
        values.append(json.dumps(paper.metadata))
        idx += 1
    if paper.file_path is not None:
        updates.append(f"file_path = ${idx}")
        values.append(paper.file_path)
        idx += 1
    if paper.source is not None:
        updates.append(f"source = ${idx}")
        values.append(paper.source.value)
        idx += 1
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    values.append(paper_id)
    query = f"""UPDATE papers SET {', '.join(updates)} 
                WHERE id = ${idx} 
                RETURNING id, corpus_id, arxiv_id, title, abstract, metadata, file_path, source, created_at"""
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *values)
        if not row:
            raise HTTPException(status_code=404, detail="Paper not found")
        result = dict(row)
        if result['metadata']:
            result['metadata'] = json.loads(result['metadata'])
        return result

@router.delete("/{paper_id}", status_code=204)
async def delete_paper(paper_id: int):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM papers WHERE id = $1", paper_id)
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Paper not found")

