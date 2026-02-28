"""
Compatibility Scoring Agent (LangChain-Powered)
Computes compatibility scores between users using vectorized preferences.

Technology:
- LangChain Tools: cosine_similarity, lifestyle_score, budget_score, habits_score
- Google Gemini LLM: Score interpretation and insights
- NumPy: Vector mathematics for cosine similarity
- Rule-based fallback when LLM unavailable

Status: AGENT 3 of 6
"""

from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from backend.agents.base_agent import BaseAgent, AgentResult, AgentStatus
from backend.database import db
from backend.models import User, PreferenceVector, CompatibilityScore
from datetime import datetime, timedelta
import numpy as np
import json


class CompatibilityScoringAgent(BaseAgent):
    """
    LangChain-powered compatibility scoring agent.
    Uses cosine similarity + weighted scoring with Gemini for interpretation.
    """

    def __init__(self):
        super().__init__(
            'Compatibility Scoring Agent', '2.0',
            system_prompt=(
                "You are the Compatibility Scoring Agent in an AI roommate matching system. "
                "You interpret compatibility scores between users and provide insights "
                "about their potential as roommates. You explain what the scores mean "
                "in practical terms."
            )
        )
        self.weights = {
            'cosine_similarity': 0.30,
            'lifestyle': 0.20,
            'schedule': 0.20,
            'budget': 0.15,
            'habits': 0.15
        }
        self.interpretation_chain = self._build_interpretation_chain()

    def _build_interpretation_chain(self):
        """Build LangChain chain for score interpretation."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human",
             "Interpret this compatibility score between two roommate candidates:\n"
             "Overall Score: {overall_score}/100\n"
             "Cosine Similarity: {cosine_sim}\n"
             "Lifestyle Score: {lifestyle}/100\n"
             "Schedule Score: {schedule}/100\n"
             "Budget Score: {budget}/100\n"
             "Habits Score: {habits}/100\n"
             "User A: {user_a_info}\n"
             "User B: {user_b_info}\n\n"
             "Provide a brief JSON response with keys: "
             "'interpretation' (2-3 sentence explanation of what the score means), "
             "'strongest_area' (which area is most compatible), "
             "'weakest_area' (which area needs attention), "
             "'roommate_potential' ('excellent', 'good', 'fair', or 'poor'), "
             "'advice' (one practical tip for these two)."
             )
        ])
        return self.create_chain(prompt)

    def _register_tools(self):
        """Register LangChain tools for compatibility scoring."""

        @tool
        def compute_cosine_similarity(vector_a_json: str, vector_b_json: str) -> str:
            """Compute cosine similarity between two preference vectors using NumPy dot product."""
            vec_a = np.array(json.loads(vector_a_json), dtype=np.float32)
            vec_b = np.array(json.loads(vector_b_json), dtype=np.float32)
            dot_product = float(np.dot(vec_a, vec_b))
            norm_a = float(np.linalg.norm(vec_a))
            norm_b = float(np.linalg.norm(vec_b))
            if norm_a == 0 or norm_b == 0:
                similarity = 0.5
            else:
                similarity = dot_product / (norm_a * norm_b)
            return json.dumps({'similarity': round(float(np.clip(similarity, 0, 1)), 4)})

        @tool
        def compute_budget_compatibility(budget_a_min: float, budget_a_max: float,
                                         budget_b_min: float, budget_b_max: float) -> str:
            """Compute budget compatibility score based on budget range overlap."""
            overlap_min = max(budget_a_min, budget_b_min)
            overlap_max = min(budget_a_max, budget_b_max)
            if overlap_min > overlap_max:
                return json.dumps({'score': 30, 'overlap': False})
            overlap_range = overlap_max - overlap_min
            a_range = max(budget_a_max - budget_a_min, 1)
            b_range = max(budget_b_max - budget_b_min, 1)
            overlap_pct = min(overlap_range / a_range, overlap_range / b_range)
            score = int(50 + (overlap_pct * 50))
            return json.dumps({'score': min(100, score), 'overlap': True, 'overlap_percent': round(overlap_pct, 2)})

        @tool
        def compute_habits_compatibility(smoking_a: bool, smoking_b: bool,
                                         pets_a: bool, pets_b: bool,
                                         clean_a: float, clean_b: float) -> str:
            """Compute habits compatibility based on smoking, pets, and cleanliness preferences."""
            score = 100
            if smoking_a != smoking_b:
                score -= 30
            if pets_a != pets_b:
                score -= 20
            clean_gap = abs(clean_a - clean_b)
            if clean_gap > 5:
                score -= 15
            elif clean_gap > 3:
                score -= 8
            return json.dumps({'score': max(0, score), 'clean_gap': round(clean_gap, 1)})

        return [compute_cosine_similarity, compute_budget_compatibility, compute_habits_compatibility]

    def execute(self, **inputs):
        """
        Score compatibility between two users.

        Inputs:
        - user_a_id (int): First user
        - user_b_id (int): Second user
        - use_cache (bool, optional): Use cached score

        Returns:
            AgentResult with score breakdown and AI interpretation
        """
        try:
            user_a_id = inputs.get('user_a_id')
            user_b_id = inputs.get('user_b_id')
            use_cache = inputs.get('use_cache', True)

            is_valid, missing = self.validate_inputs(['user_a_id', 'user_b_id'], inputs)
            if not is_valid:
                return AgentResult(self.name, AgentStatus.ERROR, error=f"Missing: {missing}")

            # Check cache
            if use_cache:
                cached_score = CompatibilityScore.query.filter(
                    ((CompatibilityScore.user_a_id == user_a_id) &
                     (CompatibilityScore.user_b_id == user_b_id)) |
                    ((CompatibilityScore.user_a_id == user_b_id) &
                     (CompatibilityScore.user_b_id == user_a_id))
                ).first()

                if cached_score and not cached_score.is_stale():
                    return AgentResult(
                        self.name, AgentStatus.SUCCESS,
                        data=cached_score.to_dict(),
                        metadata={'cached': True, 'cached_at': cached_score.computed_at.isoformat()}
                    )

            # Load users and vectors
            user_a = User.query.get(user_a_id)
            user_b = User.query.get(user_b_id)
            if not user_a or not user_b:
                return AgentResult(self.name, AgentStatus.ERROR, error="One or both users not found")

            vector_a = PreferenceVector.query.filter_by(user_id=user_a_id).first()
            vector_b = PreferenceVector.query.filter_by(user_id=user_b_id).first()
            if not vector_a or not vector_b:
                return AgentResult(self.name, AgentStatus.ERROR, error="One or both users missing preference vectors")

            # ── Tool: Compute scores ──
            cosine_sim = self._cosine_similarity(vector_a, vector_b)
            lifestyle_score = self._estimate_lifestyle_score(user_a, user_b)
            schedule_score = self._estimate_schedule_score(user_a, user_b)
            budget_score = self._estimate_budget_score(user_a, user_b)
            habits_score = self._estimate_habits_score(user_a, user_b)
            age_match_score = self._estimate_age_match_score(user_a, user_b)

            # Weighted total
            overall_score = int(
                cosine_sim * 100 * self.weights['cosine_similarity'] +
                lifestyle_score * self.weights['lifestyle'] +
                schedule_score * self.weights['schedule'] +
                budget_score * self.weights['budget'] +
                habits_score * self.weights['habits']
            )

            # Save to database
            existing = CompatibilityScore.query.filter(
                ((CompatibilityScore.user_a_id == user_a_id) &
                 (CompatibilityScore.user_b_id == user_b_id)) |
                ((CompatibilityScore.user_a_id == user_b_id) &
                 (CompatibilityScore.user_b_id == user_a_id))
            ).first()

            if existing:
                existing.overall_score = overall_score
                existing.lifestyle_score = int(lifestyle_score)
                existing.schedule_score = int(schedule_score)
                existing.budget_score = int(budget_score)
                existing.habits_score = int(habits_score)
                existing.age_match_score = int(age_match_score)
                existing.computed_at = datetime.utcnow()
            else:
                score_obj = CompatibilityScore(
                    user_a_id=user_a_id, user_b_id=user_b_id,
                    overall_score=overall_score,
                    lifestyle_score=int(lifestyle_score),
                    schedule_score=int(schedule_score),
                    budget_score=int(budget_score),
                    habits_score=int(habits_score),
                    age_match_score=int(age_match_score),
                    computed_at=datetime.utcnow()
                )
                db.session.add(score_obj)

            db.session.commit()

            # ── LLM: Score interpretation (Gemini) ──
            ai_interpretation = None
            if self.interpretation_chain:
                try:
                    llm_response = self.interpretation_chain.invoke({
                        'overall_score': overall_score,
                        'cosine_sim': round(cosine_sim, 3),
                        'lifestyle': int(lifestyle_score),
                        'schedule': int(schedule_score),
                        'budget': int(budget_score),
                        'habits': int(habits_score),
                        'user_a_info': f"{user_a.full_name} from {user_a.city or 'unknown'}",
                        'user_b_info': f"{user_b.full_name} from {user_b.city or 'unknown'}"
                    }, config={"callbacks": [self.callback_handler]})
                    ai_interpretation = self._parse_interpretation(llm_response)
                except Exception as e:
                    self.logger.warning(f"LLM interpretation failed: {e}")

            if not ai_interpretation:
                ai_interpretation = self._fallback_interpretation(
                    overall_score, cosine_sim, lifestyle_score, schedule_score, budget_score, habits_score
                )

            # Log decision
            self.log_decision(
                entity_type='score',
                entity_id=existing.score_id if existing else (score_obj.score_id if 'score_obj' in dir() else 0),
                action='computed_compatibility_score',
                details={
                    'user_a_id': user_a_id, 'user_b_id': user_b_id,
                    'overall_score': overall_score,
                    'cosine_similarity': round(cosine_sim, 3),
                    'ai_interpretation': ai_interpretation
                }
            )

            return AgentResult(
                self.name, AgentStatus.SUCCESS,
                data={
                    'user_a_id': user_a_id, 'user_b_id': user_b_id,
                    'overall_score': overall_score,
                    'cosine_similarity': round(cosine_sim, 3),
                    'component_scores': {
                        'lifestyle': int(lifestyle_score), 'schedule': int(schedule_score),
                        'budget': int(budget_score), 'habits': int(habits_score)
                    },
                    'weights': self.weights,
                    'ai_interpretation': ai_interpretation,
                    'computed_at': datetime.utcnow().isoformat()
                },
                metadata={
                    'cached': False,
                    'llm_used': ai_interpretation.get('llm_generated', False),
                    'tools_used': [t.name for t in self.tools]
                }
            )

        except Exception as e:
            return AgentResult(self.name, AgentStatus.ERROR, error=str(e))

    def _parse_interpretation(self, raw):
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
                'interpretation': raw[:200] if raw else 'Score interpretation unavailable',
                'llm_generated': True
            }

    def _fallback_interpretation(self, overall, cosine, lifestyle, schedule, budget, habits):
        scores = {'lifestyle': lifestyle, 'schedule': schedule, 'budget': budget, 'habits': habits}
        strongest = max(scores, key=scores.get)
        weakest = min(scores, key=scores.get)

        if overall >= 80:
            potential = 'excellent'
            interp = f"Strong compatibility at {overall}%. These users share very similar preferences."
        elif overall >= 65:
            potential = 'good'
            interp = f"Good compatibility at {overall}%. Most preference areas align well."
        elif overall >= 50:
            potential = 'fair'
            interp = f"Moderate compatibility at {overall}%. Some preference differences to discuss."
        else:
            potential = 'poor'
            interp = f"Low compatibility at {overall}%. Significant preference mismatches."

        return {
            'interpretation': interp,
            'strongest_area': strongest,
            'weakest_area': weakest,
            'roommate_potential': potential,
            'advice': f"Focus on discussing {weakest} expectations early.",
            'llm_generated': False
        }

    # ── Scoring methods ──

    CLEANLINESS_MAP = {'Very Clean': 10, 'Clean': 7, 'Average': 5, 'Relaxed': 2}
    SCHEDULE_COMPAT = {
        ('9-5 Job', '9-5 Job'): 95, ('Night Shift', 'Night Shift'): 95,
        ('Student', 'Student'): 90, ('Flexible', 'Flexible'): 85,
        ('9-5 Job', 'Student'): 70, ('Student', '9-5 Job'): 70,
        ('Flexible', '9-5 Job'): 75, ('9-5 Job', 'Flexible'): 75,
        ('Flexible', 'Student'): 75, ('Student', 'Flexible'): 75,
        ('Flexible', 'Night Shift'): 65, ('Night Shift', 'Flexible'): 65,
        ('9-5 Job', 'Night Shift'): 30, ('Night Shift', '9-5 Job'): 30,
        ('Student', 'Night Shift'): 45, ('Night Shift', 'Student'): 45,
    }

    def _cosine_similarity(self, vector_a, vector_b):
        try:
            vec_a = np.array(vector_a.vector_data, dtype=np.float32)
            vec_b = np.array(vector_b.vector_data, dtype=np.float32)
            dot_product = np.dot(vec_a, vec_b)
            norm_a = np.linalg.norm(vec_a)
            norm_b = np.linalg.norm(vec_b)
            if norm_a == 0 or norm_b == 0:
                return 0.5
            similarity = dot_product / (norm_a * norm_b)
            return float(np.clip(similarity, 0, 1))
        except Exception as e:
            self.logger.error(f"Cosine similarity failed: {e}")
            return 0.5

    def _estimate_lifestyle_score(self, user_a, user_b):
        """Real lifestyle scoring: city match + cleanliness + noise tolerance."""
        score = 50  # base
        try:
            prefs_a = user_a.preferences
            prefs_b = user_b.preferences
            if not prefs_a or not prefs_b:
                return score

            # City match (up to +20)
            if user_a.city and user_b.city and user_a.city.lower() == user_b.city.lower():
                score += 20

            # Cleanliness compatibility (up to +20)
            clean_a = self.CLEANLINESS_MAP.get(prefs_a.cleanliness_level, 5)
            clean_b = self.CLEANLINESS_MAP.get(prefs_b.cleanliness_level, 5)
            clean_gap = abs(clean_a - clean_b)
            if clean_gap == 0:
                score += 20
            elif clean_gap <= 2:
                score += 15
            elif clean_gap <= 4:
                score += 8
            # else: +0

            # Noise tolerance compatibility (up to +10)
            noise_a = int(prefs_a.noise_tolerance or 5)
            noise_b = int(prefs_b.noise_tolerance or 5)
            noise_gap = abs(noise_a - noise_b)
            if noise_gap <= 2:
                score += 10
            elif noise_gap <= 4:
                score += 5
        except Exception as e:
            self.logger.warning(f"Lifestyle scoring error: {e}")

        return min(100, max(0, score))

    def _estimate_schedule_score(self, user_a, user_b):
        """Real schedule scoring based on schedule type compatibility."""
        try:
            prefs_a = user_a.preferences
            prefs_b = user_b.preferences
            if not prefs_a or not prefs_b:
                return 60
            sched_a = prefs_a.schedule or 'Flexible'
            sched_b = prefs_b.schedule or 'Flexible'
            return self.SCHEDULE_COMPAT.get((sched_a, sched_b), 55)
        except Exception as e:
            self.logger.warning(f"Schedule scoring error: {e}")
            return 60

    def _estimate_budget_score(self, user_a, user_b):
        try:
            prefs_a = user_a.preferences
            prefs_b = user_b.preferences
            if not prefs_a or not prefs_b:
                return 50
            a_min, a_max = float(prefs_a.budget_min or 300), float(prefs_a.budget_max or 1500)
            b_min, b_max = float(prefs_b.budget_min or 300), float(prefs_b.budget_max or 1500)
            overlap_min = max(a_min, b_min)
            overlap_max = min(a_max, b_max)
            if overlap_min > overlap_max:
                return 20  # No overlap at all
            overlap_range = overlap_max - overlap_min
            a_range = max(a_max - a_min, 1)
            b_range = max(b_max - b_min, 1)
            overlap_percent = min(overlap_range / a_range, overlap_range / b_range)
            return min(100, int(40 + (overlap_percent * 60)))
        except:
            return 50

    def _estimate_habits_score(self, user_a, user_b):
        try:
            prefs_a = user_a.preferences
            prefs_b = user_b.preferences
            if not prefs_a or not prefs_b:
                return 50
            score = 100
            # Smoking mismatch is a big deal
            if prefs_a.smoking_ok != prefs_b.smoking_ok:
                score -= 35
            # Pets mismatch
            if prefs_a.pets_ok != prefs_b.pets_ok:
                score -= 25
            # Cleanliness gap
            clean_a = self.CLEANLINESS_MAP.get(prefs_a.cleanliness_level, 5)
            clean_b = self.CLEANLINESS_MAP.get(prefs_b.cleanliness_level, 5)
            clean_gap = abs(clean_a - clean_b)
            if clean_gap >= 5:
                score -= 20
            elif clean_gap >= 3:
                score -= 10
            return max(0, score)
        except:
            return 50

    def _estimate_age_match_score(self, user_a, user_b):
        """Compute age range compatibility."""
        try:
            prefs_a = user_a.preferences
            prefs_b = user_b.preferences
            if not prefs_a or not prefs_b:
                return 70
            a_min = int(prefs_a.age_min or 18)
            a_max = int(prefs_a.age_max or 65)
            b_min = int(prefs_b.age_min or 18)
            b_max = int(prefs_b.age_max or 65)
            overlap_min = max(a_min, b_min)
            overlap_max = min(a_max, b_max)
            if overlap_min > overlap_max:
                return 20  # No age overlap
            overlap_range = overlap_max - overlap_min
            a_range = max(a_max - a_min, 1)
            b_range = max(b_max - b_min, 1)
            overlap_pct = min(overlap_range / a_range, overlap_range / b_range)
            return min(100, int(40 + (overlap_pct * 60)))
        except:
            return 70
