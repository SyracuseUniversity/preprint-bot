from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from database import get_db_pool
from services.email_service import send_recommendations_digest, send_email

router = APIRouter(prefix="/emails", tags=["emails"])


class DigestRequest(BaseModel):
    user_id: int
    profile_id: int
    run_date: Optional[str] = None


@router.post("/send-digest")
async def send_digest(req: DigestRequest):
    pool = await get_db_pool()
    run_date = req.run_date or str(date.today())
    run_date_obj = datetime.strptime(run_date, "%Y-%m-%d").date()

    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id, email, name FROM users WHERE id = $1", req.user_id
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        profile = await conn.fetchrow(
            "SELECT id, name, email_notify, top_x FROM profiles WHERE id = $1 AND user_id = $2",
            req.profile_id, req.user_id
        )
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")

        if not profile["email_notify"]:
            return {"status": "skipped", "reason": "email_notify is disabled for this profile"}

        top_x = profile["top_x"] or 10

        rows = await conn.fetch(
            """
            SELECT p.arxiv_id, p.title, p.abstract, r.score, r.summary, s.summary_text
            FROM profile_recommendations pr
            JOIN recommendations r ON r.id = pr.recommendation_id
            JOIN recommendation_runs rr ON rr.id = r.run_id
            JOIN papers p ON p.id = r.paper_id
            LEFT JOIN summaries s ON s.paper_id = p.id
            WHERE pr.profile_id = $1
            AND rr.target_date = $2
            ORDER BY r.score DESC
            LIMIT $3
            """,
            req.profile_id, run_date_obj, top_x
        )

        if not rows:
            return {"status": "skipped", "reason": "no recommendations found for this date"}

        papers = [dict(r) for r in rows]

    success, subject, html_body = await run_in_threadpool(
        send_recommendations_digest,
        to_address=user["email"],
        profile_name=profile["name"],
        papers=papers,
        run_date=run_date,
    )

    status = "sent" if success else "failed"

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO email_logs (user_id, profile_id, subject, body, status)
            VALUES ($1, $2, $3, $4, $5)
            """,
            req.user_id, req.profile_id, subject, html_body, status
        )

    if not success:
        raise HTTPException(status_code=500, detail="Email sending failed")

    return {"status": "sent", "to": user["email"], "papers_count": len(papers)}


@router.post("/test-email")
async def test_email(to_email: str):
    success = await run_in_threadpool(
        send_email,
        to_address=to_email,
        subject="Preprint Bot — Test Email",
        html_body="<p>If you received this, your SMTP relay is configured correctly.</p>"
    )
    if not success:
        raise HTTPException(status_code=500, detail="Test email failed")
    return {"status": "sent", "to": to_email}