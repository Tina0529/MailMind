"""
Evolution Agent - Learns from human edits to improve Skills
Phase 3 of the three-phase agent architecture
"""
import json
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime

from sqlalchemy import select

from agents.base_agent import BaseAgent, AgentResult
from models.database import (
    Email, Reply, Skill, SkillSourceEmail, SkillChangeLog, async_session
)
from services.skill_service import SkillService
from config import settings


class EvolutionAgent(BaseAgent):
    """
    Evolution Agent - Learns from human edits to improve Skills.

    Responsibilities:
    - V-01: Collect AI drafts and human-edited versions
    - V-02: Analyze differences using Claude
    - V-03: Identify new rules or rule updates
    - V-04: Automatically update Skill library
    - V-05: Record change history
    """

    # Minimum edit distance to trigger analysis
    MIN_EDIT_THRESHOLD = 20  # characters

    def __init__(self):
        super().__init__(
            name="EvolutionAgent",
            description="Learns from human edits to improve Skills over time",
            model="claude-3-5-haiku-20241022",
            max_tokens=4096,
            temperature=0.3
        )
        self.skill_service = SkillService()

    async def run(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Analyze a human-edited reply and evolve related Skills.

        Args:
            input_data: {
                "reply_id": str - ID of the reply with human edits
            }

        Returns:
            AgentResult with evolution results
        """
        run_id = self._start_run()

        reply_id = input_data.get("reply_id")

        if not reply_id:
            self._end_run("failed")
            return AgentResult(
                success=False,
                status="failed",
                errors=["reply_id is required"],
                data={"job_id": run_id}
            )

        try:
            # Step 1: Get reply and email
            self._update_progress(1, 5, "Fetching reply data...")
            reply, email = await self._get_reply_with_email(reply_id)

            if not reply:
                self._end_run("failed")
                return AgentResult(
                    success=False,
                    status="failed",
                    errors=[f"Reply {reply_id} not found"],
                    data={"job_id": run_id}
                )

            # Check if there are meaningful edits
            if not reply.human_edited:
                self._end_run("completed")
                return AgentResult(
                    success=True,
                    status="no_changes",
                    data={
                        "job_id": run_id,
                        "reply_id": reply_id,
                        "message": "No human edits to learn from"
                    }
                )

            # Check edit significance
            edit_distance = self._calculate_edit_distance(
                reply.ai_draft,
                reply.human_edited
            )

            if edit_distance < self.MIN_EDIT_THRESHOLD:
                self._end_run("completed")
                return AgentResult(
                    success=True,
                    status="no_changes",
                    data={
                        "job_id": run_id,
                        "reply_id": reply_id,
                        "message": f"Edit too minor ({edit_distance} chars). Skipping evolution."
                    }
                )

            # Step 2: Find related skills
            self._update_progress(2, 5, "Finding related skills...")
            related_skills = await self._find_related_skills(email)

            if not related_skills:
                self._end_run("completed")
                return AgentResult(
                    success=True,
                    status="no_changes",
                    data={
                        "job_id": run_id,
                        "reply_id": reply_id,
                        "message": "No related skills found to evolve"
                    }
                )

            # Step 3: Analyze differences
            self._update_progress(3, 5, "Analyzing differences with Claude...")
            analysis = await self._analyze_differences(
                email,
                reply.ai_draft,
                reply.human_edited,
                related_skills
            )

            if not analysis or not analysis.get("improvements"):
                self._end_run("completed")
                return AgentResult(
                    success=True,
                    status="no_changes",
                    data={
                        "job_id": run_id,
                        "reply_id": reply_id,
                        "message": "No actionable improvements identified"
                    }
                )

            # Step 4: Apply improvements
            self._update_progress(4, 5, "Applying skill improvements...")
            changes = await self._apply_improvements(
                analysis["improvements"],
                related_skills,
                reply_id,
                email.id
            )

            # Step 5: Save skills
            self._update_progress(5, 5, "Saving updated skills...")
            await self.skill_service.save_to_file()

            self._end_run("completed")

            return AgentResult(
                success=True,
                status="skill_updated" if changes else "no_changes",
                data={
                    "job_id": run_id,
                    "reply_id": reply_id,
                    "changes": changes,
                    "analysis_summary": analysis.get("summary", "")
                }
            )

        except Exception as e:
            self._end_run("failed")
            return AgentResult(
                success=False,
                status="failed",
                errors=[str(e)],
                data={"job_id": run_id, "reply_id": reply_id}
            )

    async def _get_reply_with_email(self, reply_id: str) -> tuple:
        """Get reply and associated email"""
        async with async_session() as session:
            result = await session.execute(
                select(Reply).where(Reply.id == reply_id)
            )
            reply = result.scalar_one_or_none()

            if not reply:
                return None, None

            email_result = await session.execute(
                select(Email).where(Email.id == reply.email_id)
            )
            email = email_result.scalar_one_or_none()

            return reply, email

    def _calculate_edit_distance(self, original: str, edited: str) -> int:
        """Calculate simple character difference between texts"""
        if not original or not edited:
            return 0
        return abs(len(edited) - len(original)) + sum(
            1 for a, b in zip(original, edited) if a != b
        )

    async def _find_related_skills(self, email: Email) -> List[Dict]:
        """Find skills related to the email"""
        email_content = f"{email.subject}\n\n{email.body}"
        matched = await self.skill_service.match_skills(email_content, email.category)

        # Also get skill by category if no direct match
        if not matched and email.category:
            all_skills = await self.skill_service.get_all_skills()
            matched = [
                {
                    "id": s.id,
                    "name": s.name,
                    "name_en": s.name_en,
                    "category": s.category,
                    "rules": s.rules
                }
                for s in all_skills
                if s.category == email.category
            ]

        return matched

    async def _analyze_differences(
        self,
        email: Email,
        ai_draft: str,
        human_edited: str,
        related_skills: List[Dict]
    ) -> Optional[Dict]:
        """Use Claude to analyze differences and suggest improvements"""

        skills_info = json.dumps([
            {
                "name": s.get("name"),
                "name_en": s.get("name_en"),
                "category": s.get("category"),
                "rules": [r.get("name") for r in s.get("rules", [])]
            }
            for s in related_skills
        ], ensure_ascii=False, indent=2)

        prompt = f"""Analyze the differences between an AI-generated reply and the human-edited version.
Identify improvements that can be applied to the skill rules.

Original Email:
Subject: {email.subject}
Body: {email.body[:1000]}
Category: {email.category}

AI Draft:
{ai_draft}

Human Edited Version:
{human_edited}

Related Skills:
{skills_info}

Analyze the changes and respond in JSON format:

{{
    "summary": "Brief summary of what the human changed and why",
    "improvements": [
        {{
            "type": "keyword_added" | "rule_added" | "rule_updated" | "template_improved",
            "target_skill_name_en": "skill-name-en",
            "description": "What improvement to make",
            "details": {{
                // For keyword_added: {{"keywords": ["new", "keywords"]}}
                // For rule_added: {{"rule_name": "...", "conditions": [...], "template": "..."}}
                // For rule_updated: {{"rule_name": "...", "new_template": "..."}}
                // For template_improved: {{"improved_template": "..."}}
            }}
        }}
    ]
}}

Guidelines:
1. Only suggest improvements that reflect meaningful pattern changes
2. Use {{{{customer_name}}}} and {{{{company_name}}}} placeholders in templates
3. If no clear improvements, return empty improvements array
4. Focus on reusable patterns, not one-time fixes

Only return the JSON, nothing else."""

        response = await self.call_claude(prompt)

        if not response.get("success"):
            return None

        return self.extract_json(response.get("content", ""))

    async def _apply_improvements(
        self,
        improvements: List[Dict],
        related_skills: List[Dict],
        reply_id: str,
        email_id: str
    ) -> List[Dict]:
        """Apply improvements to skills"""
        applied_changes = []

        for improvement in improvements:
            imp_type = improvement.get("type")
            target_skill_name_en = improvement.get("target_skill_name_en")
            details = improvement.get("details", {})

            # Find target skill
            target_skill = next(
                (s for s in related_skills if s.get("name_en") == target_skill_name_en),
                None
            )

            if not target_skill:
                continue

            skill_id = target_skill.get("id")

            try:
                if imp_type == "keyword_added":
                    change = await self._add_keywords(
                        skill_id,
                        details.get("keywords", []),
                        reply_id
                    )
                elif imp_type == "rule_added":
                    change = await self._add_rule(
                        skill_id,
                        details,
                        reply_id
                    )
                elif imp_type == "rule_updated":
                    change = await self._update_rule(
                        skill_id,
                        details,
                        reply_id
                    )
                elif imp_type == "template_improved":
                    change = await self._improve_template(
                        skill_id,
                        details.get("improved_template", ""),
                        reply_id
                    )
                else:
                    continue

                if change:
                    change["skill_name"] = target_skill.get("name")
                    applied_changes.append(change)

                    # Record source email for evolution
                    await self._record_evolution_source(
                        skill_id,
                        email_id,
                        improvement.get("description", "")
                    )

            except Exception as e:
                # Log error but continue with other improvements
                print(f"Error applying improvement: {e}")
                continue

        return applied_changes

    async def _add_keywords(
        self,
        skill_id: str,
        keywords: List[str],
        reply_id: str
    ) -> Optional[Dict]:
        """Add new keywords to a skill"""
        if not keywords:
            return None

        async with async_session() as session:
            result = await session.execute(
                select(Skill).where(Skill.id == skill_id)
            )
            skill = result.scalar_one_or_none()

            if not skill:
                return None

            # Add new keywords (avoid duplicates)
            existing = set(kw.lower() for kw in skill.trigger_keywords or [])
            new_keywords = [kw for kw in keywords if kw.lower() not in existing]

            if not new_keywords:
                return None

            skill.trigger_keywords = (skill.trigger_keywords or []) + new_keywords
            skill.updated_at = datetime.utcnow()

            # Log change
            change_log = SkillChangeLog(
                id=str(uuid.uuid4()),
                skill_id=skill_id,
                change_type="keyword_added",
                change_detail={
                    "added_keywords": new_keywords,
                    "total_keywords": len(skill.trigger_keywords)
                },
                triggered_by_reply_id=reply_id
            )
            session.add(change_log)

            await session.commit()

            return {
                "change_type": "keyword_added",
                "skill_id": skill_id,
                "detail": f"Added keywords: {', '.join(new_keywords)}"
            }

    async def _add_rule(
        self,
        skill_id: str,
        rule_details: Dict,
        reply_id: str
    ) -> Optional[Dict]:
        """Add a new rule to a skill"""
        async with async_session() as session:
            result = await session.execute(
                select(Skill).where(Skill.id == skill_id)
            )
            skill = result.scalar_one_or_none()

            if not skill:
                return None

            new_rule = {
                "rule_id": f"rule_{uuid.uuid4().hex[:8]}",
                "name": rule_details.get("rule_name", "Auto-generated Rule"),
                "trigger_keywords": rule_details.get("trigger_keywords", []),
                "conditions": rule_details.get("conditions", []),
                "action_steps": rule_details.get("action_steps", []),
                "response_template": rule_details.get("template", ""),
                "priority": rule_details.get("priority", 5)
            }

            skill.rules = (skill.rules or []) + [new_rule]
            skill.updated_at = datetime.utcnow()

            # Log change
            change_log = SkillChangeLog(
                id=str(uuid.uuid4()),
                skill_id=skill_id,
                change_type="rule_added",
                change_detail={
                    "rule_id": new_rule["rule_id"],
                    "rule_name": new_rule["name"]
                },
                triggered_by_reply_id=reply_id
            )
            session.add(change_log)

            await session.commit()

            return {
                "change_type": "rule_added",
                "skill_id": skill_id,
                "detail": f"Added rule: {new_rule['name']}"
            }

    async def _update_rule(
        self,
        skill_id: str,
        update_details: Dict,
        reply_id: str
    ) -> Optional[Dict]:
        """Update an existing rule in a skill"""
        rule_name = update_details.get("rule_name")
        new_template = update_details.get("new_template")

        if not rule_name or not new_template:
            return None

        async with async_session() as session:
            result = await session.execute(
                select(Skill).where(Skill.id == skill_id)
            )
            skill = result.scalar_one_or_none()

            if not skill or not skill.rules:
                return None

            # Find and update rule
            updated = False
            old_template = ""
            for rule in skill.rules:
                if rule.get("name") == rule_name:
                    old_template = rule.get("response_template", "")
                    rule["response_template"] = new_template
                    updated = True
                    break

            if not updated:
                return None

            skill.updated_at = datetime.utcnow()

            # Log change
            change_log = SkillChangeLog(
                id=str(uuid.uuid4()),
                skill_id=skill_id,
                change_type="rule_updated",
                change_detail={
                    "rule_name": rule_name,
                    "old_template": old_template[:200],
                    "new_template": new_template[:200]
                },
                triggered_by_reply_id=reply_id
            )
            session.add(change_log)

            await session.commit()

            return {
                "change_type": "rule_updated",
                "skill_id": skill_id,
                "detail": f"Updated rule template: {rule_name}"
            }

    async def _improve_template(
        self,
        skill_id: str,
        improved_template: str,
        reply_id: str
    ) -> Optional[Dict]:
        """Improve the primary template of a skill's first rule"""
        if not improved_template:
            return None

        async with async_session() as session:
            result = await session.execute(
                select(Skill).where(Skill.id == skill_id)
            )
            skill = result.scalar_one_or_none()

            if not skill or not skill.rules:
                return None

            # Update first rule's template
            old_template = skill.rules[0].get("response_template", "")
            skill.rules[0]["response_template"] = improved_template
            skill.updated_at = datetime.utcnow()

            # Log change
            change_log = SkillChangeLog(
                id=str(uuid.uuid4()),
                skill_id=skill_id,
                change_type="template_improved",
                change_detail={
                    "old_template": old_template[:200],
                    "new_template": improved_template[:200]
                },
                triggered_by_reply_id=reply_id
            )
            session.add(change_log)

            await session.commit()

            return {
                "change_type": "template_improved",
                "skill_id": skill_id,
                "detail": "Improved primary response template"
            }

    async def _record_evolution_source(
        self,
        skill_id: str,
        email_id: str,
        contribution_detail: str
    ):
        """Record the email as a source for skill evolution"""
        async with async_session() as session:
            # Check if already linked
            existing = await session.execute(
                select(SkillSourceEmail).where(
                    SkillSourceEmail.skill_id == skill_id,
                    SkillSourceEmail.email_id == email_id,
                    SkillSourceEmail.contribution_type == "evolution_update"
                )
            )

            if not existing.scalar_one_or_none():
                source = SkillSourceEmail(
                    id=str(uuid.uuid4()),
                    skill_id=skill_id,
                    email_id=email_id,
                    contribution_type="evolution_update",
                    contribution_detail=contribution_detail
                )
                session.add(source)
                await session.commit()


# Singleton instance
evolution_agent = EvolutionAgent()
