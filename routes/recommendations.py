from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from schemas import (
    RecommendationRunCreate, RecommendationRunResponse,
    RecommendationCreate, RecommendationResponse
)
from database import get_db_pool
import json

router = APIRouter(prefix="/recommendation-runs", tags=["recommendation-runs"])

# Recommendation Run endpoints
@router.post("/", response_model=RecommendationRunResponse, status_code=201)
async def create_recommendation_run(run: RecommendationRunCreate):
    pool = await get_db_pool()
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO recommendation_runs (profile_id, user_id, user_corpus_id, ref_corpus_id, threshold, method)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, profile_id, user_id, user_corpus_id, ref_corpus_id, threshold, method, created_at
                """,
                run.profile_id, run.user_id, run.user_corpus_id, run.ref_corpus_id, run.threshold, run.method
            )
            return dict(row)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[RecommendationRunResponse])
async def get_recommendation_runs():
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, profile_id, user_id, user_corpus_id, ref_corpus_id, threshold, method, created_at FROM recommendation_runs"
        )
        return [dict(row) for row in rows]

@router.get("/{run_id}", response_model=RecommendationRunResponse)
async def get_recommendation_run(run_id: int):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, profile_id, user_id, user_corpus_id, ref_corpus_id, threshold, method, created_at FROM recommendation_runs WHERE id = $1",
            run_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Recommendation run not found")
        return dict(row)

@router.delete("/{run_id}", status_code=204)
async def delete_recommendation_run(run_id: int):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM recommendation_runs WHERE id = $1", run_id)
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Recommendation run not found")


# Add recommendations router
recommendations_router = APIRouter(prefix="/recommendations", tags=["recommendations"])

@recommendations_router.post("/", response_model=RecommendationResponse, status_code=201)
async def create_recommendation(rec: RecommendationCreate):
    pool = await get_db_pool()
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO recommendations (run_id, paper_id, score, rank, summary)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, run_id, paper_id, score, rank, summary, created_at
                """,
                rec.run_id, rec.paper_id, rec.score, rec.rank, rec.summary
            )
            return dict(row)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@recommendations_router.get("/", response_model=List[RecommendationResponse])
async def get_recommendations(run_id: Optional[int] = Query(None)):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        if run_id is not None:
            rows = await conn.fetch(
                "SELECT id, run_id, paper_id, score, rank, summary, created_at FROM recommendations WHERE run_id = $1 ORDER BY rank",
                run_id
            )
        else:
            rows = await conn.fetch(
                "SELECT id, run_id, paper_id, score, rank, summary, created_at FROM recommendations ORDER BY created_at DESC"
            )
        return [dict(row) for row in rows]

@recommendations_router.get("/{rec_id}", response_model=RecommendationResponse)
async def get_recommendation(rec_id: int):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, run_id, paper_id, score, rank, summary, created_at FROM recommendations WHERE id = $1",
            rec_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        return dict(row)

@recommendations_router.get("/run/{run_id}/with-papers")
async def get_recommendations_with_papers(run_id: int, limit: int = Query(50, ge=1, le=100)):
    """Get recommendations with full paper details"""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT 
                r.id, r.run_id, r.paper_id, r.score, r.rank, r.summary, r.created_at,
                p.arxiv_id, p.title, p.abstract, p.metadata, p.source,
                s.summary_text
            FROM recommendations r
            JOIN papers p ON r.paper_id = p.id
            LEFT JOIN summaries s ON s.paper_id = p.id
            WHERE r.run_id = $1
            ORDER BY r.rank
            LIMIT $2
            """,
            run_id, limit
        )
        
        results = []
        for row in rows:
            result = dict(row)
            if result.get('metadata'):
                result['metadata'] = json.loads(result['metadata'])
            results.append(result)
        
        return results

@recommendations_router.delete("/{rec_id}", status_code=204)
async def delete_recommendation(rec_id: int):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM recommendations WHERE id = $1", rec_id)
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Recommendation not found")


@recommendations_router.get("/profile/{profile_id}")
async def get_recommendations_by_profile(profile_id: int, limit: int = Query(100)):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # First, get the corpus associated with this profile
        profile = await conn.fetchrow(
            "SELECT user_id FROM profiles WHERE id = $1",
            profile_id
        )
        
        if not profile:
            return []
        
        user_id = profile['user_id']
        
        # Get the user corpus for this profile
        corpus_name = f"user_{user_id}_profile_{profile_id}"
        
        corpus = await conn.fetchrow(
            "SELECT id FROM corpora WHERE user_id = $1 AND name = $2",
            user_id, corpus_name
        )
        
        if not corpus:
            return []
        
        user_corpus_id = corpus['id']
        
        # Get recommendations with summaries
        rows = await conn.fetch(
            """
            SELECT 
                r.id, r.run_id, r.paper_id, r.score, r.rank, r.created_at,
                p.arxiv_id, p.title, p.abstract, p.metadata,
                s.summary_text
            FROM recommendations r
            JOIN recommendation_runs rr ON r.run_id = rr.id
            JOIN papers p ON r.paper_id = p.id
            LEFT JOIN summaries s ON s.paper_id = p.id
            WHERE rr.user_corpus_id = $1
            ORDER BY r.created_at DESC, r.rank
            LIMIT $2
            """,
            user_corpus_id, limit
        )
        
        return [dict(row) for row in rows]