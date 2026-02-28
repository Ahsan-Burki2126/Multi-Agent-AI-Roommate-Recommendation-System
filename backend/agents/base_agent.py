"""
LangChain-Powered Multi-Agent Base
====================================
Framework for building AI agents using LangChain + Google Gemini.

Each agent in this system:
1. Inherits from BaseAgent (LangChain integration)
2. Registers LangChain Tools for specific tasks
3. Uses Google Gemini LLM for reasoning & explanation
4. Logs all decisions for Explainable AI (XAI)
5. Falls back gracefully if LLM is unavailable

Technology Stack:
- LangChain: Agent framework, tools, chains, prompt templates
- Google Gemini: Large Language Model for reasoning
- NumPy: Numerical computations (cosine similarity, vectorization)
- SQLAlchemy: Database persistence
"""

from abc import ABC, abstractmethod
from enum import Enum
import json
import os
from datetime import datetime
import logging

# ═══════════════════════════════════════════════════════
# LangChain Framework Imports
# ═══════════════════════════════════════════════════════
from langchain_core.tools import tool, StructuredTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnablePassthrough, RunnableLambda, RunnableSequence
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════
# LangChain Callback Handler for Agent Logging
# ═══════════════════════════════════════════════════════

class AgentLoggingCallback(BaseCallbackHandler):
    """
    Custom LangChain callback handler for logging agent actions.
    Tracks tool invocations and LLM calls for auditability.
    """

    def __init__(self, agent_name):
        self.agent_name = agent_name
        self.tool_calls = []
        self.llm_calls = []
        self.logger = logging.getLogger(f'langchain.{agent_name}')

    def on_tool_start(self, serialized, input_str, **kwargs):
        tool_name = serialized.get('name', 'unknown')
        self.tool_calls.append({
            'tool': tool_name,
            'input': str(input_str)[:200],
            'timestamp': datetime.utcnow().isoformat()
        })
        self.logger.info(f"Tool called: {tool_name}")

    def on_tool_end(self, output, **kwargs):
        if self.tool_calls:
            self.tool_calls[-1]['output'] = str(output)[:200]
            self.tool_calls[-1]['completed'] = True

    def on_llm_start(self, serialized, prompts, **kwargs):
        model_id = 'gemini'
        if serialized and serialized.get('id'):
            model_id = serialized['id'][-1] if isinstance(serialized['id'], list) else str(serialized['id'])
        self.llm_calls.append({
            'model': model_id,
            'timestamp': datetime.utcnow().isoformat()
        })
        self.logger.info(f"LLM invoked (Google Gemini)")

    def on_llm_end(self, response, **kwargs):
        if self.llm_calls:
            self.llm_calls[-1]['completed'] = True
            self.llm_calls[-1]['finished_at'] = datetime.utcnow().isoformat()

    def reset(self):
        """Reset tracking for new execution."""
        self.tool_calls = []
        self.llm_calls = []

    def get_summary(self):
        """Get summary of all tracked calls."""
        return {
            'tool_calls': len(self.tool_calls),
            'llm_calls': len(self.llm_calls),
            'tools_used': [tc['tool'] for tc in self.tool_calls],
            'details': {
                'tool_calls': self.tool_calls,
                'llm_calls': self.llm_calls
            }
        }


# ═══════════════════════════════════════════════════════
# LLM Initialization (Google Gemini via LangChain)
# ═══════════════════════════════════════════════════════

def get_llm(temperature=0.3):
    """
    Initialize Google Gemini LLM via LangChain.

    Uses langchain-google-genai to connect to Google's Gemini API.
    Falls back to None if API key is not configured.

    Environment Variables:
        GOOGLE_API_KEY: Your Google AI Studio API key
        GEMINI_MODEL: Model name (default: gemini-2.0-flash)

    Returns:
        ChatGoogleGenerativeAI instance or None
    """
    api_key = os.getenv('GOOGLE_API_KEY', '')
    if not api_key:
        logger.warning("GOOGLE_API_KEY not set - agents will use rule-based fallback")
        return None

    model_name = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')

    try:
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=temperature,
            max_output_tokens=2048,
            timeout=15,
            max_retries=1,
        )
        logger.info(f"LangChain LLM initialized: Google Gemini ({model_name})")
        return llm
    except Exception as e:
        logger.error(f"Failed to initialize Gemini LLM: {e}")
        return None


# ═══════════════════════════════════════════════════════
# Agent Status & Result (Standard Output Format)
# ═══════════════════════════════════════════════════════

class AgentStatus(Enum):
    """Status of agent execution"""
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"


class AgentResult:
    """
    Standard result object returned by all agents.
    Includes LangChain execution metadata for transparency.
    """

    def __init__(self, agent_name, status, data=None, error=None, metadata=None):
        self.agent_name = agent_name
        self.status = status
        self.data = data
        self.error = error
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()

    def to_dict(self):
        return {
            'agent': self.agent_name,
            'status': self.status.value,
            'data': self.data,
            'error': self.error,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }

    def is_success(self):
        return self.status in [AgentStatus.SUCCESS, AgentStatus.PARTIAL]


# ═══════════════════════════════════════════════════════
# LangChain-Powered Base Agent
# ═══════════════════════════════════════════════════════

class BaseAgent(ABC):
    """
    Abstract base class for all LangChain-powered agents.

    Features:
    - Google Gemini LLM access via LangChain
    - LangChain Tool registration
    - LangChain Chain composition (prompt | llm | parser)
    - Custom callback handler for execution tracking
    - Decision audit logging for XAI
    - Graceful fallback when LLM is unavailable

    All agents must:
    1. Inherit from BaseAgent
    2. Implement _register_tools() to define LangChain Tools
    3. Implement execute() for agent logic
    4. Use self.invoke_llm() for AI reasoning
    """

    # Class-level LLM shared across all agents (singleton)
    _shared_llm = None
    _llm_initialized = False

    def __init__(self, agent_name, version='1.0',
                 system_prompt="You are a helpful AI agent in a roommate matching system."):
        self.name = agent_name
        self.version = version
        self.status = AgentStatus.IDLE
        self.last_result = None
        self.system_prompt = system_prompt
        self.logger = logging.getLogger(f'agent.{agent_name}')

        # Initialize shared LLM (once for all agents)
        if not BaseAgent._llm_initialized:
            BaseAgent._shared_llm = get_llm()
            BaseAgent._llm_initialized = True

        self.llm = BaseAgent._shared_llm

        # LangChain callback handler for this agent
        self.callback_handler = AgentLoggingCallback(agent_name)

        # Register LangChain tools
        self.tools = self._register_tools()

    @abstractmethod
    def _register_tools(self):
        """
        Register LangChain tools for this agent.
        Override in subclass to define agent-specific tools.

        Returns:
            List of LangChain Tool objects
        """
        return []

    @abstractmethod
    def execute(self, **inputs):
        """
        Execute the agent logic.
        Must be implemented by subclasses.

        Returns:
            AgentResult
        """
        pass

    # ─── LangChain LLM Methods ──────────────────────────

    def invoke_llm(self, user_prompt, system_prompt=None):
        """
        Invoke Google Gemini LLM via LangChain for reasoning.
        Falls back to None if LLM is unavailable.

        Args:
            user_prompt: The prompt/question for the LLM
            system_prompt: Override the default system prompt

        Returns:
            String response from Gemini, or None on failure
        """
        if not self.llm:
            return None

        try:
            self.callback_handler.reset()
            messages = []
            if system_prompt or self.system_prompt:
                messages.append(SystemMessage(content=system_prompt or self.system_prompt))
            messages.append(HumanMessage(content=user_prompt))

            response = self.llm.invoke(
                messages,
                config={"callbacks": [self.callback_handler]}
            )
            return response.content
        except Exception as e:
            self.logger.error(f"LLM invocation failed: {e}")
            return None

    def invoke_llm_json(self, user_prompt, system_prompt=None):
        """
        Invoke LLM and parse response as JSON.
        Handles markdown code blocks in response.

        Returns:
            Parsed dict/list, or None on failure
        """
        raw = self.invoke_llm(user_prompt, system_prompt)
        if not raw:
            return None
        try:
            cleaned = raw.strip()
            if cleaned.startswith('```json'):
                cleaned = cleaned[7:]
            if cleaned.startswith('```'):
                cleaned = cleaned[3:]
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]
            return json.loads(cleaned.strip())
        except (json.JSONDecodeError, ValueError):
            self.logger.warning("Failed to parse LLM response as JSON")
            return None

    def create_chain(self, prompt_template, output_parser=None):
        """
        Create a LangChain chain (prompt | llm | parser).

        Args:
            prompt_template: ChatPromptTemplate instance
            output_parser: Output parser (default: StrOutputParser)

        Returns:
            LangChain Runnable chain, or None if LLM unavailable
        """
        if not self.llm:
            return None
        parser = output_parser or StrOutputParser()
        return prompt_template | self.llm | parser

    # ─── Audit & Logging ─────────────────────────────────

    def log_decision(self, entity_type, entity_id, action, details=None):
        """Log agent decision for Explainable AI auditability."""
        try:
            from backend.database import db
            from backend.models.audit import AuditLog

            if details and isinstance(details, dict):
                # Include LangChain execution metadata
                details['langchain_metadata'] = self.callback_handler.get_summary()
                details_json = json.dumps(details, default=str)
            else:
                details_json = str(details) if details else None

            audit_entry = AuditLog(
                agent_name=self.name,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details_json
            )

            db.session.add(audit_entry)
            db.session.commit()
            self.logger.info(f"Decision logged: {action} on {entity_type}#{entity_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to log decision: {str(e)}")
            return False

    # ─── Utilities ────────────────────────────────────────

    def validate_inputs(self, required_inputs, provided_inputs):
        """Validate that all required inputs are provided."""
        missing = [key for key in required_inputs if key not in provided_inputs]
        return len(missing) == 0, missing

    def get_status(self):
        """Get agent status including LangChain info."""
        return {
            'name': self.name,
            'version': self.version,
            'status': self.status.value,
            'framework': 'LangChain',
            'llm': 'Google Gemini' if self.llm else 'Unavailable (rule-based mode)',
            'llm_model': os.getenv('GEMINI_MODEL', 'gemini-2.0-flash'),
            'tools': [t.name for t in self.tools] if self.tools else [],
            'tool_count': len(self.tools) if self.tools else 0,
            'last_execution': self.callback_handler.get_summary(),
            'last_result': self.last_result.to_dict() if self.last_result else None
        }

    def cache_result(self, key, value, ttl_seconds=None):
        """Cache computation result for later reuse."""
        try:
            self.logger.debug(f"Cached {key} (TTL: {ttl_seconds}s)")
            return True
        except Exception as e:
            self.logger.warning(f"Cache write failed: {str(e)}")
            return False

    def get_cached(self, key):
        """Retrieve cached value if exists."""
        return None
