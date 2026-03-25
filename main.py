from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import get_db_pool, close_db_pool

from routes import users, papers, corpora, sections, embeddings, auth, uploads
import routes.recommendations as recommendations

try:
    from routes import profiles, profile_corpora, summaries, profile_recommendations, email_logs, emails
    HAS_OPTIONAL_ROUTES = True
except ImportError:
    HAS_OPTIONAL_ROUTES = False
    print("Warning: Some optional route modules not found. Core functionality will work.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting Preprint Bot API...")
    await get_db_pool()
    print("Database connection pool created")
    
    yield
    
    print("Shutting down Preprint Bot API...")
    await close_db_pool()
    print("Database connections closed")


app = FastAPI(
    title="Preprint Bot API",
    description="API for managing academic paper recommendations with vector search",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(papers.router)
app.include_router(corpora.router)
app.include_router(sections.router)
app.include_router(embeddings.router)
app.include_router(recommendations.router)
app.include_router(recommendations.recommendations_router)
app.include_router(summaries.router)
app.include_router(auth.router)
app.include_router(uploads.router)

if HAS_OPTIONAL_ROUTES:
    try:
        app.include_router(profiles.router)
        app.include_router(profile_corpora.router)
        app.include_router(summaries.router)
        app.include_router(profile_recommendations.router)
        app.include_router(email_logs.router)
        app.include_router(emails.router)
        print("All route modules loaded")
    except Exception as e:
        print(f"Warning loading optional routes: {e}")


@app.get("/")
async def root():
    return {
        "message": "Preprint Bot - Academic Paper Recommendation System",
        "version": "2.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "status": "operational",
        "features": [
            "arXiv paper fetching and storage",
            "PDF parsing with GROBID integration",
            "Semantic embedding generation",
            "Vector similarity search",
            "Personalized recommendations",
            "PostgreSQL with pgvector"
        ]
    }


@app.get("/health")
async def health_check():
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        
        return {
            "status": "healthy",
            "database": "connected",
            "api": "operational"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }


@app.get("/stats")
async def get_stats():
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            users_count = await conn.fetchval("SELECT COUNT(*) FROM users")
            papers_count = await conn.fetchval("SELECT COUNT(*) FROM papers")
            embeddings_count = await conn.fetchval("SELECT COUNT(*) FROM embeddings")
            recommendations_count = await conn.fetchval("SELECT COUNT(*) FROM recommendations")
            
            return {
                "users": users_count,
                "papers": papers_count,
                "embeddings": embeddings_count,
                "recommendations": recommendations_count
            }
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )