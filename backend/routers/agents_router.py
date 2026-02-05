"""
Agents router - API endpoints for agent operations
Provides unified access to Learning, Execution, and Evolution agents
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from sqlalchemy import select, func

from models.database import Email, Skill, Reply, async_session
from models.schemas import (
    AgentLearnRequest,
    AgentLearnResponse,
    AgentExecuteRequest,
    AgentExecuteResponse,
    AgentEvolveRequest,
    AgentEvolveResponse,
    AgentStatusResponse,
    MatchedSkillDetail,
    SkillChange
)
from agents.learning_agent import learning_agent
from agents.execution_agent import execution_agent
from agents.evolution_agent import evolution_agent


agents_router = APIRouter()

# Track background jobs
_background_jobs = {}


@agents_router.post("/learn", response_model=AgentLearnResponse)
async def trigger_learning(
    request: AgentLearnRequest,
    background_tasks: BackgroundTasks
):
    """
    Trigger the Learning Agent to analyze emails and create/update Skills.

    The learning process runs in the background. Use the returned job_id
    to check status via GET /api/agents/status.
    """
    job_id = str(uuid.uuid4())

    # Store job status
    _background_jobs[job_id] = {
        "status": "started",
        "started_at": datetime.utcnow(),
        "agent": "learning"
    }

    # Run learning in background
    background_tasks.add_task(
        _run_learning_background,
        job_id,
        request.email_count,
        request.force
    )

    return AgentLearnResponse(
        job_id=job_id,
        status="started",
        message=f"Learning process started. Analyzing up to {request.email_count} emails.",
        summary=None
    )


async def _run_learning_background(job_id: str, email_count: int, force: bool):
    """Background task for learning"""
    try:
        result = await learning_agent.run({
            "email_count": email_count,
            "force": force
        })

        _background_jobs[job_id] = {
            "status": result.status,
            "completed_at": datetime.utcnow(),
            "result": result.data,
            "errors": result.errors
        }
    except Exception as e:
        _background_jobs[job_id] = {
            "status": "failed",
            "completed_at": datetime.utcnow(),
            "errors": [str(e)]
        }


@agents_router.post("/execute", response_model=AgentExecuteResponse)
async def execute_email(request: AgentExecuteRequest):
    """
    Execute the Execution Agent on a specific email.

    This will:
    1. Classify the email (if not already classified)
    2. Match relevant Skills
    3. Generate an AI reply draft
    4. Return match details and confidence score

    If confidence is too low, the email will be marked for escalation.
    """
    result = await execution_agent.run({
        "email_id": request.email_id,
        "auto_send": request.auto_send
    })

    if not result.success:
        raise HTTPException(
            status_code=500,
            detail=result.errors[0] if result.errors else "Execution failed"
        )

    data = result.data

    # Convert matched skills to response format
    matched_skills = [
        MatchedSkillDetail(
            skill_id=s.get("skill_id", ""),
            skill_name=s.get("skill_name", ""),
            skill_name_en=s.get("skill_name_en", ""),
            category=s.get("category", ""),
            matched_keywords=s.get("matched_keywords", []),
            matched_rules=s.get("matched_rules", []),
            confidence=s.get("confidence", 0.0)
        )
        for s in data.get("matched_skills", [])
    ]

    return AgentExecuteResponse(
        status=data.get("status", result.status),
        email_id=data.get("email_id", request.email_id),
        reply_id=data.get("reply_id"),
        ai_draft=data.get("ai_draft"),
        matched_skills=matched_skills,
        confidence=data.get("confidence", 0.0),
        requires_escalation=data.get("requires_escalation", False),
        escalation_reason=data.get("escalation_reason")
    )


@agents_router.post("/evolve", response_model=AgentEvolveResponse)
async def evolve_skill(request: AgentEvolveRequest):
    """
    Trigger the Evolution Agent to learn from human edits.

    This will:
    1. Compare AI draft with human-edited version
    2. Analyze differences using Claude
    3. Identify improvements (new keywords, rules, templates)
    4. Apply improvements to related Skills
    5. Record change history
    """
    result = await evolution_agent.run({
        "reply_id": request.reply_id
    })

    if not result.success:
        raise HTTPException(
            status_code=500,
            detail=result.errors[0] if result.errors else "Evolution failed"
        )

    data = result.data

    # Convert changes to response format
    changes = [
        SkillChange(
            change_type=c.get("change_type", ""),
            skill_id=c.get("skill_id", ""),
            skill_name=c.get("skill_name", ""),
            detail=c.get("detail", "")
        )
        for c in data.get("changes", [])
    ]

    return AgentEvolveResponse(
        status=result.status,
        reply_id=data.get("reply_id", request.reply_id),
        changes=changes,
        message=data.get("message", data.get("analysis_summary", ""))
    )


@agents_router.get("/status", response_model=AgentStatusResponse)
async def get_agent_status():
    """
    Get the current status of all agents and system statistics.

    Returns:
    - System health status
    - Status of each agent (Learning, Execution, Evolution)
    - Skill library statistics
    - Email processing statistics
    """
    # Get agent statuses
    agents_status = {
        "learning": learning_agent.get_status(),
        "execution": execution_agent.get_status(),
        "evolution": evolution_agent.get_status()
    }

    # Determine system health
    all_ready = all(
        a.get("status") == "ready" for a in agents_status.values()
    )
    system_status = "healthy" if all_ready else "busy"

    # Get skill library stats
    async with async_session() as session:
        # Total skills
        total_skills = await session.execute(
            select(func.count(Skill.id))
        )
        total_skills_count = total_skills.scalar() or 0

        # Active skills
        active_skills = await session.execute(
            select(func.count(Skill.id)).where(Skill.is_active == True)
        )
        active_skills_count = active_skills.scalar() or 0

        # Categories
        categories = await session.execute(
            select(func.count(func.distinct(Skill.category)))
        )
        categories_count = categories.scalar() or 0

        # Email stats
        total_emails = await session.execute(
            select(func.count(Email.id))
        )
        total_emails_count = total_emails.scalar() or 0

        customer_service_emails = await session.execute(
            select(func.count(Email.id)).where(Email.is_customer_service == True)
        )
        cs_emails_count = customer_service_emails.scalar() or 0

        processed_emails = await session.execute(
            select(func.count(Email.id)).where(Email.processed == True)
        )
        processed_count = processed_emails.scalar() or 0

    return AgentStatusResponse(
        system_status=system_status,
        agents=agents_status,
        skill_library={
            "total_skills": total_skills_count,
            "active_skills": active_skills_count,
            "categories": categories_count
        },
        email_stats={
            "total_emails": total_emails_count,
            "customer_service": cs_emails_count,
            "processed": processed_count
        }
    )


@agents_router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """
    Get the status of a background job (e.g., learning process).
    """
    if job_id not in _background_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = _background_jobs[job_id]
    return {
        "job_id": job_id,
        **job
    }


@agents_router.post("/batch-execute")
async def batch_execute(
    email_ids: list[str],
    background_tasks: BackgroundTasks
):
    """
    Execute the Execution Agent on multiple emails in the background.

    Returns a job_id to track progress.
    """
    job_id = str(uuid.uuid4())

    _background_jobs[job_id] = {
        "status": "started",
        "started_at": datetime.utcnow(),
        "agent": "batch_execution",
        "total": len(email_ids),
        "completed": 0,
        "results": []
    }

    background_tasks.add_task(
        _run_batch_execute_background,
        job_id,
        email_ids
    )

    return {
        "job_id": job_id,
        "status": "started",
        "message": f"Batch execution started for {len(email_ids)} emails"
    }


async def _run_batch_execute_background(job_id: str, email_ids: list[str]):
    """Background task for batch execution"""
    results = []

    for idx, email_id in enumerate(email_ids):
        try:
            result = await execution_agent.run({"email_id": email_id})
            results.append({
                "email_id": email_id,
                "success": result.success,
                "status": result.status,
                "reply_id": result.data.get("reply_id")
            })
        except Exception as e:
            results.append({
                "email_id": email_id,
                "success": False,
                "error": str(e)
            })

        # Update progress
        _background_jobs[job_id]["completed"] = idx + 1
        _background_jobs[job_id]["results"] = results

    _background_jobs[job_id]["status"] = "completed"
    _background_jobs[job_id]["completed_at"] = datetime.utcnow()
