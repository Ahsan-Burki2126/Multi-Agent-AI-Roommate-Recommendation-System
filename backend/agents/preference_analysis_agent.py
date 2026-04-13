"""
Preference Analysis Agent (LangChain-Powered)
Converts raw preferences into numerical vectors for compatibility analysis.

Technology:
- LangChain Tools: vectorize_preferences, analyze_patterns
- Google Gemini LLM: Preference pattern insights
- NumPy: Vector mathematics and normalization
- Rule-based fallback when LLM unavailable

Status: AGENT 2 of 6
"""

from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from backend.agents.base_agent import BaseAgent, AgentResult, AgentStatus
from backend.database import db
from backend.models import User, UserPreference, PreferenceVector
from datetime import datetime
import numpy as np
import json


class PreferenceAnalysisAgent(BaseAgent):
    """
    LangChain-powered preference analysis agent.
    Vectorizes preferences using NumPy and analyzes patterns with Gemini.
    """

    def __init__(self):
        super().__init__(
            'Preference Analysis Agent', '2.0',
            system_prompt=(
                "You are the Preference Analysis Agent in an AI roommate matching system. "
                "You analyze user preference patterns to identify matching opportunities. "
                "You use numerical vectorization and pattern recognition to understand "
                "what users are looking for in a roommate."
            )
        )
        self.pattern_chain = self._build_pattern_chain()

    def _build_pattern_chain(self):
        """Build LangChain chain for preference pattern analysis."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human",
             "Analyze these roommate preferences for user matching:\n"
             "Preferences: {preferences_json}\n"
             "Vector (6D): {vector}\n"
             "Vector Norm: {norm}\n\n"
             "Provide a brief JSON response with keys: "
             "'pattern_type' (e.g. 'budget-conscious', 'social butterfly', 'quiet studious'), "
             "'key_priorities' (top 3 priorities as list), "
             "'flexibility_score' (0-100, how flexible are they), "
             "'ideal_match_traits' (list of 3 ideal roommate traits), "
             "'analysis' (1-2 sentence summary)."
             )
        ])
        return self.create_chain(prompt)

    def _register_tools(self):
        """Register LangChain tools for preference analysis."""

        @tool
        def vectorize_user_preferences(user_id: int) -> str:
            """Convert user preferences to a 6-dimensional numerical vector using NumPy."""
            prefs = UserPreference.query.filter_by(user_id=user_id).first()
            if not prefs:
                return json.dumps({'error': f'No preferences for user {user_id}'})

            budget_min = float(prefs.budget_min or 300)
            budget_max = float(prefs.budget_max or 1500)
            budget_normalized = min(1.0, ((budget_min + budget_max) / 2.0) / 2000.0)
            age_min = float(prefs.age_min or 18)
            age_max = float(prefs.age_max or 65)
            age_normalized = min(1.0, ((age_min + age_max) / 2.0) / 80.0)
            noise_normalized = min(1.0, max(0.0, float(prefs.noise_tolerance or 5) / 10.0))
            smoking_normalized = 1.0 if prefs.smoking_ok else 0.0
            pets_normalized = 1.0 if prefs.pets_ok else 0.0
            _clean_map = {'Very Clean': 10, 'Clean': 7, 'Average': 5, 'Relaxed': 2}
            cleanliness_normalized = min(1.0, max(0.0, float(_clean_map.get(prefs.cleanliness_level, 5)) / 10.0))

            vector = [budget_normalized, age_normalized, noise_normalized,
                     smoking_normalized, pets_normalized, cleanliness_normalized]
            norm = float(np.linalg.norm(vector))

            return json.dumps({
                'user_id': user_id, 'vector': vector,
                'norm': round(norm, 4), 'dimensions': 6,
                'labels': ['budget', 'age', 'noise_tolerance', 'smoking', 'pets', 'cleanliness']
            })

        @tool
        def compute_vector_similarity(vector_a: str, vector_b: str) -> str:
            """Compute cosine similarity between two preference vectors."""
            va = np.array(json.loads(vector_a), dtype=np.float32)
            vb = np.array(json.loads(vector_b), dtype=np.float32)
            dot = float(np.dot(va, vb))
            norm_a = float(np.linalg.norm(va))
            norm_b = float(np.linalg.norm(vb))
            if norm_a == 0 or norm_b == 0:
                similarity = 0.5
            else:
                similarity = dot / (norm_a * norm_b)
            return json.dumps({'similarity': round(float(np.clip(similarity, 0, 1)), 4)})

        return [vectorize_user_preferences, compute_vector_similarity]

    def execute(self, **inputs):
        """
        Vectorize user preferences and analyze patterns.

        Inputs:
        - user_id (int): User whose preferences to vectorize
        - force_recompute (bool, optional): Ignore cache

        Returns:
            AgentResult with vector data and AI pattern analysis
        """
        try:
            user_id = inputs.get('user_id')
            force_recompute = inputs.get('force_recompute', False)

            is_valid, missing = self.validate_inputs(['user_id'], inputs)
            if not is_valid:
                return AgentResult(
                    self.name, AgentStatus.ERROR,
                    error=f"Missing required inputs: {missing}"
                )

            user = User.query.get(user_id)
            if not user:
                return AgentResult(self.name, AgentStatus.ERROR, error=f"User {user_id} not found")

            prefs = UserPreference.query.filter_by(user_id=user_id).first()
            if not prefs:
                return AgentResult(self.name, AgentStatus.ERROR, error=f"User {user_id} has no preferences")

            # Check cache
            if not force_recompute:
                cached_vector = PreferenceVector.query.filter_by(user_id=user_id).first()
                if cached_vector and not cached_vector.is_stale():
                    from datetime import timezone
                    age_seconds = int(
                        (datetime.utcnow() - cached_vector.computed_at).total_seconds()
                    )
                    return AgentResult(
                        self.name, AgentStatus.SUCCESS,
                        data=cached_vector.to_dict(),
                        metadata={'cached': True, 'age_seconds': age_seconds}
                    )

            # ── Tool: Vectorize preferences (NumPy) ──
            vector_data = self._vectorize_preferences(prefs)
            vector_norm = float(np.linalg.norm(vector_data))
            normalized_vector = vector_data / (vector_norm + 1e-10)

            # Save to database
            existing = PreferenceVector.query.filter_by(user_id=user_id).first()
            if existing:
                existing.vector_data = normalized_vector.tolist()
                existing.vector_norm = vector_norm
                existing.computed_at = datetime.utcnow()
            else:
                vector = PreferenceVector(
                    user_id=user_id,
                    vector_data=normalized_vector.tolist(),
                    vector_norm=vector_norm,
                    computed_at=datetime.utcnow()
                )
                db.session.add(vector)

            db.session.commit()

            # ── LLM: Analyze preference patterns (Gemini) ──
            pattern_analysis = None
            if self.pattern_chain:
                try:
                    prefs_dict = {
                        'budget_range': f"${prefs.budget_min or 300}-${prefs.budget_max or 1500}",
                        'age_range': f"{prefs.age_min or 18}-{prefs.age_max or 65}",
                        'noise_tolerance': f"{prefs.noise_tolerance or 5}/10",
                        'smoking_ok': bool(prefs.smoking_ok),
                        'pets_ok': bool(prefs.pets_ok),
                        'cleanliness': prefs.cleanliness_level or 'Average',
                        'preferred_location': prefs.preferred_location or 'Not set',
                        'gender_preference': prefs.gender_preference or 'Any'
                    }
                    llm_response = self.pattern_chain.invoke({
                        'preferences_json': json.dumps(prefs_dict),
                        'vector': normalized_vector.tolist(),
                        'norm': round(vector_norm, 4)
                    }, config={"callbacks": [self.callback_handler]})

                    pattern_analysis = self._parse_pattern_response(llm_response)
                except Exception as e:
                    self.logger.warning(f"LLM pattern analysis failed: {e}")

            if not pattern_analysis:
                pattern_analysis = self._fallback_pattern_analysis(prefs, vector_data)

            # Log decision
            self.log_decision(
                entity_type='user',
                entity_id=user_id,
                action='preferences_vectorized',
                details={
                    'vector_dimensions': len(vector_data),
                    'vector_norm': vector_norm,
                    'method': 'numpy_vectorization',
                    'pattern_analysis': pattern_analysis
                }
            )

            return AgentResult(
                self.name, AgentStatus.SUCCESS,
                data={
                    'user_id': user_id,
                    'vector': vector_data.tolist(),
                    'vector_norm': vector_norm,
                    'dimensions': len(vector_data),
                    'pattern_analysis': pattern_analysis,
                    'timestamp': datetime.utcnow().isoformat()
                },
                metadata={
                    'cached': False,
                    'llm_used': pattern_analysis.get('llm_generated', False),
                    'tools_used': [t.name for t in self.tools]
                }
            )

        except Exception as e:
            return AgentResult(self.name, AgentStatus.ERROR, error=str(e))

    def _parse_pattern_response(self, raw):
        """Parse LLM pattern analysis response."""
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
            return {
                'analysis': raw[:200] if raw else 'Pattern analysis unavailable',
                'pattern_type': 'general',
                'key_priorities': [],
                'llm_generated': True
            }

    def _fallback_pattern_analysis(self, prefs, vector):
        """Rule-based fallback pattern analysis."""
        priorities = []
        pattern_type = 'balanced'

        budget_weight = float(prefs.budget_min or 300) / 2000.0
        if budget_weight < 0.25:
            priorities.append('Budget-conscious')
            pattern_type = 'budget-conscious'
        elif budget_weight > 0.5:
            priorities.append('Comfortable budget')

        clean_map = {'Very Clean': 10, 'Clean': 7, 'Average': 5, 'Relaxed': 2}
        clean_pref = clean_map.get(prefs.cleanliness_level, 5)
        if clean_pref >= 8:
            priorities.append('High cleanliness standards')
            pattern_type = 'neat and organized'
        elif clean_pref <= 3:
            priorities.append('Relaxed about cleanliness')

        noise_tol = float(prefs.noise_tolerance or 5)
        if noise_tol <= 3:
            priorities.append('Quiet environment preferred')
            pattern_type = 'quiet studious'
        elif noise_tol >= 8:
            priorities.append('Social and noise-tolerant')
            if pattern_type == 'balanced':
                pattern_type = 'social butterfly'

        if not prefs.smoking_ok:
            priorities.append('Non-smoking environment')
        if prefs.pets_ok:
            priorities.append('Pet-friendly')

        return {
            'pattern_type': pattern_type,
            'key_priorities': priorities[:3],
            'flexibility_score': int(noise_tol * 10),
            'ideal_match_traits': ['Compatible budget', 'Similar lifestyle', 'Respectful habits'],
            'analysis': f'User shows a {pattern_type} preference pattern with {len(priorities)} key priorities.',
            'llm_generated': False
        }

    def _vectorize_preferences(self, prefs):
        """Convert UserPreference to 6D NumPy vector."""
        try:
            budget_min = float(prefs.budget_min or 300)
            budget_max = float(prefs.budget_max or 1500)
            budget_normalized = min(1.0, ((budget_min + budget_max) / 2.0) / 2000.0)

            age_min = float(prefs.age_min or 18)
            age_max = float(prefs.age_max or 65)
            age_normalized = min(1.0, ((age_min + age_max) / 2.0) / 80.0)

            noise_normalized = min(1.0, max(0.0, float(prefs.noise_tolerance or 5) / 10.0))
            smoking_normalized = 1.0 if prefs.smoking_ok else 0.0
            pets_normalized = 1.0 if prefs.pets_ok else 0.0
            _cmap = {'Very Clean': 10, 'Clean': 7, 'Average': 5, 'Relaxed': 2}
            cleanliness_normalized = min(1.0, max(0.0, float(_cmap.get(prefs.cleanliness_level, 5)) / 10.0))

            return np.array([
                budget_normalized, age_normalized, noise_normalized,
                smoking_normalized, pets_normalized, cleanliness_normalized
            ], dtype=np.float32)
        except Exception as e:
            self.logger.error(f"Vectorization failed: {e}")
            return np.array([0.5, 0.5, 0.5, 0.5, 0.5, 0.5], dtype=np.float32)
