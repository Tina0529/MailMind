"""
Agent Tools - Define tools for EmailAssistantAgent
Using Claude Agent SDK's @tool decorator
"""
from typing import Dict, List, Optional, Any
from claude_agent_sdk import tool


# Database session and services will be injected
_db_session = None
_skill_service = None


def set_services(db_session, skill_service):
    """Set service instances for tools to use"""
    global _db_session, _skill_service
    _db_session = db_session
    _skill_service = skill_service


@tool("get_email", "Get email details by ID", {
    "email_id": str
})
async def get_email(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get email details from database"""
    from models.database import Email, async_session
    from sqlalchemy import select
    
    email_id = args.get("email_id")
    
    async with async_session() as session:
        result = await session.execute(
            select(Email).where(Email.id == email_id)
        )
        email = result.scalar_one_or_none()
        
        if not email:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error: Email with ID {email_id} not found"
                }]
            }
        
        return {
            "content": [{
                "type": "text",
                "text": f"""Email Details:
- ID: {email.id}
- From: {email.from_name} <{email.from_address}>
- Subject: {email.subject}
- Category: {email.category or 'Not classified'}
- Is Customer Service: {email.is_customer_service}
- Body:
{email.body[:2000]}"""
            }]
        }


@tool("get_skills", "Get all available skills from the database", {})
async def get_skills(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get all skills from database"""
    from services.skill_service import SkillService
    
    skill_service = SkillService()
    skills = await skill_service.get_all_skills()
    
    if not skills:
        return {
            "content": [{
                "type": "text",
                "text": "No skills found in database. Need to run learning first."
            }]
        }
    
    skills_text = "\n".join([
        f"- {s.name} ({s.name_en}): {s.description or 'No description'} | Keywords: {', '.join(s.trigger_keywords or [])}"
        for s in skills
    ])
    
    return {
        "content": [{
            "type": "text",
            "text": f"Available Skills ({len(skills)} total):\n{skills_text}"
        }]
    }


@tool("match_skill", "Match the best skill for given email content", {
    "email_content": str,
    "category": str
})
async def match_skill(args: Dict[str, Any]) -> Dict[str, Any]:
    """Match skills to email content"""
    from services.skill_service import SkillService
    
    email_content = args.get("email_content", "")
    category = args.get("category")
    
    skill_service = SkillService()
    matched = await skill_service.match_skills(email_content, category)
    
    if not matched:
        return {
            "content": [{
                "type": "text",
                "text": "No matching skills found for this email content."
            }]
        }
    
    # Return best match
    best = matched[0]
    return {
        "content": [{
            "type": "text",
            "text": f"""Best Matching Skill:
- Name: {best['name']} ({best['name_en']})
- Category: {best['category']}
- Matched Rules: {len(best.get('rules', []))}

Rules:
{chr(10).join([f"  - {r.get('name')}: Priority {r.get('priority', 0)}" for r in best.get('rules', [])])}"""
        }]
    }


@tool("get_skill_template", "Get response template from a skill", {
    "skill_name_en": str
})
async def get_skill_template(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get response template from a skill"""
    from services.skill_service import SkillService
    from models.database import Skill, async_session
    from sqlalchemy import select
    
    skill_name_en = args.get("skill_name_en")
    
    async with async_session() as session:
        result = await session.execute(
            select(Skill).where(Skill.name_en == skill_name_en)
        )
        skill = result.scalar_one_or_none()
        
        if not skill:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Skill '{skill_name_en}' not found"
                }]
            }
        
        rules = skill.rules or []
        templates = []
        for rule in rules:
            template = rule.get("response_template")
            if template:
                templates.append(f"Rule '{rule.get('name')}':\n{template}")
        
        if not templates:
            return {
                "content": [{
                    "type": "text",
                    "text": f"No response templates found in skill '{skill_name_en}'"
                }]
            }
        
        return {
            "content": [{
                "type": "text",
                "text": f"Response Templates for '{skill.name}':\n\n" + "\n\n---\n\n".join(templates)
            }]
        }


@tool("classify_email", "Classify an email into a category", {
    "email_id": str
})
async def classify_email(args: Dict[str, Any]) -> Dict[str, Any]:
    """Classify email using AI"""
    from models.database import Email, async_session
    from services.email_classifier import EmailClassifierService
    from sqlalchemy import select
    
    email_id = args.get("email_id")
    
    async with async_session() as session:
        result = await session.execute(
            select(Email).where(Email.id == email_id)
        )
        email = result.scalar_one_or_none()
        
        if not email:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Email {email_id} not found"
                }]
            }
        
        classifier = EmailClassifierService()
        classification = await classifier.classify_email({
            "from_address": email.from_address,
            "subject": email.subject,
            "body": email.body
        })
        
        # Update email
        email.is_customer_service = classification.get("is_customer_service", False)
        email.category = classification.get("category")
        await session.commit()
        
        return {
            "content": [{
                "type": "text",
                "text": f"""Email Classification Result:
- Is Customer Service: {classification.get('is_customer_service')}
- Category: {classification.get('category')}
- Confidence: {classification.get('confidence')}
- Reasoning: {classification.get('reasoning')}"""
            }]
        }


@tool("generate_reply", "Generate a reply for an email using a template or AI", {
    "email_id": str,
    "template": str,
    "customer_name": str
})
async def generate_reply(args: Dict[str, Any]) -> Dict[str, Any]:
    """Generate reply using template or AI"""
    from models.database import Email, async_session
    from sqlalchemy import select
    import httpx
    from config import settings
    
    email_id = args.get("email_id")
    template = args.get("template", "")
    customer_name = args.get("customer_name", "Customer")
    
    async with async_session() as session:
        result = await session.execute(
            select(Email).where(Email.id == email_id)
        )
        email = result.scalar_one_or_none()
        
        if not email:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Email {email_id} not found"
                }]
            }
    
    # If template provided, use it
    if template:
        reply = template.replace("{{customer_name}}", customer_name)
        reply = reply.replace("{customer_name}", customer_name)
        return {
            "content": [{
                "type": "text",
                "text": f"Generated Reply (from template):\n\n{reply}"
            }]
        }
    
    # Otherwise generate with AI
    base_url = settings.ANTHROPIC_BASE_URL.rstrip('/')
    api_url = f"{base_url}/messages"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": settings.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01"
    }
    
    prompt = f"""Generate a professional email reply:

Original Email:
From: {email.from_name} <{email.from_address}>
Subject: {email.subject}
Body: {email.body[:1500]}

Generate a helpful, professional reply. Be concise and friendly. Only return the email content."""

    data = {
        "model": "claude-3-5-haiku-20241022",
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(api_url, headers=headers, json=data)
        
        if response.status_code == 200:
            result_json = response.json()
            reply_text = result_json["content"][0]["text"]
            return {
                "content": [{
                    "type": "text",
                    "text": f"Generated Reply (AI):\n\n{reply_text}"
                }]
            }
    except Exception as e:
        pass
    
    return {
        "content": [{
            "type": "text",
            "text": f"Dear {customer_name},\n\nThank you for your email. We will get back to you shortly.\n\nBest regards"
        }]
    }


@tool("save_reply", "Save a reply draft to the database", {
    "email_id": str,
    "reply_content": str
})
async def save_reply(args: Dict[str, Any]) -> Dict[str, Any]:
    """Save reply to database"""
    from models.database import Reply, async_session
    import uuid
    
    email_id = args.get("email_id")
    reply_content = args.get("reply_content")
    
    async with async_session() as session:
        reply = Reply(
            id=str(uuid.uuid4()),
            email_id=email_id,
            ai_draft=reply_content,
            sent=False
        )
        session.add(reply)
        await session.commit()
        
        return {
            "content": [{
                "type": "text",
                "text": f"Reply saved successfully with ID: {reply.id}"
            }]
        }


# Export all tools for MCP server
ALL_TOOLS = [
    get_email,
    get_skills,
    match_skill,
    get_skill_template,
    classify_email,
    generate_reply,
    save_reply
]
