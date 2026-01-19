"""
Pydantic schemas for API requests/responses
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr


# ==================== Email Schemas ====================

class EmailBase(BaseModel):
    """Base email schema"""
    zoho_id: str
    from_address: str
    from_name: Optional[str] = None
    to_address: str
    to_addresses: List[str] = []  # 收件人列表
    cc_addresses: List[str] = []  # 抄送人列表
    subject: str
    body: str
    received_at: datetime


class EmailCreate(EmailBase):
    """Schema for creating an email"""
    pass


class EmailResponse(EmailBase):
    """Schema for email response"""
    id: str
    is_customer_service: bool
    category: Optional[str] = None
    processed: bool
    # Priority fields
    is_priority: bool = False
    priority_score: int = 0
    priority_reason: Optional[str] = None

    class Config:
        from_attributes = True


class EmailListResponse(BaseModel):
    """Schema for email list response"""
    emails: List[EmailResponse]
    total: int
    pending: int
    processed: int
    priority: int = 0


# ==================== Reply Schemas ====================

class ReplyCreate(BaseModel):
    """Schema for creating a reply"""
    email_id: str
    ai_draft: str
    human_edited: Optional[str] = None


class ReplyResponse(BaseModel):
    """Schema for reply response"""
    id: str
    email_id: str
    ai_draft: str
    human_edited: Optional[str] = None
    sent: bool
    sent_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class GenerateReplyRequest(BaseModel):
    """Schema for generating a reply"""
    email_id: str
    regenerate: bool = False


class GenerateReplyResponse(BaseModel):
    """Schema for generated reply"""
    email_id: str
    reply_id: str
    ai_draft: str
    matched_skills: List[str]
    confidence: float
    requires_review: bool


class SendReplyRequest(BaseModel):
    """Schema for sending a reply"""
    reply_id: str
    content: Optional[str] = None  # If None, use ai_draft


class SendReplyResponse(BaseModel):
    """Schema for sent reply response"""
    success: bool
    message: str
    sent_at: Optional[datetime] = None


# ==================== Skill Schemas ====================

class RuleSchema(BaseModel):
    """Schema for a rule"""
    rule_id: str
    name: str
    trigger_keywords: List[str]
    conditions: List[str]
    action_steps: List[str]
    response_template: str
    priority: int = 0


class SkillCreate(BaseModel):
    """Schema for creating a skill"""
    name: str
    name_en: str
    category: str
    description: Optional[str] = None
    trigger_keywords: List[str]
    rules: List[RuleSchema]


class SkillResponse(BaseModel):
    """Schema for skill response"""
    id: str
    name: str
    name_en: str
    category: str
    description: Optional[str] = None
    trigger_keywords: List[str]
    rules: List[RuleSchema]
    usage_count: int
    success_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SkillListResponse(BaseModel):
    """Schema for skill list response"""
    skills: List[SkillResponse]
    total: int
    categories: List[str]


# ==================== Learn Schemas ====================

class LearnRequest(BaseModel):
    """Schema for learning request"""
    email_count: int = 100
    force: bool = False


class LearnResponse(BaseModel):
    """Schema for learning response"""
    status: str
    message: str
    emails_processed: int
    customer_service_emails: int
    skills_created: int
    skills_updated: int


# ==================== Status Schemas ====================

class StatusResponse(BaseModel):
    """Schema for status response"""
    status: str
    zoho_connected: bool
    zoho_email: str
    total_emails: int
    total_skills: int
    pending_replies: int


# ==================== Zoho Config Schemas ====================

class ZohoConfigRequest(BaseModel):
    """Schema for Zoho configuration"""
    email: EmailStr
    app_password: str


class ZohoConfigResponse(BaseModel):
    """Schema for Zoho configuration response"""
    configured: bool
    email: str


class SyncEmailsRequest(BaseModel):
    """Schema for syncing emails"""
    count: int = 100
    sync_range: Optional[str] = None  # "today", "3days", "7days", "30days", "custom", "all"
    from_date: Optional[str] = None   # Format: YYYY-MM-DD
    to_date: Optional[str] = None     # Format: YYYY-MM-DD
    mark_as_customer_service: bool = False


class SyncEmailsResponse(BaseModel):
    """Schema for sync response"""
    synced: int
    new: int
    total: int
