"""
Recommendation Engine Agent (LangChain-Powered)
Generates personalized, ranked, and explainable recommendations.

Technology:
- LangChain Tools: rank_candidates, generate_explanation
- Google Gemini LLM: Rich natural language match explanations
- Rule-based fallback when LLM unavailable

Status: AGENT 6 of 6
"""

from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from backend.agents.base_agent import BaseAgent, AgentResult, AgentStatus
from backend.database import db
from backend.models import (
    User, CompatibilityScore, ConflictLog, Recommendation
)
from datetime import datetime
import json


class RecommendationEngineAgent(BaseAgent):
    """
    LangChain-powered recommendation engine.
    Combines scoring and conflict detection into final ranked recommendations
    with Gemini-generated natural language explanations.
    """

    def __init__(self):
        super().__init__(
            'Recommendation Engine Agent', '2.0',
            system_prompt=(
                "You are the Recommendation Engine Agent in an AI roommate matching system. "
                "You generate personalized, helpful match explanations for users. "
                "Be friendly, specific, and highlight both strengths and areas to discuss."
            )
        )
        self.explanation_chain = self._build_explanation_chain()

    def _build_explanation_chain(self):
        """Build LangChain chain for generating match explanations."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human",
             "Generate a match explanation for these two users:\n"
             "User A: {user_a_name} from {user_a_city}\n"
             "User B: {user_b_name} from {user_b_city} ({user_b_gender})\n"
             "Overall Score: {overall_score}/100\n"
             "Component Scores: lifestyle={lifestyle}, schedule={schedule}, "
             "budget={budget}, habits={habits}, age_match={age_match}\n"
             "Detail Level: {detail_level}\n\n"
             "Respond with a JSON object with these exact keys:\n"
             "'summary' (one-line summary mentioning user B's name),\n"
             "'details' (list of specific strength/concern strings),\n"
             "'full' (2-3 sentence paragraph explanation)."
             )
        ])
        return self.create_chain(prompt)

    def _register_tools(self):
        """Register LangChain tools for recommendation generation."""

        @tool
        def rank_candidates(scores_json: str, min_score: float) -> str:
            """Rank and filter match candidates by score, removing those below minimum threshold."""
            scores = json.loads(scores_json)
            filtered = [s for s in scores if s.get('overall', 0) >= min_score]
            filtered.sort(key=lambda x: x.get('overall', 0), reverse=True)
            return json.dumps({'ranked': filtered, 'count': len(filtered)})

        @tool
        def compute_match_strength(score: float) -> str:
            """Determine human-readable match strength label from a compatibility score."""
            if score >= 90:
                label = "Perfect Match"
            elif score >= 80:
                label = "Excellent Match"
            elif score >= 70:
                label = "Very Good Match"
            elif score >= 60:
                label = "Good Match"
            elif score >= 50:
                label = "Decent Match"
            else:
                label = "Okay Match"
            return json.dumps({'score': score, 'strength': label})

        return [rank_candidates, compute_match_strength]

    def execute(self, **inputs):
        """
        Generate recommendations for a user.

        Inputs:
        - user_id (int): User to generate recommendations for
        - min_score (int, optional): Minimum compatibility score (default 60)
        - limit (int, optional): Max recommendations (default 20)
        - explanation_detail (str, optional): 'brief', 'standard' (default), 'detailed'

        Returns:
            AgentResult with ranked recommendations and explanations
        """
        try:
            user_id = inputs.get('user_id')
            min_score = int(inputs.get('min_score', 60))
            limit = int(inputs.get('limit', 20))
            explanation_detail = inputs.get('explanation_detail', 'standard')

            is_valid, missing = self.validate_inputs(['user_id'], inputs)
            if not is_valid:
                return AgentResult(self.name, AgentStatus.ERROR, error=f"Missing: {missing}")

            user = User.query.get(user_id)
            if not user:
                return AgentResult(self.name, AgentStatus.ERROR, error=f"User {user_id} not found")

            # Get all compatibility scores for this user
            scores = CompatibilityScore.query.filter(
                (CompatibilityScore.user_a_id == user_id) |
                (CompatibilityScore.user_b_id == user_id)
            ).order_by(CompatibilityScore.overall_score.desc()).all()

            if not scores:
                return AgentResult(
                    self.name, AgentStatus.PARTIAL,
                    data={'recommendations': [], 'message': 'No compatible users found'},
                    metadata={'scores_found': 0}
                )

            # ── Filter and rank candidates ──
            recommendations = []
            llm_explanations_generated = 0

            for score_obj in scores:
                other_user_id = (
                    score_obj.user_b_id if score_obj.user_a_id == user_id
                    else score_obj.user_a_id
                )

                if score_obj.overall_score < min_score:
                    continue

                # Check for hard conflicts (blockers)
                has_hard_conflicts = ConflictLog.has_hard_conflicts(user_id, other_user_id)
                if has_hard_conflicts:
                    continue

                other_user = User.query.get(other_user_id)
                if not other_user or not other_user.is_active:
                    continue

                # ── LLM or Fallback: Generate explanation ──
                explanation = self._generate_explanation_llm(
                    user, other_user, score_obj, explanation_detail
                )
                if explanation.get('llm_generated'):
                    llm_explanations_generated += 1

                # Create or update recommendation in DB
                existing_rec = Recommendation.query.filter(
                    (Recommendation.requester_id == user_id) &
                    (Recommendation.match_id == other_user_id) &
                    (Recommendation.match_type == 'roommate')
                ).first()

                if existing_rec:
                    existing_rec.match_score = float(score_obj.overall_score)
                    existing_rec.explanation = json.dumps(explanation)
                else:
                    rec = Recommendation(
                        requester_id=user_id,
                        match_type='roommate',
                        match_id=other_user_id,
                        match_score=float(score_obj.overall_score),
                        explanation=json.dumps(explanation),
                        conflict_warnings=json.dumps([]),
                        created_at=datetime.utcnow()
                    )
                    db.session.add(rec)

                recommendations.append({
                    'user_id': other_user_id,
                    'score': float(score_obj.overall_score),
                    'user_name': other_user.full_name,
                    'city': other_user.city,
                    'gender': other_user.gender,
                    'bio': other_user.bio,
                    'explanation': explanation,
                    'components': {
                        'lifestyle': float(score_obj.lifestyle_score or 0),
                        'schedule': float(score_obj.schedule_score or 0),
                        'budget': float(score_obj.budget_score or 0),
                        'habits': float(score_obj.habits_score or 0),
                        'age_match': float(score_obj.age_match_score or 0)
                    },
                    'strength': self._get_match_strength(float(score_obj.overall_score))
                })

            db.session.commit()
            recommendations = recommendations[:limit]

            self.log_decision(
                entity_type='user', entity_id=user_id,
                action='generated_recommendations',
                details={
                    'recommendations_count': len(recommendations),
                    'min_score': min_score,
                    'total_candidates': len(scores),
                    'llm_explanations': llm_explanations_generated
                }
            )

            return AgentResult(
                self.name, AgentStatus.SUCCESS,
                data={
                    'user_id': user_id,
                    'recommendations': recommendations,
                    'count': len(recommendations),
                    'min_score_threshold': min_score,
                    'generated_at': datetime.utcnow().isoformat()
                },
                metadata={
                    'total_candidates_scored': len(scores),
                    'filtered_final': len(recommendations),
                    'explanation_level': explanation_detail,
                    'llm_explanations_generated': llm_explanations_generated,
                    'tools_used': [t.name for t in self.tools]
                }
            )

        except Exception as e:
            return AgentResult(self.name, AgentStatus.ERROR, error=str(e))

    def _generate_explanation_llm(self, user_a, user_b, score_obj, detail_level):
        """
        Generate explanation using Gemini LLM via LangChain chain.
        Falls back to rule-based if LLM unavailable.

        Returns:
            Dict with 'summary', 'details', 'full', 'score_breakdown'
        """
        lifestyle = float(score_obj.lifestyle_score or 0)
        budget = float(score_obj.budget_score or 0)
        habits = float(score_obj.habits_score or 0)
        schedule = float(score_obj.schedule_score or 0)
        age_match = float(score_obj.age_match_score or 0)
        overall = float(score_obj.overall_score)

        score_breakdown = {
            'overall_score': overall,
            'lifestyle_score': lifestyle,
            'schedule_score': schedule,
            'budget_score': budget,
            'habits_score': habits,
            'age_match_score': age_match
        }

        # Try LLM-powered explanation
        if self.explanation_chain:
            try:
                llm_response = self.explanation_chain.invoke({
                    'user_a_name': user_a.full_name,
                    'user_a_city': user_a.city or 'unknown',
                    'user_b_name': user_b.full_name,
                    'user_b_city': user_b.city or 'unknown',
                    'user_b_gender': user_b.gender or 'unspecified',
                    'overall_score': overall,
                    'lifestyle': lifestyle,
                    'schedule': schedule,
                    'budget': budget,
                    'habits': habits,
                    'age_match': age_match,
                    'detail_level': detail_level
                }, config={"callbacks": [self.callback_handler]})

                parsed = self._parse_llm_explanation(llm_response)
                if parsed:
                    parsed['score_breakdown'] = score_breakdown
                    parsed['llm_generated'] = True
                    return parsed
            except Exception as e:
                self.logger.warning(f"LLM explanation failed: {e}")

        # Fallback to rule-based explanation
        return self._fallback_explanation(user_a, user_b, score_obj, detail_level, score_breakdown)

    def _parse_llm_explanation(self, raw):
        """Parse LLM JSON response into explanation dict."""
        try:
            cleaned = raw.strip()
            if cleaned.startswith('```json'):
                cleaned = cleaned[7:]
            if cleaned.startswith('```'):
                cleaned = cleaned[3:]
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]
            result = json.loads(cleaned.strip())
            if 'summary' in result and 'full' in result:
                if not isinstance(result.get('details'), list):
                    result['details'] = [result.get('details', '')]
                return result
        except (json.JSONDecodeError, ValueError):
            pass
        return None

    def _fallback_explanation(self, user_a, user_b, score_obj, detail_level, score_breakdown):
        """Rule-based fallback explanation when LLM is unavailable."""
        strengths = []
        concerns = []

        lifestyle = float(score_obj.lifestyle_score or 0)
        budget = float(score_obj.budget_score or 0)
        habits = float(score_obj.habits_score or 0)
        schedule = float(score_obj.schedule_score or 0)
        age_match = float(score_obj.age_match_score or 0)
        overall = float(score_obj.overall_score)

        if overall >= 80:
            strengths.append("Excellent overall compatibility")
        if lifestyle > 75:
            strengths.append("Compatible lifestyle preferences")
        elif lifestyle > 60:
            strengths.append("Similar lifestyle")
        if budget > 80:
            strengths.append("Well-aligned budget ranges")
        elif budget > 60:
            strengths.append("Overlapping budget expectations")
        if habits > 75:
            strengths.append("Compatible habits (smoking/pets/cleanliness)")
        if schedule > 75:
            strengths.append("Compatible daily schedules")
        if age_match > 80:
            strengths.append("Good age compatibility")

        if schedule < 50:
            concerns.append("Different daily schedules may cause friction")
        if lifestyle < 50:
            concerns.append("Lifestyle preferences differ significantly")
        if budget < 50:
            concerns.append("Budget expectations may not align")
        if habits < 50:
            concerns.append("Differing habits around smoking/pets/cleanliness")

        if strengths:
            summary = f"{user_b.full_name} ({user_b.gender}): {', '.join(strengths)}"
        else:
            summary = f"{user_b.full_name}: Good overall match"

        details = strengths + ["Warning: " + c for c in concerns]

        if detail_level == 'brief':
            full = summary
        elif detail_level == 'standard':
            full = f"{summary}. Score: {overall}/100."
            if concerns:
                full += f" Note: {', '.join(concerns)}"
        else:
            full = f"{user_a.full_name}, meet {user_b.full_name} from {user_b.city or 'your area'}. "
            full += f"You're {overall:.0f}% compatible. "
            if strengths:
                full += "Strengths: " + "; ".join(strengths) + ". "
            if concerns:
                full += "Areas to discuss: " + "; ".join(concerns) + "."

        return {
            'summary': summary,
            'details': list(details),
            'full': full,
            'score_breakdown': score_breakdown,
            'llm_generated': False
        }

    def _get_match_strength(self, score):
        """Get human-readable match strength label."""
        if score >= 90:
            return "Perfect Match"
        elif score >= 80:
            return "Excellent Match"
        elif score >= 70:
            return "Very Good Match"
        elif score >= 60:
            return "Good Match"
        elif score >= 50:
            return "Decent Match"
        else:
            return "Okay Match"
