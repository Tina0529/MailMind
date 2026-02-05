"""
Replies router - API endpoints for reply generation and sending
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from models.database import Email, Reply, async_session
from models.schemas import (
    GenerateReplyRequest,
    GenerateReplyResponse,
    SendReplyRequest,
    SendReplyResponse
)
from services.skill_service import SkillService
from services.zoho_service import ZohoMailService
from services.zoho_oauth_service import zoho_oauth_service
from config import settings


replies_router = APIRouter()

skill_service = SkillService()
zoho_service = ZohoMailService()


def get_email_sender():
    """Get appropriate email sender (OAuth or SMTP)"""
    # Try OAuth first
    if zoho_oauth_service.load_tokens():
        success, _ = zoho_oauth_service.test_connection()
        if success:
            return zoho_oauth_service
    # Fall back to SMTP
    return zoho_service


@replies_router.post("/generate", response_model=GenerateReplyResponse)
async def generate_reply(request: GenerateReplyRequest):
    """Generate a reply for an email using AI"""
    async with async_session() as session:
        # Get email
        result = await session.execute(
            select(Email).where(Email.id == request.email_id)
        )
        email = result.scalar_one_or_none()

        if not email:
            raise HTTPException(status_code=404, detail="Email not found")

        # Match skills
        email_content = f"{email.subject}\n\n{email.body}"
        matched_skills = await skill_service.match_skills(email_content)

        if not matched_skills:
            # Generate generic response
            ai_draft = f"""Dear {email.from_name or 'Customer'},

Thank you for your email regarding "{email.subject}".

We have received your inquiry and will get back to you shortly.

Best regards
{settings.ZOHO_EMAIL.split('@')[0].title()}"""

            # Create reply record
            reply = Reply(
                id=str(uuid.uuid4()),
                email_id=str(email.id),
                ai_draft=ai_draft,
                sent=False
            )
            session.add(reply)
            await session.commit()

            return GenerateReplyResponse(
                email_id=str(email.id),
                reply_id=str(reply.id),
                ai_draft=ai_draft,
                matched_skills=[],
                confidence=0.3,
                requires_review=True
            )

        # Use matched skill to generate reply
        skill = matched_skills[0]
        rules = skill.get("rules", [])

        if rules and rules[0].get("response_template"):
            # Use template from best matching rule
            template = rules[0]["response_template"]
            ai_draft = template.replace("{{customer_name}}", email.from_name or "Customer")
            ai_draft = ai_draft.replace("{{customer_name}}", email.from_name or "Customer")
            ai_draft = ai_draft.replace("{customer_name}", email.from_name or "Customer")
            ai_draft = ai_draft.replace("{{{customer_name}}}", email.from_name or "Customer")
            ai_draft = ai_draft.replace("{{company_name}}", "We")
            ai_draft = ai_draft.replace("{company_name}", "We")
            ai_draft = ai_draft.replace("{{{company_name}}}", "We")
        else:
            # Generate with Claude if available
            if settings.ANTHROPIC_API_KEY:
                ai_draft = await generate_with_claude(email, skill)
            else:
                ai_draft = f"""Dear {email.from_name or 'Customer'},

Regarding your inquiry about "{email.subject}", we are looking into it.

Our team has identified this as a {skill.get('category')} matter and will assist you shortly.

Best regards"""

        # Create reply record
        reply = Reply(
            id=str(uuid.uuid4()),
            email_id=str(email.id),
            ai_draft=ai_draft,
            sent=False
        )
        session.add(reply)

        # Update email as processed
        email.processed = True
        await session.commit()

        # Increment skill usage
        await skill_service.increment_usage(skill["id"])

        return GenerateReplyResponse(
            email_id=str(email.id),
            reply_id=str(reply.id),
            ai_draft=ai_draft,
            matched_skills=[s["name_en"] for s in matched_skills],
            confidence=len(matched_skills) * 0.2,
            requires_review=True
        )


async def generate_with_claude(email: Email, skill: dict) -> str:
    """Generate reply using Claude"""
    import httpx

    base_url = settings.ANTHROPIC_BASE_URL.rstrip('/')
    api_url = f"{base_url}/messages"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": settings.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01"
    }

    rules_text = "\n".join([
        f"- {r.get('name')}: {r.get('response_template', '')}"
        for r in skill.get("rules", [])
    ])

    prompt = f"""Generate a professional email reply based on the following:

Customer Email:
From: {email.from_name} ({email.from_address})
Subject: {email.subject}
Content: {email.body[:1000]}

Matched Skill: {skill.get('name')}
Category: {skill.get('category')}

Relevant Rules:
{rules_text}

Generate a helpful, professional reply. Keep it concise and friendly. Only return the email content, no explanation."""

    try:
        data = {
            "model": "claude-3-5-haiku-20241022",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(api_url, headers=headers, json=data)
        
        if response.status_code == 200:
            result_json = response.json()
            return result_json["content"][0]["text"]
        else:
            print(f"Error calling Claude API: {response.status_code}")
            return f"Dear {email.from_name or 'Customer'},\n\nThank you for your inquiry. We are looking into it and will get back to you shortly.\n\nBest regards"
    except Exception as e:
        print(f"Error generating reply: {e}")
        return f"Dear {email.from_name or 'Customer'},\n\nThank you for your inquiry. We are looking into it and will get back to you shortly.\n\nBest regards"


@replies_router.post("/send", response_model=SendReplyResponse)
async def send_reply(request: SendReplyRequest):
    """Send a reply via Zoho Mail"""
    async with async_session() as session:
        from sqlalchemy import select

        # Get reply
        result = await session.execute(
            select(Reply).where(Reply.id == request.reply_id)
        )
        reply = result.scalar_one_or_none()

        if not reply:
            raise HTTPException(status_code=404, detail="Reply not found")

        # Get email
        result = await session.execute(
            select(Email).where(Email.id == reply.email_id)
        )
        email = result.scalar_one_or_none()

        if not email:
            raise HTTPException(status_code=404, detail="Email not found")

        # Determine content to send
        content = request.content or reply.human_edited or reply.ai_draft

        # Get email sender (OAuth or SMTP)
        sender = get_email_sender()

        # Send via Zoho
        success = sender.send_email(
            to_address=email.from_address,
            subject=f"Re: {email.subject}",
            body=content,
            in_reply_to=email.zoho_id
        )

        if success:
            reply.sent = True
            reply.sent_at = datetime.utcnow()

            # Save edited content if provided
            if request.content and request.content != reply.ai_draft:
                reply.human_edited = request.content

            await session.commit()

            return SendReplyResponse(
                success=True,
                message="Reply sent successfully",
                sent_at=reply.sent_at
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to send email")


@replies_router.post("/{reply_id}/feedback")
async def submit_feedback(reply_id: str, feedback: dict):
    """Submit feedback on a reply (for evolution learning)"""
    async with async_session() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(Reply).where(Reply.id == reply_id)
        )
        reply = result.scalar_one_or_none()

        if not reply:
            raise HTTPException(status_code=404, detail="Reply not found")

        # Save human edited version
        if feedback.get("edited_content"):
            reply.human_edited = feedback["edited_content"]
            await session.commit()

        return {"status": "success", "message": "Feedback recorded"}
