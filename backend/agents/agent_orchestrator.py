"""
Agent Orchestrator (LangChain-Powered)
Coordinates execution of multiple agents in the matching pipeline.

Technology:
- LangChain RunnableSequence: Pipeline orchestration
- Google Gemini LLM: Pipeline summary generation
- Agent coordination with execution logging

Pipeline Flows:
1. User Registration -> Profiling Agent
2. Preference Setup -> Profiling + Analysis Agent
3. Find Matches -> Profile + Analysis + Scoring + Conflict + Recommendation Agents
4. Find Rooms -> Profile + Room Matching Agent
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnableSequence
from backend.agents.base_agent import BaseAgent, AgentResult, AgentStatus, get_llm, AgentLoggingCallback
from backend.agents.user_profiling_agent import UserProfilingAgent
from backend.agents.preference_analysis_agent import PreferenceAnalysisAgent
from backend.agents.compatibility_scoring_agent import CompatibilityScoringAgent
from backend.agents.room_matching_agent import RoomMatchingAgent
from backend.agents.conflict_detection_agent import ConflictDetectionAgent
from backend.agents.recommendation_engine_agent import RecommendationEngineAgent
from datetime import datetime
import logging
import json


logger = logging.getLogger('orchestrator')


class AgentOrchestrator:
    """
    LangChain-powered central controller for multi-agent system.
    Uses RunnableSequence for pipeline orchestration and Gemini for summaries.
    """

    def __init__(self):
        """Initialize orchestrator with LangChain pipeline support."""
        self.agents = {}
        self.execution_log = []
        self.logger = logging.getLogger('agent_orchestrator')
        self.callback_handler = AgentLoggingCallback('Orchestrator')

        # Initialize LLM for pipeline summaries
        self.llm = get_llm()
        self.summary_chain = self._build_summary_chain()

        # Register all agents
        self._register_agents()

    def _register_agents(self):
        """Register all available LangChain-powered agents."""
        agents_to_register = [
            UserProfilingAgent(),
            PreferenceAnalysisAgent(),
            CompatibilityScoringAgent(),
            RoomMatchingAgent(),
            ConflictDetectionAgent(),
            RecommendationEngineAgent(),
        ]

        for agent in agents_to_register:
            self.agents[agent.name] = agent
            self.logger.info(f"Registered agent: {agent.name} (v{agent.version})")

    def _build_summary_chain(self):
        """Build LangChain chain for generating pipeline execution summaries."""
        if not self.llm:
            return None

        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are the Pipeline Orchestrator in an AI roommate matching system. "
             "Summarize pipeline execution results concisely."),
            ("human",
             "Pipeline '{pipeline_name}' completed for user {user_id}.\n"
             "Agents executed: {agents_executed}\n"
             "Results summary: {results_summary}\n"
             "Duration: {duration_ms}ms\n\n"
             "Provide a brief JSON with keys: "
             "'summary' (1-sentence pipeline summary), "
             "'quality' ('excellent', 'good', 'partial', 'poor'), "
             "'next_steps' (list of suggested actions)."
             )
        ])

        return prompt | self.llm | StrOutputParser()

    def get_agent(self, agent_name):
        """Get an agent by name."""
        return self.agents.get(agent_name)

    def execute_agent(self, agent_name, **inputs):
        """
        Execute a single agent with logging.

        Args:
            agent_name: Name of agent to execute
            **inputs: Input parameters for agent

        Returns:
            AgentResult: Result from agent execution
        """
        if agent_name not in self.agents:
            error_msg = f"Agent not found: {agent_name}"
            self.logger.error(error_msg)
            return AgentResult('Orchestrator', AgentStatus.ERROR, error=error_msg)

        agent = self.agents[agent_name]

        try:
            self.logger.info(f"Executing {agent_name} with inputs: {list(inputs.keys())}")
            start_time = datetime.utcnow()

            result = agent.execute(**inputs)

            duration = (datetime.utcnow() - start_time).total_seconds() * 1000

            execution_record = {
                'agent': agent_name,
                'version': agent.version,
                'timestamp': datetime.utcnow().isoformat(),
                'status': result.status.value,
                'inputs': list(inputs.keys()),
                'has_error': result.error is not None,
                'duration_ms': round(duration, 2),
                'langchain_powered': True,
                'tools_available': [t.name for t in agent.tools] if hasattr(agent, 'tools') else []
            }
            self.execution_log.append(execution_record)

            self.logger.info(f"{agent_name} completed: {result.status.value} ({duration:.0f}ms)")
            return result

        except Exception as e:
            error_msg = f"Agent execution failed: {str(e)}"
            self.logger.error(error_msg)
            return AgentResult(agent_name, AgentStatus.ERROR, error=error_msg)

    def find_matches_for_user(self, user_id, min_score=60):
        """
        Complete matching pipeline using LangChain orchestration.

        Pipeline:
        1. User Profiling Agent - Validate user
        2. Preference Analysis Agent - Vectorize preferences
        3. Compatibility Scoring Agent - Score against all users
        4. Recommendation Engine - Generate recommendations (includes conflict check)

        Returns:
            Dict with combined results from all agents
        """
        self.logger.info(f"Starting LangChain match pipeline for user {user_id}")
        pipeline_start = datetime.utcnow()

        results = {}
        agents_executed = []

        # ── Step 1: Profile user (LangChain Agent) ──
        self.logger.info("Step 1: User Profiling Agent (LangChain)")
        profile_result = self.execute_agent('User Profiling Agent', user_id=user_id)
        results['profiling'] = profile_result
        agents_executed.append('User Profiling Agent')

        if not profile_result.is_success():
            self.logger.error("Profiling failed, aborting pipeline")
            return {
                'success': False,
                'error': profile_result.error,
                'agents_attempted': 1,
                'pipeline': 'langchain'
            }

        # ── Step 2: Analyze preferences (LangChain Agent) ──
        self.logger.info("Step 2: Preference Analysis Agent (LangChain)")
        analysis_result = self.execute_agent('Preference Analysis Agent', user_id=user_id)
        results['analysis'] = analysis_result
        agents_executed.append('Preference Analysis Agent')

        if not analysis_result.is_success():
            self.logger.warning("Analysis partial, continuing pipeline")

        # ── Step 2.5: Vectorize ALL candidate users' preferences ──
        self.logger.info("Step 2.5: Vectorizing candidate users' preferences")
        from backend.models import User, PreferenceVector
        other_users = User.query.filter(
            (User.user_id != user_id) & (User.is_active == True)
        ).all()

        vectorized_count = 0
        for other_user in other_users[:50]:
            # Check if vector already exists and is fresh
            existing_vector = PreferenceVector.query.filter_by(user_id=other_user.user_id).first()
            if existing_vector and not existing_vector.is_stale():
                vectorized_count += 1
                continue

            # Vectorize this user's preferences
            vec_result = self.execute_agent('Preference Analysis Agent', user_id=other_user.user_id)
            if vec_result.is_success():
                vectorized_count += 1

        self.logger.info(f"Vectorized {vectorized_count}/{min(len(other_users), 50)} candidate users")

        # ── Step 3: Score against all other users (LangChain Agent) ──
        self.logger.info("Step 3: Compatibility Scoring Agent (LangChain)")

        scores_computed = 0
        for other_user in other_users[:50]:
            score_result = self.execute_agent(
                'Compatibility Scoring Agent',
                user_a_id=user_id,
                user_b_id=other_user.user_id,
                use_cache=True
            )
            if score_result.is_success():
                scores_computed += 1

        results['scoring'] = AgentResult(
            'Compatibility Scoring Agent', AgentStatus.SUCCESS,
            data={'scores_computed': scores_computed}
        )
        agents_executed.append('Compatibility Scoring Agent')
        self.logger.info(f"Computed {scores_computed} compatibility scores")

        # ── Step 3.5: Conflict Detection for scored pairs (LangChain Agent) ──
        self.logger.info("Step 3.5: Conflict Detection Agent (LangChain)")
        conflicts_detected = 0
        for other_user in other_users[:50]:
            try:
                conflict_result = self.execute_agent(
                    'Conflict Detection Agent',
                    user_a_id=user_id,
                    user_b_id=other_user.user_id
                )
                if conflict_result.is_success():
                    conflict_data = conflict_result.data or {}
                    conflicts_detected += conflict_data.get('conflicts_found', 0)
            except Exception as e:
                self.logger.warning(f"Conflict detection failed for pair ({user_id}, {other_user.user_id}): {e}")

        results['conflicts'] = AgentResult(
            'Conflict Detection Agent', AgentStatus.SUCCESS,
            data={'conflicts_detected': conflicts_detected}
        )
        agents_executed.append('Conflict Detection Agent')
        self.logger.info(f"Detected {conflicts_detected} conflicts")

        # ── Step 4: Generate recommendations (LangChain Agent) ──
        self.logger.info("Step 4: Recommendation Engine Agent (LangChain)")
        recommendation_result = self.execute_agent(
            'Recommendation Engine Agent',
            user_id=user_id, min_score=min_score, limit=20
        )
        results['recommendations'] = recommendation_result
        agents_executed.append('Recommendation Engine Agent')

        # ── Pipeline complete: Generate AI summary ──
        pipeline_duration = (datetime.utcnow() - pipeline_start).total_seconds() * 1000
        all_success = all(
            r.is_success() for r in [profile_result, analysis_result, recommendation_result]
        )

        ai_pipeline_summary = None
        recs = recommendation_result.data.get('recommendations', []) if recommendation_result.is_success() else []

        if self.summary_chain and recs:
            try:
                summary_response = self.summary_chain.invoke({
                    'pipeline_name': 'Find Matches',
                    'user_id': user_id,
                    'agents_executed': ', '.join(agents_executed),
                    'results_summary': f"{scores_computed} scores computed, {len(recs)} recommendations generated",
                    'duration_ms': round(pipeline_duration)
                }, config={"callbacks": [self.callback_handler]})
                ai_pipeline_summary = self._parse_summary(summary_response)
            except Exception as e:
                self.logger.warning(f"Pipeline summary failed: {e}")

        return {
            'success': all_success,
            'user_id': user_id,
            'recommendations': recs,
            'metrics': {
                'profile_complete': profile_result.metadata.get('profile_complete'),
                'scores_computed': scores_computed,
                'recommendations_generated': len(recs),
                'pipeline_duration_ms': round(pipeline_duration),
                'agents_executed': agents_executed
            },
            'ai_pipeline_summary': ai_pipeline_summary,
            'pipeline': 'langchain',
            'detailed_results': results
        }

    def find_rooms_for_user(self, user_id, limit=20):
        """
        Room search pipeline using LangChain orchestration.

        Pipeline:
        1. User Profiling Agent - Validate user
        2. Room Matching Agent - Filter rooms by preferences
        3. Conflict Detection Agent - Check user-room conflicts

        Returns:
            Dict with room matches
        """
        self.logger.info(f"Starting LangChain room search pipeline for user {user_id}")

        results = {}

        # Step 1: Profile user
        self.logger.info("Step 1: User Profiling Agent (LangChain)")
        profile_result = self.execute_agent('User Profiling Agent', user_id=user_id)
        results['profiling'] = profile_result

        if not profile_result.is_success():
            return {'success': False, 'error': profile_result.error, 'pipeline': 'langchain'}

        # Step 2: Find matching rooms
        self.logger.info("Step 2: Room Matching Agent (LangChain)")
        room_result = self.execute_agent('Room Matching Agent', user_id=user_id, limit=limit)
        results['room_matching'] = room_result

        if not room_result.is_success():
            return {'success': False, 'error': room_result.error, 'pipeline': 'langchain'}

        # Step 3: Check conflicts for top rooms
        rooms = room_result.data.get('rooms', [])

        for room in rooms[:10]:
            conflict_result = self.execute_agent(
                'Conflict Detection Agent',
                user_id=user_id,
                room_id=room['room_id']
            )
            if conflict_result.is_success():
                room['conflicts'] = conflict_result.data

        return {
            'success': True,
            'user_id': user_id,
            'rooms': rooms,
            'count': len(rooms),
            'pipeline': 'langchain',
            'detailed_results': results
        }

    def _parse_summary(self, raw):
        """Parse LLM pipeline summary response."""
        try:
            cleaned = raw.strip()
            if cleaned.startswith('```json'):
                cleaned = cleaned[7:]
            if cleaned.startswith('```'):
                cleaned = cleaned[3:]
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]
            result = json.loads(cleaned.strip())
            result['llm_generated'] = True
            return result
        except (json.JSONDecodeError, ValueError):
            return {'summary': raw[:200] if raw else 'Pipeline completed', 'llm_generated': True}

    def get_execution_log(self, last_n=None):
        """Get execution log, optionally last N records."""
        if last_n:
            return self.execution_log[-last_n:]
        return self.execution_log

    def clear_execution_log(self):
        """Clear the execution log."""
        self.execution_log = []

    def get_agent_status(self):
        """
        Get status of all registered agents with LangChain metadata.

        Returns:
            Dict mapping agent names to status info
        """
        status = {}
        for agent_name, agent in self.agents.items():
            agent_status = agent.get_status()
            agent_status['langchain_tools'] = [t.name for t in agent.tools] if hasattr(agent, 'tools') else []
            agent_status['llm_enabled'] = agent.llm is not None if hasattr(agent, 'llm') else False
            status[agent_name] = agent_status
        return status

    def get_execution_summary(self):
        """Get summary of execution attempts with LangChain metrics."""
        total = len(self.execution_log)
        successful = sum(1 for ex in self.execution_log if ex.get('status') == 'success')
        failed = sum(1 for ex in self.execution_log if ex.get('has_error'))

        by_agent = {}
        for ex in self.execution_log:
            agent = ex.get('agent', 'unknown')
            if agent not in by_agent:
                by_agent[agent] = {'total': 0, 'successful': 0, 'failed': 0, 'avg_duration_ms': 0}
            by_agent[agent]['total'] += 1
            if ex.get('status') == 'success':
                by_agent[agent]['successful'] += 1
            if ex.get('has_error'):
                by_agent[agent]['failed'] += 1

        # Compute average durations
        for agent_name in by_agent:
            durations = [ex.get('duration_ms', 0) for ex in self.execution_log if ex.get('agent') == agent_name]
            if durations:
                by_agent[agent_name]['avg_duration_ms'] = round(sum(durations) / len(durations), 2)

        return {
            'total_executions': total,
            'successful': successful,
            'failed': failed,
            'success_rate': (successful / total * 100) if total > 0 else 0,
            'by_agent': by_agent,
            'framework': 'LangChain',
            'llm_provider': 'Google Gemini'
        }

    def get_pipeline_info(self):
        """Get information about the LangChain-powered pipelines."""
        return {
            'framework': 'LangChain',
            'llm_provider': 'Google Gemini',
            'llm_available': self.llm is not None,
            'agents': {
                name: {
                    'version': agent.version,
                    'tools': [t.name for t in agent.tools] if hasattr(agent, 'tools') else [],
                    'llm_enabled': agent.llm is not None if hasattr(agent, 'llm') else False
                }
                for name, agent in self.agents.items()
            },
            'pipelines': {
                'find_matches': {
                    'agents': [
                        'User Profiling Agent',
                        'Preference Analysis Agent',
                        'Compatibility Scoring Agent',
                        'Recommendation Engine Agent'
                    ],
                    'description': 'Complete roommate matching pipeline with LLM explanations'
                },
                'find_rooms': {
                    'agents': [
                        'User Profiling Agent',
                        'Room Matching Agent',
                        'Conflict Detection Agent'
                    ],
                    'description': 'Room search pipeline with AI-powered room scoring'
                }
            }
        }


# Global orchestrator instance
_orchestrator_instance = None


def get_orchestrator():
    """
    Get or create the global orchestrator instance.

    Returns:
        AgentOrchestrator instance (LangChain-powered)
    """
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = AgentOrchestrator()
    return _orchestrator_instance
