"""
Status router - API endpoints for system status
"""
from fastapi import APIRouter
from sqlalchemy import select, func

from models.database import Email, Skill, async_session
from models.schemas import StatusResponse
from services.zoho_service import ZohoMailService
from config import settings


status_router = APIRouter()


@status_router.get("", response_model=StatusResponse)
async def get_status():
    """Get system status"""
    # Check Zoho connection
    zoho_service = ZohoMailService()
    zoho_connected, _ = zoho_service.test_connection()

    async with async_session() as session:
        # Get counts
        emails_result = await session.execute(select(func.count(Email.id)))
        total_emails = emails_result.scalar() or 0

        skills_result = await session.execute(select(func.count(Skill.id)))
        total_skills = skills_result.scalar() or 0

        # Get pending replies
        from models.database import Reply
        pending_result = await session.execute(
            select(func.count(Reply.id)).where(Reply.sent == False)
        )
        pending_replies = pending_result.scalar() or 0

    return StatusResponse(
        status="running",
        zoho_connected=zoho_connected,
        zoho_email=settings.ZOHO_EMAIL,
        total_emails=total_emails,
        total_skills=total_skills,
        pending_replies=pending_replies
    )
