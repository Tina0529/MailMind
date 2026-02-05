"""
Emails router - API endpoints for email management
"""
import uuid
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import Email, async_session
from models.schemas import (
    EmailListResponse,
    EmailResponse,
    ZohoConfigRequest,
    ZohoConfigResponse,
    SyncEmailsRequest,
    SyncEmailsResponse
)
from services.zoho_service import ZohoMailService
from services.zoho_oauth_service import zoho_oauth_service
from services.email_classifier import EmailClassifierService
from services.skill_service import SkillService
from config import settings


emails_router = APIRouter()


# Global services
zoho_service = None
classifier_service = None
skill_service = None


def get_email_service():
    """Get appropriate email service (OAuth or IMAP)"""
    global zoho_service

    # Try OAuth first
    if zoho_oauth_service.load_tokens():
        success, _ = zoho_oauth_service.test_connection()
        if success:
            return zoho_oauth_service, "oauth"

    # Fall back to IMAP
    if zoho_service is None:
        zoho_service = ZohoMailService()
    return zoho_service, "imap"


def get_services():
    """Get service instances"""
    global zoho_service, classifier_service, skill_service

    email_service, mode = get_email_service()

    if classifier_service is None:
        classifier_service = EmailClassifierService()
    if skill_service is None:
        skill_service = SkillService()
    return email_service, classifier_service, skill_service, mode


@emails_router.get("", response_model=EmailListResponse)
async def get_emails(
    status: str = None,
    priority_only: bool = False,
    limit: int = 50,
    offset: int = 0
):
    """Get all emails"""
    async with async_session() as session:
        query = select(Email).order_by(Email.received_at.desc())

        if status == "pending":
            query = query.where(Email.processed == False)
        elif status == "processed":
            query = query.where(Email.processed == True)
        
        # Filter for priority emails
        if priority_only:
            query = query.where(Email.is_priority == True)

        # Get total count
        count_query = select(func.count(Email.id))
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        # Get pending count
        pending_query = select(func.count(Email.id)).where(Email.processed == False)
        pending_result = await session.execute(pending_query)
        pending = pending_result.scalar() or 0
        
        # Get priority count
        priority_query = select(func.count(Email.id)).where(Email.is_priority == True)
        priority_result = await session.execute(priority_query)
        priority_count = priority_result.scalar() or 0

        # Get emails with pagination
        query = query.offset(offset).limit(limit)
        result = await session.execute(query)
        emails = result.scalars().all()

        return {
            "emails": [
                {
                    "id": str(e.id),
                    "zoho_id": e.zoho_id,
                    "from_address": e.from_address,
                    "from_name": e.from_name,
                    "to_address": e.to_address,
                    "to_addresses": e.to_addresses or [],
                    "cc_addresses": e.cc_addresses or [],
                    "subject": e.subject,
                    "body": e.body,
                    "received_at": e.received_at.isoformat() if e.received_at else None,
                    "is_customer_service": e.is_customer_service,
                    "category": e.category,
                    "processed": e.processed,
                    "is_priority": e.is_priority,
                    "priority_score": e.priority_score,
                    "priority_reason": e.priority_reason
                }
                for e in emails
            ],
            "total": total,
            "pending": pending,
            "processed": total - pending,
            "priority": priority_count
        }


@emails_router.get("/{email_id}", response_model=EmailResponse)
async def get_email(email_id: str):
    """Get a specific email"""
    async with async_session() as session:
        from sqlalchemy import select

        result = await session.execute(select(Email).where(Email.id == email_id))
        email = result.scalar_one_or_none()

        if not email:
            raise HTTPException(status_code=404, detail="Email not found")

        return EmailResponse(
            id=str(email.id),
            zoho_id=email.zoho_id,
            from_address=email.from_address,
            from_name=email.from_name,
            to_address=email.to_address,
            to_addresses=email.to_addresses or [],
            cc_addresses=email.cc_addresses or [],
            subject=email.subject,
            body=email.body,
            received_at=email.received_at,
            is_customer_service=email.is_customer_service,
            category=email.category,
            processed=email.processed
        )


@emails_router.post("/config", response_model=ZohoConfigResponse)
async def config_zoho(config: ZohoConfigRequest):
    """Configure Zoho Mail connection"""
    global zoho_service

    zoho_service = ZohoMailService(
        email=config.email,
        app_password=config.app_password
    )

    # Test connection
    success, message = zoho_service.test_connection()

    if success:
        return ZohoConfigResponse(
            configured=True,
            email=config.email
        )
    else:
        raise HTTPException(status_code=400, detail=message)


@emails_router.delete("/clear")
async def clear_emails():
    """Clear all emails from database"""
    async with async_session() as session:
        from sqlalchemy import delete
        
        result = await session.execute(delete(Email))
        deleted_count = result.rowcount
        await session.commit()
        
        print(f"DEBUG: Cleared {deleted_count} emails from database")
        
    return {
        "status": "success",
        "deleted": deleted_count,
        "message": f"Deleted {deleted_count} emails"
    }


@emails_router.post("/analyze-priority")
async def analyze_email_priority(background_tasks: BackgroundTasks, limit: int = 100):
    """使用 AI 分析邮件价值，标记重点关注邮件"""
    import httpx
    
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(status_code=400, detail="ANTHROPIC_API_KEY not configured")
    
    # 在后台运行分析
    background_tasks.add_task(run_priority_analysis, limit)
    
    return {
        "status": "started",
        "message": f"Priority analysis started for up to {limit} emails"
    }


async def run_priority_analysis(limit: int = 100):
    """后台任务：分析邮件优先级"""
    import httpx
    
    print("DEBUG: Starting priority analysis...")
    
    async with async_session() as session:
        # 获取未分析或需要重新分析的邮件
        result = await session.execute(
            select(Email)
            .where(Email.priority_score == 0)  # 未分析的邮件
            .order_by(Email.received_at.desc())
            .limit(limit)
        )
        emails = result.scalars().all()
        
        if not emails:
            print("DEBUG: No emails to analyze")
            return
        
        print(f"DEBUG: Analyzing {len(emails)} emails for priority...")
        
        base_url = settings.ANTHROPIC_BASE_URL.rstrip('/')
        api_url = f"{base_url}/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": settings.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01"
        }
        
        # 批量分析邮件（每批10封）
        batch_size = 10
        analyzed_count = 0
        priority_count = 0
        
        for i in range(0, len(emails), batch_size):
            batch = emails[i:i + batch_size]
            
            # 构建批量分析 prompt
            emails_data = []
            for email in batch:
                emails_data.append({
                    "id": email.id,
                    "from": email.from_address,
                    "subject": email.subject,
                    "body": email.body[:500]  # 截断正文
                })
            
            prompt = f"""分析以下 {len(emails_data)} 封邮件，判断哪些是需要重点关注的高价值邮件。

【重点关注（高优先级）】
- 正常的工作沟通邮件、业务往来邮件
- 邮件主题包含 "Re:" "回复:" "转发:" 等往来标识的邮件（说明有多次沟通，需要跟进）
- 客户咨询、产品问题、技术支持请求
- 业务合作洽谈、商务机会
- 需要回复或采取行动的邮件

【低优先级 - 不标记为重点】
- 自动通知邮件：GitHub、GitLab、JIRA、Slack、Notion 等系统自动发送的通知
- 发件人地址包含 noreply@、notifications@、no-reply@、mailer@、alert@ 等
- 营销推广邮件、广告邮件、新闻订阅
- 订单确认、发货通知等交易类自动邮件
- 验证码、登录提醒等安全通知

邮件列表:
{json.dumps(emails_data, ensure_ascii=False, indent=2)}

请返回 JSON 格式的分析结果:
{{
  "results": [
    {{
      "id": "邮件ID",
      "is_priority": true/false,
      "score": 0-100,
      "reason": "简短原因说明（20字以内）"
    }}
  ]
}}

只返回 JSON，不要其他内容。"""

            try:
                data = {
                    "model": "claude-3-5-haiku-20241022",
                    "max_tokens": 2000,
                    "messages": [{"role": "user", "content": prompt}]
                }
                
                async with httpx.AsyncClient(timeout=60) as client:
                    response = await client.post(api_url, headers=headers, json=data)
                
                if response.status_code != 200:
                    print(f"DEBUG: Claude API error: {response.status_code}")
                    continue
                
                result_json = response.json()
                result_text = result_json["content"][0]["text"]
                
                # 提取 JSON
                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0].strip()
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0].strip()
                
                analysis = json.loads(result_text)
                
                # 更新邮件优先级
                for item in analysis.get("results", []):
                    email_id = item.get("id")
                    is_priority = item.get("is_priority", False)
                    score = item.get("score", 0)
                    reason = item.get("reason", "")
                    
                    # 找到对应邮件并更新
                    for email in batch:
                        if email.id == email_id:
                            email.is_priority = is_priority
                            email.priority_score = score
                            email.priority_reason = reason
                            analyzed_count += 1
                            if is_priority:
                                priority_count += 1
                            break
                
                await session.commit()
                print(f"DEBUG: Batch analyzed, {priority_count} priority emails found so far")
                
            except Exception as e:
                print(f"DEBUG: Error analyzing batch: {e}")
                continue
        
        print(f"DEBUG: Priority analysis complete. Analyzed: {analyzed_count}, Priority: {priority_count}")


@emails_router.post("/sync", response_model=SyncEmailsResponse)
async def sync_emails(request: SyncEmailsRequest, background_tasks: BackgroundTasks):
    """Sync emails from Zoho Mail"""
    zoho_service, classifier_service, skill_service, mode = get_services()

    # Fetch emails from Zoho with optional date filtering
    fetched_emails = zoho_service.fetch_emails(
        count=request.count,
        sync_range=request.sync_range,
        from_date=request.from_date,
        to_date=request.to_date
    )

    if not fetched_emails:
        return SyncEmailsResponse(
            synced=0,
            new=0,
            total=0
        )

    # Save to database
    new_count = 0
    async with async_session() as session:
        for email_data in fetched_emails:
            # Check if already exists
            from sqlalchemy import select

            existing = await session.execute(
                select(Email).where(Email.zoho_id == email_data["zoho_id"])
            )
            existing_email = existing.scalar_one_or_none()

            if not existing_email:
                email = Email(
                    id=str(uuid.uuid4()),
                    zoho_id=email_data["zoho_id"],
                    from_address=email_data["from_address"],
                    from_name=email_data.get("from_name"),
                    to_address=email_data["to_address"],
                    to_addresses=email_data.get("to_addresses", []),
                    cc_addresses=email_data.get("cc_addresses", []),
                    subject=email_data["subject"],
                    body=email_data["body"],
                    received_at=email_data["received_at"],
                    is_customer_service=request.mark_as_customer_service
                )
                session.add(email)
                new_count += 1

        await session.commit()

    # Get total count
    async with async_session() as session:
        from sqlalchemy import func

        result = await session.execute(select(func.count(Email.id)))
        total = result.scalar() or 0

    # If requested, classify emails in background
    if settings.ANTHROPIC_API_KEY and not request.mark_as_customer_service:
        background_tasks.add_task(classify_new_emails)

    return SyncEmailsResponse(
        synced=len(fetched_emails),
        new=new_count,
        total=total
    )


async def classify_new_emails():
    """Classify unclassified emails in background"""
    global classifier_service

    if not classifier_service:
        classifier_service = EmailClassifierService()

    print("DEBUG: Starting email classification...")
    
    async with async_session() as session:
        from sqlalchemy import select

        # Get unclassified emails - increase limit to 500
        result = await session.execute(
            select(Email).where(Email.category == None).limit(500)
        )
        emails = result.scalars().all()
        
        print(f"DEBUG: Found {len(emails)} unclassified emails")

        classified_count = 0
        customer_service_count = 0
        
        for email in emails:
            email_data = {
                "zoho_id": email.zoho_id,
                "from_address": email.from_address,
                "subject": email.subject,
                "body": email.body
            }

            classification = await classifier_service.classify_email(email_data)

            email.is_customer_service = classification.get("is_customer_service", False)
            email.category = classification.get("category")
            
            classified_count += 1
            if email.is_customer_service:
                customer_service_count += 1
                print(f"DEBUG: Classified as customer service: {email.subject[:50]}... -> {email.category}")

        await session.commit()
        print(f"DEBUG: Classification complete. {classified_count} emails classified, {customer_service_count} are customer service.")


@emails_router.post("/classify")
async def classify_emails(background_tasks: BackgroundTasks):
    """Trigger email classification"""
    background_tasks.add_task(classify_new_emails)
    return {"status": "Classification started"}
