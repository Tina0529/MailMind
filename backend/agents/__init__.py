# Agents package - MailMind AI Agent System
# Implements three-phase agent architecture: Learning, Execution, Evolution

from agents.base_agent import BaseAgent, AgentResult, AgentRunInfo
from agents.learning_agent import LearningAgent, learning_agent
from agents.execution_agent import ExecutionAgent, execution_agent
from agents.evolution_agent import EvolutionAgent, evolution_agent

__all__ = [
    # Base classes
    "BaseAgent",
    "AgentResult",
    "AgentRunInfo",
    # Agent classes
    "LearningAgent",
    "ExecutionAgent",
    "EvolutionAgent",
    # Singleton instances
    "learning_agent",
    "execution_agent",
    "evolution_agent",
]
