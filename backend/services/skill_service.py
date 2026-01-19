"""
Skill Service - Manage skills and skill matching
"""
import json
import uuid
from typing import List, Dict, Optional
from pathlib import Path

from models.database import Skill, async_session
from models.schemas import SkillCreate, SkillResponse


class SkillService:
    """Service for managing skills"""

    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.skills_file = self.data_dir / "skills.json"

    async def get_all_skills(self, active_only: bool = True) -> List[SkillResponse]:
        """Get all skills

        Args:
            active_only: Only return active skills

        Returns:
            List of skills
        """
        async with async_session() as session:
            from sqlalchemy import select

            query = select(Skill)
            if active_only:
                query = query.where(Skill.is_active == True)

            result = await session.execute(query.order_by(Skill.usage_count.desc()))
            skills = result.scalars().all()

            return [
                SkillResponse(
                    id=str(s.id),
                    name=s.name,
                    name_en=s.name_en,
                    category=s.category,
                    description=s.description,
                    trigger_keywords=s.trigger_keywords or [],
                    rules=s.rules or [],
                    usage_count=s.usage_count,
                    success_count=s.success_count,
                    is_active=s.is_active,
                    created_at=s.created_at,
                    updated_at=s.updated_at
                )
                for s in skills
            ]

    async def get_skill(self, skill_id: str) -> Optional[SkillResponse]:
        """Get a specific skill

        Args:
            skill_id: Skill ID

        Returns:
            Skill or None
        """
        async with async_session() as session:
            from sqlalchemy import select

            result = await session.execute(select(Skill).where(Skill.id == skill_id))
            skill = result.scalar_one_or_none()

            if skill:
                return SkillResponse(
                    id=str(skill.id),
                    name=skill.name,
                    name_en=skill.name_en,
                    category=skill.category,
                    description=skill.description,
                    trigger_keywords=skill.trigger_keywords or [],
                    rules=skill.rules or [],
                    usage_count=skill.usage_count,
                    success_count=skill.success_count,
                    is_active=skill.is_active,
                    created_at=skill.created_at,
                    updated_at=skill.updated_at
                )
            return None

    async def create_skill(self, skill_data: SkillCreate) -> SkillResponse:
        """Create a new skill

        Args:
            skill_data: Skill data

        Returns:
            Created skill
        """
        async with async_session() as session:
            skill = Skill(
                id=str(uuid.uuid4()),
                name=skill_data.name,
                name_en=skill_data.name_en,
                category=skill_data.category,
                description=skill_data.description,
                trigger_keywords=skill_data.trigger_keywords,
                rules=[r.dict() for r in skill_data.rules]
            )

            session.add(skill)
            await session.commit()
            await session.refresh(skill)

            return SkillResponse(
                id=str(skill.id),
                name=skill.name,
                name_en=skill.name_en,
                category=skill.category,
                description=skill.description,
                trigger_keywords=skill.trigger_keywords or [],
                rules=skill.rules or [],
                usage_count=skill.usage_count,
                success_count=skill.success_count,
                is_active=skill.is_active,
                created_at=skill.created_at,
                updated_at=skill.updated_at
            )

    async def import_from_support_skill(self, skills_data: dict) -> int:
        """Import skills from support-email-composer-skill format

        Args:
            skills_data: Skills data from support-email-composer-skill

        Returns:
            Number of skills imported
        """
        imported = 0

        for skill_data in skills_data.get("skills", []):
            async with async_session() as session:
                # Check if skill already exists
                from sqlalchemy import select

                existing = await session.execute(
                    select(Skill).where(Skill.name_en == skill_data.get("name_en"))
                )
                existing_skill = existing.scalar_one_or_none()

                if existing_skill:
                    # Update existing skill
                    existing_skill.name = skill_data.get("name")
                    existing_skill.category = skill_data.get("category")
                    existing_skill.description = skill_data.get("description")
                    existing_skill.trigger_keywords = skill_data.get("trigger_keywords", [])
                    existing_skill.rules = skill_data.get("rules", [])
                    existing_skill.updated_at = datetime.utcnow()
                else:
                    # Create new skill
                    skill = Skill(
                        id=str(uuid.uuid4()),
                        name=skill_data.get("name"),
                        name_en=skill_data.get("name_en"),
                        category=skill_data.get("category"),
                        description=skill_data.get("description"),
                        trigger_keywords=skill_data.get("trigger_keywords", []),
                        rules=skill_data.get("rules", [])
                    )
                    session.add(skill)

                await session.commit()
                imported += 1

        return imported

    async def match_skills(self, email_content: str, category: str = None) -> List[Dict]:
        """Match skills to email content

        Args:
            email_content: Email content to match
            category: Optional category filter

        Returns:
            List of matched skills with their rules
        """
        async with async_session() as session:
            from sqlalchemy import select

            query = select(Skill).where(Skill.is_active == True)
            if category:
                query = query.where(Skill.category == category)

            result = await session.execute(query)
            skills = result.scalars().all()

            matched = []
            content_lower = email_content.lower()

            for skill in skills:
                # Check trigger keywords
                trigger_match = False
                for keyword in skill.trigger_keywords:
                    if keyword.lower() in content_lower:
                        trigger_match = True
                        break

                if trigger_match:
                    # Find matching rules
                    matched_rules = []
                    for rule in skill.rules or []:
                        rule_match = True
                        for condition in rule.get("conditions", []):
                            if condition.lower() not in content_lower:
                                rule_match = False
                                break

                        if rule_match:
                            matched_rules.append(rule)

                    matched.append({
                        "id": str(skill.id),
                        "name": skill.name,
                        "name_en": skill.name_en,
                        "category": skill.category,
                        "rules": sorted(matched_rules, key=lambda r: r.get("priority", 0), reverse=True)
                    })

            return matched

    async def increment_usage(self, skill_id: str, success: bool = True) -> None:
        """Increment skill usage counter

        Args:
            skill_id: Skill ID
            success: Whether the usage was successful
        """
        async with async_session() as session:
            from sqlalchemy import select

            result = await session.execute(select(Skill).where(Skill.id == skill_id))
            skill = result.scalar_one_or_none()

            if skill:
                skill.usage_count += 1
                if success:
                    skill.success_count += 1
                await session.commit()

    async def get_categories(self) -> List[str]:
        """Get all skill categories

        Returns:
            List of categories
        """
        async with async_session() as session:
            from sqlalchemy import distinct, select

            result = await session.execute(select(distinct(Skill.category)))
            return [row[0] for row in result.all() if row[0]]

    async def save_to_file(self) -> None:
        """Save skills to JSON file"""
        async with async_session() as session:
            from sqlalchemy import select

            result = await session.execute(select(Skill))
            skills = result.scalars().all()

            skills_data = {
                "skills": [
                    {
                        "id": str(s.id),
                        "name": s.name,
                        "name_en": s.name_en,
                        "category": s.category,
                        "description": s.description,
                        "trigger_keywords": s.trigger_keywords or [],
                        "rules": s.rules or [],
                        "usage_count": s.usage_count,
                        "success_count": s.success_count
                    }
                    for s in skills
                ],
                "total": len(skills)
            }

            with open(self.skills_file, "w", encoding="utf-8") as f:
                json.dump(skills_data, f, ensure_ascii=False, indent=2)

    async def load_from_file(self) -> int:
        """Load skills from JSON file

        Returns:
            Number of skills loaded
        """
        if not self.skills_file.exists():
            return 0

        with open(self.skills_file, "r", encoding="utf-8") as f:
            skills_data = json.load(f)

        imported = 0
        for skill_data in skills_data.get("skills", []):
            async with async_session() as session:
                from sqlalchemy import select

                # Check if exists
                existing = await session.execute(
                    select(Skill).where(Skill.name_en == skill_data.get("name_en"))
                )
                existing_skill = existing.scalar_one_or_none()

                if not existing_skill:
                    skill = Skill(
                        id=skill_data.get("id", str(uuid.uuid4())),
                        name=skill_data.get("name"),
                        name_en=skill_data.get("name_en"),
                        category=skill_data.get("category"),
                        description=skill_data.get("description"),
                        trigger_keywords=skill_data.get("trigger_keywords", []),
                        rules=skill_data.get("rules", []),
                        usage_count=skill_data.get("usage_count", 0),
                        success_count=skill_data.get("success_count", 0)
                    )
                    session.add(skill)
                    await session.commit()
                    imported += 1

        return imported
