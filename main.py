from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import get_db_pool, close_db_pool

# Import route modules
from routes import users, papers, corpora, sections, embeddings
from routes.recommendations import router as recommendation_runs_router, recommendations_router

# Optional route imports
try:
    from routes import profiles, profile_corpora, summaries, profile_recommendations, email_logs
    HAS_OPTIONAL_ROUTES = True
except ImportError:
    HAS_OPTIONAL_ROUTES = False
    print("Warning: Some optional route modules not found. Core functionality will work.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    print("Starting Preprint Bot API...")
    await get_db_pool()
    print("Database connection pool created")
    
    yield
    
    # Shutdown
    print("Shutting down Preprint Bot API...")
    await close_db_pool()
    print("Database connections closed")


# Create FastAPI app
app = FastAPI(
    title="Preprint Bot API",
    description="API for managing academic paper recommendations with vector search",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include core routers
app.include_router(users.router)
app.include_router(corpora.router)
app.include_router(papers.router)
app.include_router(sections.router)
app.include_router(embeddings.router)
app.include_router(recommendation_runs_router)
app.include_router(recommendations_router)

# Include optional routers if available
if HAS_OPTIONAL_ROUTES:
    try:
        app.include_router(profiles.router)
        app.include_router(profile_corpora.router)
        app.include_router(summaries.router)
        app.include_router(profile_recommendations.router)
        app.include_router(email_logs.router)
        print("✓ All route modules loaded")
    except Exception as e:
        print(f"⚠ Warning loading optional routes: {e}")


@app.get("/")
async def root():
    """Root endpoint with API information"""
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
    """Health check endpoint"""
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
    """Get database statistics"""
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