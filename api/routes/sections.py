from fastapi import APIRouter, HTTPException
from typing import List
from schemas import SectionCreate, SectionUpdate, SectionResponse
from database import get_db_pool

router = APIRouter(prefix="/sections", tags=["sections"])

@router.post("/", response_model=SectionResponse, status_code=201)
async def create_section(section: SectionCreate):
    pool = await get_db_pool()
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO sections (paper_id, header, text)
                VALUES ($1, $2, $3)
                RETURNING id, paper_id, header, text, created_at
                """,
                section.paper_id, section.header, section.text
            )
            return dict(row)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[SectionResponse])
async def get_sections():
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, paper_id, header, text, created_at FROM sections")
        return [dict(row) for row in rows]

@router.get("/{section_id}", response_model=SectionResponse)
async def get_section(section_id: int):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, paper_id, header, text, created_at FROM sections WHERE id = $1",
            section_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Section not found")
        return dict(row)

@router.get("/paper/{paper_id}", response_model=List[SectionResponse])
async def get_sections_by_paper(paper_id: int):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, paper_id, header, text, created_at FROM sections WHERE paper_id = $1",
            paper_id
        )
        return [dict(row) for row in rows]

@router.put("/{section_id}", response_model=SectionResponse)
async def update_section(section_id: int, section: SectionUpdate):
    pool = await get_db_pool()
    updates = []
    values = []
    idx = 1
    
    if section.header is not None:
        updates.append(f"header = ${idx}")
        values.append(section.header)
        idx += 1
    if section.text is not None:
        updates.append(f"text = ${idx}")
        values.append(section.text)
        idx += 1
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    values.append(section_id)
    query = f"UPDATE sections SET {', '.join(updates)} WHERE id = ${idx} RETURNING id, paper_id, header, text, created_at"
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *values)
        if not row:
            raise HTTPException(status_code=404, detail="Section not found")
        return dict(row)

@router.delete("/{section_id}", status_code=204)
async def delete_section(section_id: int):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM sections WHERE id = $1", section_id)
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Section not found")
