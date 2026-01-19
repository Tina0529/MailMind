"""
Database models and initialization
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, Integer, Text, JSON, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from config import settings

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
)

# Create async session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


class Base(DeclarativeBase):
    """Base class for all models"""
    pass


class Email(Base):
    """Email model"""
    __tablename__ = "emails"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    zoho_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    from_address: Mapped[str] = mapped_column(String)
    from_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    to_address: Mapped[str] = mapped_column(String)
    to_addresses: Mapped[list] = mapped_column(JSON, default=list)  # 收件人列表
    cc_addresses: Mapped[list] = mapped_column(JSON, default=list)  # 抄送人列表
    subject: Mapped[str] = mapped_column(String)
    body: Mapped[str] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(DateTime)
    is_customer_service: Mapped[bool] = mapped_column(Boolean, default=False)
    category: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Priority fields - 重点关注邮件
    is_priority: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    priority_score: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    priority_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship
    replies: Mapped[list["Reply"]] = relationship(
        "Reply", back_populates="email", cascade="all, delete-orphan"
    )


class Reply(Base):
    """Reply model"""
    __tablename__ = "replies"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email_id: Mapped[str] = mapped_column(String, ForeignKey("emails.id"))
    ai_draft: Mapped[str] = mapped_column(Text)
    human_edited: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sent: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship
    email: Mapped["Email"] = relationship("Email", back_populates="replies")


class Skill(Base):
    """Skill model"""
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    name_en: Mapped[str] = mapped_column(String, unique=True)
    category: Mapped[str] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    trigger_keywords: Mapped[list] = mapped_column(JSON, default=list)
    rules: Mapped[list] = mapped_column(JSON, default=list)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to source emails
    source_emails: Mapped[list["SkillSourceEmail"]] = relationship(
        "SkillSourceEmail", back_populates="skill", cascade="all, delete-orphan"
    )


class SkillSourceEmail(Base):
    """
    关联表：记录 Skill 是基于哪些邮件学习生成的
    用于追溯 Skill 的来源和支持自进化优化
    """
    __tablename__ = "skill_source_emails"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    skill_id: Mapped[str] = mapped_column(String, ForeignKey("skills.id"), index=True)
    email_id: Mapped[str] = mapped_column(String, ForeignKey("emails.id"), index=True)
    
    # 贡献类型: initial_learning (初始学习), evolution_update (自进化更新)
    contribution_type: Mapped[str] = mapped_column(String, default="initial_learning")
    
    # 可选：记录该邮件对 Skill 的具体贡献（如提取了哪条规则）
    contribution_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    skill: Mapped["Skill"] = relationship("Skill", back_populates="source_emails")
    email: Mapped["Email"] = relationship("Email")


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

