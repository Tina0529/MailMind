"""
Email Classifier Service - Classify emails using Claude
"""
import os
import json
import httpx
from typing import Dict, List

from config import settings


class EmailClassifierService:
    """Service for classifying emails using Claude"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.api_url = "https://api.anthropic.com/v1/messages"

    async def classify_email(self, email_data: Dict) -> Dict:
        """Classify an email to determine if it's customer service related

        Args:
            email_data: Email data with subject, body, from_address

        Returns:
            Classification result with is_customer_service and category
        """
        if not self.api_key:
            # Default to false if no API key
            return {
                "is_customer_service": False,
                "category": None,
                "confidence": 0.0,
                "reasoning": "No Claude API key configured"
            }

        prompt = f"""You are an email classifier. Analyze the following email and determine:

1. Is this a customer service related email? (inquiry, complaint, support request, etc.)
2. What category does it belong to?

Email:
From: {email_data.get('from_address', '')}
Subject: {email_data.get('subject', '')}
Body: {email_data.get('body', '')[:2000]}

Respond in JSON format:
{{
    "is_customer_service": true/false,
    "category": "equipment-fault|refund-cancellation|price-inquiry|technical-support|logistics-issue|complaint-suggestion|other|non-customer-service",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation"
}}

Only return the JSON, nothing else."""

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }

        data = {
            "model": "claude-3-5-haiku-20241022",
            "max_tokens": 500,
            "messages": [{"role": "user", "content": prompt}]
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(self.api_url, headers=headers, json=data)
                
            if response.status_code != 200:
                print(f"Error calling Claude API: {response.status_code} - {response.text}")
                return {
                    "is_customer_service": False,
                    "category": None,
                    "confidence": 0.0,
                    "reasoning": f"API error: {response.status_code}"
                }

            result_json = response.json()
            result_text = result_json["content"][0]["text"]

            # Extract JSON
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            result = json.loads(result_text)

            # Map non-customer-service to None
            if result.get("category") == "non-customer-service":
                result["is_customer_service"] = False
                result["category"] = None

            return result

        except Exception as e:
            print(f"Error classifying email: {e}")
            return {
                "is_customer_service": False,
                "category": None,
                "confidence": 0.0,
                "reasoning": f"Error: {str(e)}"
            }

    async def batch_classify(self, emails: List[Dict]) -> List[Dict]:
        """Classify multiple emails

        Args:
            emails: List of email data

        Returns:
            List of classification results
        """
        results = []
        for email_data in emails:
            result = await self.classify_email(email_data)
            results.append({
                "zoho_id": email_data.get("zoho_id"),
                **result
            })
        return results

