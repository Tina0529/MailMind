"""
Skills router - API endpoints for skill management
"""
import httpx
from fastapi import APIRouter, HTTPException, BackgroundTasks
from sqlalchemy import select

from models.database import async_session
from models.schemas import (
    SkillListResponse,
    SkillResponse,
    LearnRequest,
    LearnResponse
)
from services.skill_service import SkillService
from services.email_classifier import EmailClassifierService
from config import settings


skills_router = APIRouter()

skill_service = SkillService()


@skills_router.get("", response_model=SkillListResponse)
async def get_skills(active_only: bool = True):
    """Get all skills"""
    skills = await skill_service.get_all_skills(active_only=active_only)
    categories = await skill_service.get_categories()

    return SkillListResponse(
        skills=skills,
        total=len(skills),
        categories=categories
    )


@skills_router.get("/{skill_id}", response_model=SkillResponse)
async def get_skill(skill_id: str):
    """Get a specific skill"""
    skill = await skill_service.get_skill(skill_id)

    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    return skill


@skills_router.get("/{skill_id}/source-emails")
async def get_skill_source_emails(skill_id: str, limit: int = 20):
    """获取 Skill 的源邮件列表 - 用于追溯 Skill 是基于哪些邮件生成的"""
    from models.database import SkillSourceEmail, Email, Skill
    
    async with async_session() as session:
        # 验证 Skill 存在
        skill_result = await session.execute(
            select(Skill).where(Skill.id == skill_id)
        )
        skill = skill_result.scalar_one_or_none()
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")
        
        # 获取源邮件关联
        result = await session.execute(
            select(SkillSourceEmail, Email)
            .join(Email, SkillSourceEmail.email_id == Email.id)
            .where(SkillSourceEmail.skill_id == skill_id)
            .order_by(SkillSourceEmail.created_at.desc())
            .limit(limit)
        )
        rows = result.all()
        
        source_emails = []
        for source, email in rows:
            source_emails.append({
                "id": source.id,
                "email_id": email.id,
                "from_address": email.from_address,
                "from_name": email.from_name,
                "subject": email.subject,
                "received_at": email.received_at.isoformat() if email.received_at else None,
                "category": email.category,
                "contribution_type": source.contribution_type,
                "contribution_detail": source.contribution_detail,
                "linked_at": source.created_at.isoformat() if source.created_at else None
            })
        
        return {
            "skill_id": skill_id,
            "skill_name": skill.name,
            "total_source_emails": len(source_emails),
            "source_emails": source_emails
        }


@skills_router.post("/learn", response_model=LearnResponse)
async def learn_skills(request: LearnRequest, background_tasks: BackgroundTasks):
    """Trigger learning from emails"""
    # Start learning in background
    background_tasks.add_task(run_learning, request.email_count, request.force)

    return LearnResponse(
        status="started",
        message="Learning process started. This may take several minutes.",
        emails_processed=0,
        customer_service_emails=0,
        skills_created=0,
        skills_updated=0
    )


async def run_learning(email_count: int = 100, force: bool = False):
    """Run the learning process"""
    from services.zoho_service import ZohoMailService
    from models.database import Email, Skill, SkillSourceEmail, async_session
    from models.schemas import SkillCreate
    from anthropic import Anthropic
    import json
    import uuid

    # Get customer service emails
    async with async_session() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(Email)
            .where(Email.is_customer_service == True)
            .order_by(Email.received_at.desc())
            .limit(email_count)
        )
        emails = result.scalars().all()

    if not emails:
        return

    # Group emails by category
    by_category = {}
    for email in emails:
        cat = email.category or "other"
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(email)

    # Use Claude to extract skills from each category
    if not settings.ANTHROPIC_API_KEY:
        print("DEBUG: No ANTHROPIC_API_KEY configured, skipping learning")
        return

    api_url = "https://api.anthropic.com/v1/messages"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": settings.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01"
    }
    
    skills_created = 0
    skills_updated = 0

    for category, category_emails in by_category.items():
        # Format emails for analysis (keep track of IDs for source tracking)
        conversations = []
        source_email_ids = []  # 记录用于生成此 Skill 的邮件 ID
        for email in category_emails[:20]:  # Limit per category
            conversations.append({
                "from": email.from_address,
                "subject": email.subject,
                "body": email.body[:1000]  # Truncate for API
            })
            source_email_ids.append(email.id)

        prompt = f"""You are analyzing customer service emails to extract skills and response patterns.

Category: {category}

Here are {len(conversations)} example emails:

{json.dumps(conversations, ensure_ascii=False, indent=2)}

Extract the common patterns and create a skill with rules. Respond in JSON format:

{{
    "name": "Skill Name (Chinese)",
    "name_en": "skill-name-en",
    "category": "{category}",
    "description": "Brief description",
    "trigger_keywords": ["keyword1", "keyword2"],
    "rules": [
        {{
            "rule_id": "rule_1",
            "name": "Rule Name",
            "trigger_keywords": ["trigger1"],
            "conditions": ["condition1"],
            "action_steps": ["step1", "step2"],
            "response_template": "Response template with {{{{customer_name}}}} placeholder",
            "priority": 10
        }}
    ]
}}

Only return the JSON, nothing else."""

        try:
            data = {
                "model": "claude-3-5-haiku-20241022",
                "max_tokens": 2000,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(api_url, headers=headers, json=data)
            
            if response.status_code != 200:
                print(f"Error calling Claude API for {category}: {response.status_code} - {response.text}")
                continue
                
            result_json = response.json()
            result_text = result_json["content"][0]["text"]

            # Extract JSON
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            skill_data = json.loads(result_text)

            # Create or update skill
            existing = await skill_service.get_all_skills()
            existing_skill = next((s for s in existing if s.name_en == skill_data.get("name_en")), None)

            if existing_skill and not force:
                skills_updated += 1
                skill_id = existing_skill.id
            else:
                skill_create = SkillCreate(**skill_data)
                new_skill = await skill_service.create_skill(skill_create)
                skills_created += 1
                skill_id = new_skill.id if new_skill else None

            # 记录源邮件关联
            if skill_id and source_email_ids:
                async with async_session() as session:
                    for email_id in source_email_ids:
                        # 检查是否已存在关联
                        existing_link = await session.execute(
                            select(SkillSourceEmail).where(
                                SkillSourceEmail.skill_id == skill_id,
                                SkillSourceEmail.email_id == email_id
                            )
                        )
                        if not existing_link.scalar_one_or_none():
                            source_record = SkillSourceEmail(
                                id=str(uuid.uuid4()),
                                skill_id=skill_id,
                                email_id=email_id,
                                contribution_type="initial_learning",
                                contribution_detail=f"Used for learning category: {category}"
                            )
                            session.add(source_record)
                    await session.commit()
                    print(f"DEBUG: Recorded {len(source_email_ids)} source emails for skill: {skill_data.get('name')}")

        except Exception as e:
            print(f"Error extracting skill for {category}: {e}")
            continue

    # Save to file
    await skill_service.save_to_file()


@skills_router.post("/export")
async def export_skills():
    """Export skills to JSON file"""
    await skill_service.save_to_file()
    return {"status": "success", "message": "Skills exported to data/skills.json"}


@skills_router.post("/import")
async def import_skills():
    """Import skills from JSON file"""
    count = await skill_service.load_from_file()
    return {"status": "success", "message": f"Imported {count} skills"}
