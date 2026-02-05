"""
Execution Agent - Processes incoming emails and generates replies
Phase 2 of the three-phase agent architecture
"""
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime

from sqlalchemy import select

from agents.base_agent import BaseAgent, AgentResult
from models.database import Email, Reply, Skill, async_session
from services.skill_service import SkillService
from services.email_classifier import EmailClassifierService
from config import settings


class ExecutionAgent(BaseAgent):
    """
    Execution Agent - Processes emails and generates AI replies.

    Responsibilities:
    - E-01: Receive and parse email content
    - E-02: Classify email using Claude
    - E-03: Match relevant Skills based on keywords
    - E-04: Match specific rules with priority ordering
    - E-05: Generate reply draft based on rules
    - E-06: Escalate to human if no match found
    - E-07: Provide match confidence and details
    """

    # Confidence thresholds
    HIGH_CONFIDENCE_THRESHOLD = 0.7
    ESCALATION_THRESHOLD = 0.3

    def __init__(self):
        super().__init__(
            name="ExecutionAgent",
            description="Processes incoming emails and generates AI-powered replies",
            model="claude-3-5-haiku-20241022",
            max_tokens=2048,
            temperature=0.5
        )
        self.skill_service = SkillService()
        self.classifier = EmailClassifierService()

    async def run(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Process an email and generate a reply.

        Args:
            input_data: {
                "email_id": str - ID of the email to process,
                "auto_send": bool (default False) - auto-send if confidence is high
            }

        Returns:
            AgentResult with reply draft and match details
        """
        run_id = self._start_run()

        email_id = input_data.get("email_id")
        auto_send = input_data.get("auto_send", False)

        if not email_id:
            self._end_run("failed")
            return AgentResult(
                success=False,
                status="failed",
                errors=["email_id is required"],
                data={"job_id": run_id}
            )

        try:
            # Step 1: Get email
            self._update_progress(1, 6, "Fetching email...")
            email = await self._get_email(email_id)

            if not email:
                self._end_run("failed")
                return AgentResult(
                    success=False,
                    status="failed",
                    errors=[f"Email {email_id} not found"],
                    data={"job_id": run_id}
                )

            # Step 2: Classify email if not already classified
            self._update_progress(2, 6, "Classifying email...")
            if not email.category:
                classification = await self._classify_email(email)
                email = await self._update_email_classification(email_id, classification)

            # Step 3: Match skills
            self._update_progress(3, 6, "Matching skills...")
            email_content = f"{email.subject}\n\n{email.body}"
            matched_skills = await self._match_skills_with_details(
                email_content,
                email.category
            )

            # Step 4: Calculate confidence and check for escalation
            self._update_progress(4, 6, "Calculating confidence...")
            confidence = self._calculate_confidence(matched_skills, email)
            requires_escalation = confidence < self.ESCALATION_THRESHOLD

            # Step 5: Generate reply
            self._update_progress(5, 6, "Generating reply...")
            if requires_escalation:
                ai_draft = self._generate_escalation_draft(email)
                escalation_reason = self._get_escalation_reason(matched_skills, confidence)
            else:
                ai_draft = await self._generate_reply(email, matched_skills)
                escalation_reason = None

            # Step 6: Save reply
            self._update_progress(6, 6, "Saving reply...")
            reply_id = await self._save_reply(email_id, ai_draft)

            # Update email as processed
            await self._mark_email_processed(email_id)

            # Increment skill usage
            if matched_skills and not requires_escalation:
                await self.skill_service.increment_usage(
                    matched_skills[0]["skill_id"],
                    success=True
                )

            self._end_run("completed")

            return AgentResult(
                success=True,
                status="draft_ready" if not requires_escalation else "escalated",
                data={
                    "job_id": run_id,
                    "email_id": email_id,
                    "reply_id": reply_id,
                    "ai_draft": ai_draft,
                    "matched_skills": matched_skills,
                    "confidence": confidence,
                    "requires_escalation": requires_escalation,
                    "escalation_reason": escalation_reason
                }
            )

        except Exception as e:
            self._end_run("failed")
            return AgentResult(
                success=False,
                status="failed",
                errors=[str(e)],
                data={"job_id": run_id, "email_id": email_id}
            )

    async def _get_email(self, email_id: str) -> Optional[Email]:
        """Get email from database"""
        async with async_session() as session:
            result = await session.execute(
                select(Email).where(Email.id == email_id)
            )
            return result.scalar_one_or_none()

    async def _classify_email(self, email: Email) -> Dict[str, Any]:
        """Classify email using Claude"""
        return await self.classifier.classify_email({
            "from_address": email.from_address,
            "subject": email.subject,
            "body": email.body
        })

    async def _update_email_classification(
        self,
        email_id: str,
        classification: Dict[str, Any]
    ) -> Email:
        """Update email with classification results"""
        async with async_session() as session:
            result = await session.execute(
                select(Email).where(Email.id == email_id)
            )
            email = result.scalar_one_or_none()

            if email:
                email.is_customer_service = classification.get("is_customer_service", False)
                email.category = classification.get("category")
                await session.commit()
                await session.refresh(email)

            return email

    async def _match_skills_with_details(
        self,
        email_content: str,
        category: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Match skills and return detailed matching info"""
        # Get basic matches from skill service
        basic_matches = await self.skill_service.match_skills(email_content, category)

        detailed_matches = []
        content_lower = email_content.lower()

        for match in basic_matches:
            # Get full skill info
            skill = await self.skill_service.get_skill(match["id"])
            if not skill:
                continue

            # Find which keywords matched
            matched_keywords = [
                kw for kw in skill.trigger_keywords
                if kw.lower() in content_lower
            ]

            # Calculate keyword match score
            keyword_score = len(matched_keywords) / max(len(skill.trigger_keywords), 1)

            # Calculate rule match score
            matched_rules = match.get("rules", [])
            rule_score = len(matched_rules) / max(len(skill.rules), 1) if skill.rules else 0

            # Combined confidence for this skill
            skill_confidence = (keyword_score * 0.4) + (rule_score * 0.6)

            detailed_matches.append({
                "skill_id": match["id"],
                "skill_name": match["name"],
                "skill_name_en": match["name_en"],
                "category": match["category"],
                "matched_keywords": matched_keywords,
                "matched_rules": matched_rules,
                "keyword_score": keyword_score,
                "rule_score": rule_score,
                "confidence": skill_confidence
            })

        # Sort by confidence
        detailed_matches.sort(key=lambda x: x["confidence"], reverse=True)

        return detailed_matches

    def _calculate_confidence(
        self,
        matched_skills: List[Dict],
        email: Email
    ) -> float:
        """Calculate overall confidence score"""
        if not matched_skills:
            return 0.0

        # Base confidence from best skill match
        base_confidence = matched_skills[0]["confidence"] if matched_skills else 0

        # Bonus for customer service classification
        if email.is_customer_service:
            base_confidence += 0.1

        # Bonus for having category
        if email.category:
            base_confidence += 0.1

        # Penalty for very short emails (might be unclear)
        if len(email.body) < 50:
            base_confidence -= 0.2

        # Cap at 1.0
        return min(max(base_confidence, 0.0), 1.0)

    def _get_escalation_reason(
        self,
        matched_skills: List[Dict],
        confidence: float
    ) -> str:
        """Get reason for escalation"""
        if not matched_skills:
            return "No matching skills found for this email"
        if confidence < self.ESCALATION_THRESHOLD:
            return f"Low confidence score ({confidence:.2f}). Manual review recommended."
        return "Unknown reason"

    def _generate_escalation_draft(self, email: Email) -> str:
        """Generate a generic draft for escalated emails"""
        customer_name = email.from_name or "Customer"
        return f"""Dear {customer_name},

Thank you for your email regarding "{email.subject}".

We have received your inquiry and a member of our team will review it personally and get back to you shortly.

Best regards,
Customer Support Team"""

    async def _generate_reply(
        self,
        email: Email,
        matched_skills: List[Dict]
    ) -> str:
        """Generate reply using matched skill templates or Claude"""
        customer_name = email.from_name or "Customer"

        if not matched_skills:
            return self._generate_escalation_draft(email)

        best_skill = matched_skills[0]
        matched_rules = best_skill.get("matched_rules", [])

        # Try to use template from best matching rule
        if matched_rules and matched_rules[0].get("response_template"):
            template = matched_rules[0]["response_template"]
            reply = template.replace("{{customer_name}}", customer_name)
            reply = reply.replace("{customer_name}", customer_name)
            reply = reply.replace("{{company_name}}", "We")
            reply = reply.replace("{company_name}", "We")
            return reply

        # Generate with Claude if no template
        return await self._generate_with_claude(email, best_skill)

    async def _generate_with_claude(
        self,
        email: Email,
        skill: Dict
    ) -> str:
        """Generate reply using Claude"""
        customer_name = email.from_name or "Customer"

        rules_text = "\n".join([
            f"- {r.get('name')}: {r.get('response_template', 'No template')}"
            for r in skill.get("matched_rules", [])
        ])

        prompt = f"""Generate a professional email reply based on the following:

Customer Email:
From: {email.from_name} ({email.from_address})
Subject: {email.subject}
Content: {email.body[:1500]}

Matched Skill: {skill.get('skill_name')}
Category: {skill.get('category')}

Relevant Rules:
{rules_text}

Generate a helpful, professional reply. Keep it concise and friendly.
Address the customer as "{customer_name}".
Only return the email content, no explanation."""

        response = await self.call_claude(prompt)

        if response.get("success") and response.get("content"):
            return response["content"]

        # Fallback
        return f"""Dear {customer_name},

Thank you for your inquiry regarding "{email.subject}".

We have reviewed your request and are working on resolving it. Our team will get back to you with more details shortly.

Best regards,
Customer Support Team"""

    async def _save_reply(self, email_id: str, ai_draft: str) -> str:
        """Save reply to database"""
        reply_id = str(uuid.uuid4())

        async with async_session() as session:
            reply = Reply(
                id=reply_id,
                email_id=email_id,
                ai_draft=ai_draft,
                sent=False
            )
            session.add(reply)
            await session.commit()

        return reply_id

    async def _mark_email_processed(self, email_id: str):
        """Mark email as processed"""
        async with async_session() as session:
            result = await session.execute(
                select(Email).where(Email.id == email_id)
            )
            email = result.scalar_one_or_none()

            if email:
                email.processed = True
                await session.commit()


# Singleton instance
execution_agent = ExecutionAgent()
