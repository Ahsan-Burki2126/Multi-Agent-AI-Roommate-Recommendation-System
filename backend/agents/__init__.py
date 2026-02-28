"""
Multi-Agent System Package (LangChain-Powered)

This module contains the LangChain-powered intelligent agents
that drive the roommate matching system.

Framework: LangChain + Google Gemini LLM
Each agent uses LangChain tools, chains, and Gemini for AI reasoning.

Agents Included:
1. UserProfilingAgent - Validates user data (LangChain tools + Gemini analysis)
2. PreferenceAnalysisAgent - Vectorizes preferences (NumPy + Gemini patterns)
3. CompatibilityScoringAgent - Computes match scores (NumPy + Gemini interpretation)
4. RoomMatchingAgent - Filters and scores rooms (LangChain tools + Gemini summary)
5. ConflictDetectionAgent - Detects incompatibilities (LangChain tools + Gemini analysis)
6. RecommendationEngineAgent - Ranks with AI explanations (LangChain + Gemini NL)

Plus the AgentOrchestrator that coordinates them with LangChain pipelines.

Example Usage:
    from backend.agents import get_orchestrator
    
    orchestrator = get_orchestrator()
    matches = orchestrator.find_matches_for_user(user_id=123)
"""

from backend.agents.base_agent import BaseAgent, AgentResult, AgentStatus
from backend.agents.user_profiling_agent import UserProfilingAgent
from backend.agents.preference_analysis_agent import PreferenceAnalysisAgent
from backend.agents.compatibility_scoring_agent import CompatibilityScoringAgent
from backend.agents.room_matching_agent import RoomMatchingAgent
from backend.agents.conflict_detection_agent import ConflictDetectionAgent
from backend.agents.recommendation_engine_agent import RecommendationEngineAgent
from backend.agents.agent_orchestrator import AgentOrchestrator, get_orchestrator

__all__ = [
    'BaseAgent',
    'AgentResult',
    'AgentStatus',
    'UserProfilingAgent',
    'PreferenceAnalysisAgent',
    'CompatibilityScoringAgent',
    'RoomMatchingAgent',
    'ConflictDetectionAgent',
    'RecommendationEngineAgent',
    'AgentOrchestrator',
    'get_orchestrator',
]
