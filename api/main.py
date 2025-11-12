from fastapi import FastAPI
from contextlib import asynccontextmanager
from database import get_db_pool, close_db_pool
from routes import (
    users, profiles, corpora, profile_corpora, papers,
    sections, summaries, embeddings, recommendation_runs,
    recommendations, profile_recommendations, email_logs
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await get_db_pool()
    yield
    # Shutdown
    await close_db_pool()

app = FastAPI(
    title="Preprint Bot API",
    description="API for managing academic paper recommendations with vector search",
    version="1.0.0",
    lifespan=lifespan
)

# Include all routers
app.include_router(users.router)
app.include_router(profiles.router)
app.include_router(corpora.router)
app.include_router(profile_corpora.router)
app.include_router(papers.router)
app.include_router(sections.router)
app.include_router(summaries.router)
app.include_router(embeddings.router)
app.include_router(recommendation_runs.router)
app.include_router(recommendations.router)
app.include_router(profile_recommendations.router)
app.include_router(email_logs.router)

@app.get("/")
async def root():
    return {
        "message": "Paper Recommendation System API",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
