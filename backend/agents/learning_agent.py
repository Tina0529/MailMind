"""
Learning Agent - Analyzes historical emails to create Skills
Phase 1 of the three-phase agent architecture
"""
import json
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from agents.base_agent import BaseAgent, AgentResult
from models.database import Email, Reply, Skill, SkillSourceEmail, async_session
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
    - L-08: Deduplicate similar Skills after extraction
    """

    # Max emails per category for learning
    MAX_EMAILS_PER_CATEGORY = 50

    def __init__(self):
        super().__init__(
            name="LearningAgent",
            description="Analyzes historical emails to create and update Skills",
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
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
            self._update_progress(3, 6, "Extracting skills from emails...")
            skills_created = 0
            skills_updated = 0
            collaborative_skills = []

            total_categories = len(by_category)
            for idx, (category, category_emails) in enumerate(by_category.items()):
                self._update_progress(
                    3,
                    6,
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

            # Step 4: Deduplicate similar skills
            self._update_progress(4, 6, "Deduplicating similar skills...")
            dedup_result = await self._deduplicate_skills()

            # Step 5: Save skills to file
            self._update_progress(5, 6, "Saving skills to file...")
            await self.skill_service.save_to_file()

            # Step 6: Complete
            self._update_progress(6, 6, "Learning complete!")

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
                    "skills_deduplicated": dedup_result.get("merged", 0),
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
        """Get customer service emails from database, with replies eagerly loaded"""
        async with async_session() as session:
            result = await session.execute(
                select(Email)
                .options(selectinload(Email.replies))
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
        """Extract skill from a category of emails, including reply samples"""
        # Prepare email-reply pairs (up to MAX_EMAILS_PER_CATEGORY)
        conversations = []
        source_email_ids = []

        for email in emails[:self.MAX_EMAILS_PER_CATEGORY]:
            entry = {
                "from": email.from_address,
                "subject": email.subject,
                "body": email.body[:2000],  # Allow more context for Sonnet
            }

            # Include human-edited reply if available, otherwise AI draft
            if email.replies:
                best_reply = None
                for reply in email.replies:
                    if reply.human_edited:
                        best_reply = reply.human_edited
                        break
                    elif reply.ai_draft and not best_reply:
                        best_reply = reply.ai_draft
                if best_reply:
                    entry["reply"] = best_reply[:2000]

            conversations.append(entry)
            source_email_ids.append(email.id)

        # Detect dominant language from email content
        language_hint = self._detect_language_hint(conversations)

        # Build prompt for Claude
        prompt = self._build_extraction_prompt(category, conversations, language_hint)

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

    def _detect_language_hint(self, conversations: List[Dict]) -> str:
        """Detect the dominant language from email conversations"""
        ja_markers = ["様", "お", "ご", "です", "ます", "いたし", "ございます", "の件"]
        zh_markers = ["您好", "请", "谢谢", "我们", "的", "了", "是", "尊敬的"]
        en_markers = ["Dear", "Hello", "Thank", "Please", "regards", "Best", "Hi "]

        ja_count = zh_count = en_count = 0
        for conv in conversations:
            text = conv.get("subject", "") + " " + conv.get("body", "")[:500]
            reply = conv.get("reply", "")[:500]
            combined = text + " " + reply
            for m in ja_markers:
                if m in combined:
                    ja_count += 1
            for m in zh_markers:
                if m in combined:
                    zh_count += 1
            for m in en_markers:
                if m in combined:
                    en_count += 1

        scores = {"ja": ja_count, "zh": zh_count, "en": en_count}
        dominant = max(scores, key=scores.get)
        lang_map = {"ja": "Japanese", "zh": "Chinese", "en": "English"}
        return lang_map.get(dominant, "English")

    def _build_extraction_prompt(
        self,
        category: str,
        conversations: List[Dict],
        language_hint: str = "Japanese"
    ) -> str:
        """Build prompt for skill extraction with email-reply pairs"""

        # Count how many have replies
        with_replies = sum(1 for c in conversations if c.get("reply"))
        total = len(conversations)

        return f"""You are an expert at analyzing customer service email patterns to create reusable response Skills.

## Task
Analyze the following {total} customer service emails (category: "{category}") and extract ONE comprehensive Skill.
{f'{with_replies} of these emails include actual human-written replies — use these as reference for response templates.' if with_replies > 0 else ''}

## Email Data

{json.dumps(conversations, ensure_ascii=False, indent=2)}

## Output Format

Return a single JSON object:

{{
    "name": "Skill name in {language_hint}",
    "name_en": "kebab-case-english-name",
    "category": "{category}",
    "description": "What types of emails this skill handles (2-3 sentences)",
    "trigger_keywords": ["keyword1", "keyword2", "...at least 6 keywords"],
    "rules": [
        {{
            "rule_id": "rule_1",
            "name": "Rule name in {language_hint}",
            "trigger_keywords": ["specific", "trigger", "words"],
            "conditions": [
                "Condition that can be verified from email content"
            ],
            "action_steps": [
                "Concrete step the agent should take"
            ],
            "response_template": "Complete multi-paragraph response template",
            "priority": 10
        }}
    ],
    "collaborative_skills": ["related-skill-name-en"]
}}

## Critical Requirements

### 1. Rules (MUST have 3-5 distinct rules)
Each rule must cover a DIFFERENT scenario found in the emails. Do NOT create rules that overlap.
Example: For "billing" category, you might have separate rules for "plan upgrade request", "payment failure", "refund request", "invoice inquiry".

### 2. Conditions (MUST be verifiable from email content)
BAD conditions (too vague, cannot be checked):
- "需要进一步调查" (too vague)
- "检查邮件主题" (this is an action, not a condition)
- "验证发件人" (too vague)

GOOD conditions (can be checked against email text):
- "Email mentions a specific product model or serial number"
- "Customer explicitly requests a refund or cancellation"
- "Email contains an order number or invoice reference"
- "Customer reports an error message or malfunction"

### 3. Trigger Keywords (at least 6)
Include both the original language keywords AND common variations.
Include keywords in multiple languages if the emails are multilingual.

### 4. Response Templates (MUST be complete and professional)
Each template must be a FULL email reply, not just an opening sentence.
Structure: greeting → acknowledge the issue → provide solution/next steps → closing.
{"Use the actual human replies in the data as reference for tone and structure." if with_replies > 0 else ""}
Use these placeholders: {{{{customer_name}}}}, {{{{company_name}}}}, {{{{product_name}}}}, {{{{order_id}}}}, {{{{issue_detail}}}}

### 5. Language
All user-facing text (name, rule names, response_template) MUST be in {language_hint}.
name_en and rule_id must always be in English.

Only return the JSON, nothing else."""

    async def _deduplicate_skills(self) -> Dict[str, Any]:
        """Deduplicate similar skills by asking Claude to identify overlaps"""
        all_skills = await self.skill_service.get_all_skills(active_only=True)

        if len(all_skills) <= 1:
            return {"merged": 0}

        # Build a summary of all skills for Claude to analyze
        skill_summaries = []
        for s in all_skills:
            skill_summaries.append({
                "id": s.id,
                "name": s.name,
                "name_en": s.name_en,
                "category": s.category,
                "description": s.description,
                "trigger_keywords": s.trigger_keywords[:10],
                "rule_count": len(s.rules),
                "rule_names": [r.get("name", "") for r in (s.rules or [])]
            })

        prompt = f"""Analyze these {len(skill_summaries)} skills and identify groups that are DUPLICATES or NEAR-DUPLICATES (covering the same topic with overlapping rules).

Skills:
{json.dumps(skill_summaries, ensure_ascii=False, indent=2)}

Return a JSON array of merge groups. Each group lists skill IDs that should be merged into one.
Only include groups where skills are genuinely redundant — different categories should NOT be merged.

Example output:
{{
    "merge_groups": [
        {{
            "keep_id": "id-of-best-skill-to-keep",
            "remove_ids": ["id-to-remove-1", "id-to-remove-2"],
            "reason": "These skills all handle subscription plan changes"
        }}
    ]
}}

If no duplicates exist, return: {{"merge_groups": []}}
Only return the JSON, nothing else."""

        response = await self.call_claude(prompt)
        if not response.get("success"):
            return {"merged": 0, "error": "Claude call failed"}

        result = self.extract_json(response.get("content", ""))
        if not result or not result.get("merge_groups"):
            return {"merged": 0}

        merged_count = 0
        for group in result["merge_groups"]:
            remove_ids = group.get("remove_ids", [])
            for skill_id in remove_ids:
                await self._deactivate_skill(skill_id)
                merged_count += 1

        return {"merged": merged_count}

    async def _deactivate_skill(self, skill_id: str):
        """Deactivate a skill (soft delete)"""
        async with async_session() as session:
            result = await session.execute(
                select(Skill).where(Skill.id == skill_id)
            )
            skill = result.scalar_one_or_none()
            if skill:
                skill.is_active = False
                skill.updated_at = datetime.utcnow()
                await session.commit()

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
