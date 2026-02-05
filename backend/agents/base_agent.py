"""
Base Agent - Foundation class for all agents
Provides common functionality for Claude API calls and tool management
"""
import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field

import httpx

from config import settings


@dataclass
class AgentResult:
    """Result from an agent run"""
    success: bool
    status: str  # "completed", "failed", "partial"
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentRunInfo:
    """Information about an agent run"""
    run_id: str
    agent_name: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str = "running"
    progress: int = 0
    total_steps: int = 0


class BaseAgent(ABC):
    """
    Base class for all agents in the MailMind AI system.

    Provides:
    - Claude API calling with retry logic
    - Tool management and execution
    - Progress tracking and callbacks
    - Error handling and logging
    """

    def __init__(
        self,
        name: str,
        description: str,
        model: str = "claude-3-5-haiku-20241022",
        max_tokens: int = 4096,
        temperature: float = 0.7
    ):
        self.name = name
        self.description = description
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

        # API configuration
        self.api_key = settings.ANTHROPIC_API_KEY
        base_url = settings.ANTHROPIC_BASE_URL.rstrip('/')
        self.api_url = f"{base_url}/messages"

        # Run tracking
        self.current_run: Optional[AgentRunInfo] = None
        self.run_history: List[AgentRunInfo] = []

        # Progress callback
        self._progress_callback: Optional[Callable[[int, int, str], None]] = None

    def set_progress_callback(self, callback: Callable[[int, int, str], None]):
        """Set a callback for progress updates: callback(current, total, message)"""
        self._progress_callback = callback

    def _update_progress(self, current: int, total: int, message: str = ""):
        """Update progress and call callback if set"""
        if self.current_run:
            self.current_run.progress = current
            self.current_run.total_steps = total

        if self._progress_callback:
            self._progress_callback(current, total, message)

    async def call_claude(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Call Claude API with the given prompt.

        Args:
            prompt: User prompt to send
            system_prompt: Optional system prompt
            tools: Optional list of tool definitions
            max_tokens: Override default max_tokens
            temperature: Override default temperature

        Returns:
            API response as dict
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "No ANTHROPIC_API_KEY configured",
                "content": None
            }

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }

        data = {
            "model": self.model,
            "max_tokens": max_tokens or self.max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        }

        if system_prompt:
            data["system"] = system_prompt

        if tools:
            data["tools"] = tools

        if temperature is not None:
            data["temperature"] = temperature
        elif self.temperature is not None:
            data["temperature"] = self.temperature

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(self.api_url, headers=headers, json=data)

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"API error: {response.status_code} - {response.text}",
                    "content": None
                }

            result = response.json()
            content = result.get("content", [])

            # Extract text content
            text_content = ""
            tool_use = None
            for block in content:
                if block.get("type") == "text":
                    text_content += block.get("text", "")
                elif block.get("type") == "tool_use":
                    tool_use = block

            return {
                "success": True,
                "content": text_content,
                "tool_use": tool_use,
                "raw_response": result
            }

        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "Request timeout",
                "content": None
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}",
                "content": None
            }

    def extract_json(self, text: str) -> Optional[Dict]:
        """Extract JSON from Claude response text"""
        if not text:
            return None

        # Try to extract JSON from markdown code block
        if "```json" in text:
            try:
                json_str = text.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            except (IndexError, json.JSONDecodeError):
                pass

        # Try to extract from generic code block
        if "```" in text:
            try:
                json_str = text.split("```")[1].split("```")[0].strip()
                return json.loads(json_str)
            except (IndexError, json.JSONDecodeError):
                pass

        # Try to parse the entire text as JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        return None

    def _start_run(self) -> str:
        """Start a new run and return the run ID"""
        run_id = str(uuid.uuid4())
        self.current_run = AgentRunInfo(
            run_id=run_id,
            agent_name=self.name,
            started_at=datetime.utcnow(),
            status="running"
        )
        return run_id

    def _end_run(self, status: str = "completed"):
        """End the current run"""
        if self.current_run:
            self.current_run.completed_at = datetime.utcnow()
            self.current_run.status = status
            self.run_history.append(self.current_run)
            self.current_run = None

    @abstractmethod
    async def run(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Execute the agent's main logic.

        Args:
            input_data: Input parameters for the agent

        Returns:
            AgentResult with success status and data
        """
        pass

    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        return {
            "name": self.name,
            "description": self.description,
            "status": "busy" if self.current_run else "ready",
            "current_run": {
                "run_id": self.current_run.run_id,
                "started_at": self.current_run.started_at.isoformat(),
                "progress": self.current_run.progress,
                "total_steps": self.current_run.total_steps
            } if self.current_run else None,
            "total_runs": len(self.run_history),
            "last_run": self.run_history[-1].completed_at.isoformat() if self.run_history else None
        }
