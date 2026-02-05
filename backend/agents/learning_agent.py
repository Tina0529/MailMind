"""
Learning Agent - Analyzes historical emails to create Skills
Phase 1 of the three-phase agent architecture
"""
import json
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime

from sqlalchemy import select

from agents.base_agent import BaseAgent, AgentResult
from models.database import Email, Skill, SkillSourceEmail, async_session
from services.skill_service import SkillService
from config import settings


class LearningAgent(BaseAgent):
    """
    Learning Agent - Extracts patterns from historical emails to create Skills.

    Responsibilities:
    - L-01: Import emails from database (already synced from Zoho)
    - L-02: Analyze email conversations to extract patterns
    - L-03: Create Skills by category
    - L-04: Extract trigger keywords and processing rules
    - L-05: Generate response templates
    - L-06: Identify collaborative Skill relationships
    - L-07: Track source emails for each Skill
    """

    def __init__(self):
        super().__init__(
            name="LearningAgent",
            description="Analyzes historical emails to create and update Skills",
            model="claude-3-5-haiku-20241022",
            max_tokens=4096,
            temperature=0.3  # Lower temperature for consistent extraction
        )
        self.skill_service = SkillService()

    async def run(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Run the learning process.

        Args:
            input_data: {
                "email_count": int (default 100),
                "force": bool (default False) - recreate skills even if exists,
                "categories": List[str] (optional) - specific categories to learn
            }

        Returns:
            AgentResult with learning summary
        """
        run_id = self._start_run()

        email_count = input_data.get("email_count", 100)
        force = input_data.get("force", False)
        target_categories = input_data.get("categories", None)

        try:
            # Step 1: Get customer service emails
            self._update_progress(1, 5, "Fetching customer service emails...")
            emails = await self._get_customer_service_emails(email_count)

            if not emails:
                self._end_run("completed")
                return AgentResult(
                    success=True,
                    status="completed",
                    data={
                        "job_id": run_id,
                        "emails_processed": 0,
                        "skills_created": 0,
                        "skills_updated": 0,
                        "message": "No customer service emails found"
                    }
                )

            # Step 2: Group emails by category
            self._update_progress(2, 5, "Grouping emails by category...")
            by_category = self._group_by_category(emails, target_categories)

            # Step 3: Extract skills from each category
            self._update_progress(3, 5, "Extracting skills from emails...")
            skills_created = 0
            skills_updated = 0
            collaborative_skills = []

            total_categories = len(by_category)
            for idx, (category, category_emails) in enumerate(by_category.items()):
                self._update_progress(
                    3,
                    5,
                    f"Processing category {idx + 1}/{total_categories}: {category}"
                )

                result = await self._extract_skill_from_category(
                    category,
                    category_emails,
                    force
                )

                if result.get("created"):
                    skills_created += 1
                elif result.get("updated"):
                    skills_updated += 1

                if result.get("collaborative_skills"):
                    collaborative_skills.extend(result["collaborative_skills"])

            # Step 4: Save skills to file
            self._update_progress(4, 5, "Saving skills to file...")
            await self.skill_service.save_to_file()

            # Step 5: Complete
            self._update_progress(5, 5, "Learning complete!")

            self._end_run("completed")
            return AgentResult(
                success=True,
                status="completed",
                data={
                    "job_id": run_id,
                    "emails_processed": len(emails),
                    "categories_processed": len(by_category),
                    "skills_created": skills_created,
                    "skills_updated": skills_updated,
                    "collaborative_skills": collaborative_skills
                }
            )

        except Exception as e:
            self._end_run("failed")
            return AgentResult(
                success=False,
                status="failed",
                errors=[str(e)],
                data={"job_id": run_id}
            )

    async def _get_customer_service_emails(self, limit: int) -> List[Email]:
        """Get customer service emails from database"""
        async with async_session() as session:
            result = await session.execute(
                select(Email)
                .where(Email.is_customer_service == True)
                .order_by(Email.received_at.desc())
                .limit(limit)
            )
            return list(result.scalars().all())

    def _group_by_category(
        self,
        emails: List[Email],
        target_categories: Optional[List[str]] = None
    ) -> Dict[str, List[Email]]:
        """Group emails by category"""
        by_category = {}
        for email in emails:
            cat = email.category or "other"
            if target_categories and cat not in target_categories:
                continue
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(email)
        return by_category

    async def _extract_skill_from_category(
        self,
        category: str,
        emails: List[Email],
        force: bool
    ) -> Dict[str, Any]:
        """Extract skill from a category of emails"""
        # Prepare email data for analysis (limit to 20 per category)
        conversations = []
        source_email_ids = []

        for email in emails[:20]:
            conversations.append({
                "from": email.from_address,
                "subject": email.subject,
                "body": email.body[:1000]  # Truncate for API
            })
            source_email_ids.append(email.id)

        # Build prompt for Claude
        prompt = self._build_extraction_prompt(category, conversations)

        # Call Claude to extract skill
        response = await self.call_claude(prompt)

        if not response.get("success"):
            return {"error": response.get("error")}

        # Parse response
        skill_data = self.extract_json(response.get("content", ""))
        if not skill_data:
            return {"error": "Failed to parse skill data from response"}

        # Check if skill already exists
        existing_skills = await self.skill_service.get_all_skills(active_only=False)
        existing_skill = next(
            (s for s in existing_skills if s.name_en == skill_data.get("name_en")),
            None
        )

        result = {
            "category": category,
            "skill_name": skill_data.get("name"),
            "collaborative_skills": skill_data.get("collaborative_skills", [])
        }

        if existing_skill and not force:
            # Update existing skill (could add merge logic here)
            result["updated"] = True
            result["skill_id"] = existing_skill.id
        else:
            # Create new skill
            from models.schemas import SkillCreate, RuleSchema

            # Convert rules to RuleSchema
            rules = []
            for rule in skill_data.get("rules", []):
                rules.append(RuleSchema(
                    rule_id=rule.get("rule_id", f"rule_{uuid.uuid4().hex[:8]}"),
                    name=rule.get("name", "Unnamed Rule"),
                    trigger_keywords=rule.get("trigger_keywords", []),
                    conditions=rule.get("conditions", []),
                    action_steps=rule.get("action_steps", []),
                    response_template=rule.get("response_template", ""),
                    priority=rule.get("priority", 0)
                ))

            skill_create = SkillCreate(
                name=skill_data.get("name", f"Skill for {category}"),
                name_en=skill_data.get("name_en", f"skill-{category}"),
                category=category,
                description=skill_data.get("description", ""),
                trigger_keywords=skill_data.get("trigger_keywords", []),
                rules=rules
            )

            new_skill = await self.skill_service.create_skill(skill_create)
            result["created"] = True
            result["skill_id"] = new_skill.id if new_skill else None

        # Record source emails
        if result.get("skill_id") and source_email_ids:
            await self._record_source_emails(
                result["skill_id"],
                source_email_ids,
                category
            )

        return result

    def _build_extraction_prompt(
        self,
        category: str,
        conversations: List[Dict]
    ) -> str:
        """Build prompt for skill extraction"""
        return f"""You are analyzing customer service emails to extract skills and response patterns.

Category: {category}

Here are {len(conversations)} example emails:

{json.dumps(conversations, ensure_ascii=False, indent=2)}

Extract the common patterns and create a skill with rules. Also identify if this skill should collaborate with other skills.

Respond in JSON format:

{{
    "name": "Skill Name (Chinese)",
    "name_en": "skill-name-en",
    "category": "{category}",
    "description": "Brief description of what this skill handles",
    "trigger_keywords": ["keyword1", "keyword2", "keyword3"],
    "rules": [
        {{
            "rule_id": "rule_1",
            "name": "Rule Name",
            "trigger_keywords": ["specific", "triggers"],
            "conditions": ["condition that must be true"],
            "action_steps": ["step1", "step2"],
            "response_template": "Response template with {{{{customer_name}}}} placeholder",
            "priority": 10
        }}
    ],
    "collaborative_skills": ["skill-name-en-1", "skill-name-en-2"]
}}

Guidelines:
1. Extract 2-5 specific rules based on different scenarios in the emails
2. Use {{{{customer_name}}}} and {{{{company_name}}}} as placeholders in templates
3. Priority: higher number = more specific rule (10-100)
4. Identify skills that might work together (e.g., "refund" often relates to "logistics")

Only return the JSON, nothing else."""

    async def _record_source_emails(
        self,
        skill_id: str,
        email_ids: List[str],
        category: str
    ):
        """Record source emails for a skill"""
        async with async_session() as session:
            for email_id in email_ids:
                # Check if link already exists
                existing = await session.execute(
                    select(SkillSourceEmail).where(
                        SkillSourceEmail.skill_id == skill_id,
                        SkillSourceEmail.email_id == email_id
                    )
                )
                if not existing.scalar_one_or_none():
                    source_record = SkillSourceEmail(
                        id=str(uuid.uuid4()),
                        skill_id=skill_id,
                        email_id=email_id,
                        contribution_type="initial_learning",
                        contribution_detail=f"Used for learning category: {category}"
                    )
                    session.add(source_record)
            await session.commit()


# Singleton instance
learning_agent = LearningAgent()
