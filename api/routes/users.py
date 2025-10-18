from fastapi import APIRouter, HTTPException
from typing import List
from schemas import UserCreate, UserUpdate, UserResponse
from database import get_db_pool

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(user: UserCreate):
    pool = await get_db_pool()
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO users (email, name)
                VALUES ($1, $2)
                RETURNING id, email, name, created_at
                """,
                user.email, user.name
            )
            return dict(row)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[UserResponse])
async def get_users():
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, email, name, created_at FROM users")
        return [dict(row) for row in rows]

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, name, created_at FROM users WHERE id = $1",
            user_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        return dict(row)

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user: UserUpdate):
    pool = await get_db_pool()
    updates = []
    values = []
    idx = 1
    
    if user.email is not None:
        updates.append(f"email = ${idx}")
        values.append(user.email)
        idx += 1
    if user.name is not None:
        updates.append(f"name = ${idx}")
        values.append(user.name)
        idx += 1
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    values.append(user_id)
    query = f"UPDATE users SET {', '.join(updates)} WHERE id = ${idx} RETURNING id, email, name, created_at"
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *values)
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        return dict(row)

@router.delete("/{user_id}", status_code=204)
async def delete_user(user_id: int):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM users WHERE id = $1", user_id)
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="User not found")


