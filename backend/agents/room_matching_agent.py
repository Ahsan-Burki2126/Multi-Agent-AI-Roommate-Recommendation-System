"""
Room Matching Agent (LangChain-Powered)
Filters and matches available rooms with user preferences.

Technology:
- LangChain Tools: filter_rooms_by_criteria, score_room
- Google Gemini LLM: Room match explanation and recommendation
- Rule-based fallback when LLM unavailable

Status: AGENT 4 of 6
"""

from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from backend.agents.base_agent import BaseAgent, AgentResult, AgentStatus
from backend.database import db
from backend.models import User, UserPreference, Room
from datetime import datetime
from decimal import Decimal
import json


class RoomMatchingAgent(BaseAgent):
    """
    LangChain-powered room matching agent.
    Filters and scores rooms with Gemini for recommendations.
    """

    def __init__(self):
        super().__init__(
            'Room Matching Agent', '2.0',
            system_prompt=(
                "You are the Room Matching Agent in an AI roommate matching system. "
                "You help users find the best available rooms based on their preferences. "
                "You evaluate rooms on budget fit, location, amenities, and user requirements."
            )
        )
        self.room_chain = self._build_room_chain()

    def _build_room_chain(self):
        """Build LangChain chain for room match explanation."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human",
             "Summarize room search results for this user:\n"
             "User Preferences: {user_prefs}\n"
             "Rooms Found: {room_count}\n"
             "Top Room: {top_room}\n"
             "Filters Applied: {filters}\n\n"
             "Provide a brief JSON response with keys: "
             "'summary' (2-sentence summary of results), "
             "'top_recommendation' (why the top room is a good fit), "
             "'search_quality' ('excellent', 'good', 'limited', or 'poor'), "
             "'suggestions' (list of tips for finding better matches)."
             )
        ])
        return self.create_chain(prompt)

    def _register_tools(self):
        """Register LangChain tools for room matching."""

        @tool
        def filter_rooms_by_budget(budget_min: float, budget_max: float) -> str:
            """Filter available rooms that fall within the user's budget range."""
            rooms = Room.query.filter(
                Room.is_available == True,
                Room.rent_price >= budget_min,
                Room.rent_price <= budget_max
            ).all()
            return json.dumps({
                'count': len(rooms),
                'room_ids': [r.room_id for r in rooms]
            })

        @tool
        def score_room_for_user(room_id: int, budget_mid: float,
                                 preferred_location: str) -> str:
            """Score a specific room (0-100) based on budget alignment and location match."""
            room = Room.query.get(room_id)
            if not room:
                return json.dumps({'error': 'Room not found'})
            score = 0
            try:
                rent = float(room.rent_price)
                budget_diff = abs(rent - budget_mid)
                score += max(0, 40 - int(budget_diff / 50) * 5)
            except:
                score += 20
            if preferred_location and room.location:
                if preferred_location.lower() in room.location.lower():
                    score += 30
                else:
                    score += 10
            else:
                score += 15
            return json.dumps({'room_id': room_id, 'score': min(100, score)})

        return [filter_rooms_by_budget, score_room_for_user]

    def execute(self, **inputs):
        """
        Find suitable rooms for a user.

        Inputs:
        - user_id (int): User looking for rooms
        - limit (int, optional): Max rooms to return

        Returns:
            AgentResult with ranked rooms and AI summary
        """
        try:
            user_id = inputs.get('user_id')
            limit = int(inputs.get('limit', 20))
            include_unsuitable = inputs.get('include_unsuitable', False)

            is_valid, missing = self.validate_inputs(['user_id'], inputs)
            if not is_valid:
                return AgentResult(self.name, AgentStatus.ERROR, error=f"Missing: {missing}")

            user = User.query.get(user_id)
            if not user:
                return AgentResult(self.name, AgentStatus.ERROR, error=f"User {user_id} not found")

            prefs = UserPreference.query.filter_by(user_id=user_id).first()
            if not prefs:
                return AgentResult(
                    self.name, AgentStatus.PARTIAL,
                    data={'rooms': [], 'message': 'User has no preferences set'},
                    metadata={'filters_applied': []}
                )

            # ── Tool: Build query with filters ──
            query = Room.query.filter_by(is_available=True)
            filters_applied = []

            if prefs.budget_min or prefs.budget_max:
                budget_min = float(prefs.budget_min) if prefs.budget_min else 0
                budget_max = float(prefs.budget_max) if prefs.budget_max else 10000
                query = query.filter(Room.rent_price >= budget_min, Room.rent_price <= budget_max)
                filters_applied.append(f"budget: ${budget_min}-${budget_max}")

            if prefs.preferred_location:
                location = prefs.preferred_location.strip().lower()
                query = query.filter(Room.location.ilike(f'%{location}%'))
                filters_applied.append(f"location: {location}")

            if not prefs.smoking_ok:
                query = query.filter_by(smoking_allowed=False)
                filters_applied.append("smoking: not allowed")

            if not prefs.pets_ok:
                query = query.filter_by(pets_allowed=False)
                filters_applied.append("pets: not allowed")

            rooms = query.all()

            # ── Tool: Score and rank rooms ──
            room_scores = []
            for room in rooms:
                score = self._compute_room_score(room, prefs)
                room_owner = User.query.get(room.owner_id)
                room_scores.append({'score': score, 'room': room, 'owner': room_owner})

            room_scores.sort(key=lambda x: x['score'], reverse=True)
            room_scores = room_scores[:limit]

            result = [
                {
                    'room_id': item['room'].room_id,
                    'title': item['room'].title,
                    'location': item['room'].location,
                    'rent_price': float(item['room'].rent_price),
                    'room_type': item['room'].room_type,
                    'bed_size': item['room'].bed_size,
                    'furnishing': item['room'].furnishing_type,
                    'pets_allowed': item['room'].pets_allowed,
                    'smoking_allowed': item['room'].smoking_allowed,
                    'amenities': item['room'].amenities,
                    'description': item['room'].description,
                    'match_score': item['score'],
                    'owner': {
                        'user_id': item['owner'].user_id,
                        'name': item['owner'].full_name,
                        'city': item['owner'].city
                    } if item['owner'] else None,
                    'posted_at': item['room'].created_at.isoformat() if item['room'].created_at else None
                }
                for item in room_scores
            ]

            # ── LLM: Room search summary (Gemini) ──
            ai_summary = None
            if result and self.room_chain:
                try:
                    prefs_summary = {
                        'budget': f"${prefs.budget_min or 0}-${prefs.budget_max or 'any'}",
                        'location': prefs.preferred_location or 'any',
                        'smoking': 'no' if not prefs.smoking_ok else 'ok',
                        'pets': 'yes' if prefs.pets_ok else 'no'
                    }
                    llm_response = self.room_chain.invoke({
                        'user_prefs': json.dumps(prefs_summary),
                        'room_count': len(result),
                        'top_room': json.dumps(result[0]) if result else 'None',
                        'filters': ', '.join(filters_applied) or 'None'
                    }, config={"callbacks": [self.callback_handler]})
                    ai_summary = self._parse_room_summary(llm_response)
                except Exception as e:
                    self.logger.warning(f"LLM room summary failed: {e}")

            if not ai_summary:
                ai_summary = {
                    'summary': f"Found {len(result)} rooms matching your criteria.",
                    'search_quality': 'good' if len(result) >= 3 else 'limited',
                    'llm_generated': False
                }

            # Log decision
            self.log_decision(
                entity_type='user', entity_id=user_id,
                action='found_matching_rooms',
                details={
                    'rooms_found': len(result),
                    'filters_applied': filters_applied,
                    'ai_summary': ai_summary
                }
            )

            return AgentResult(
                self.name, AgentStatus.SUCCESS,
                data={
                    'user_id': user_id, 'rooms': result,
                    'count': len(result), 'filters_applied': filters_applied,
                    'ai_summary': ai_summary
                },
                metadata={
                    'total_available': len(rooms), 'returned': len(result),
                    'limit': limit,
                    'llm_used': ai_summary.get('llm_generated', False),
                    'tools_used': [t.name for t in self.tools]
                }
            )

        except Exception as e:
            return AgentResult(self.name, AgentStatus.ERROR, error=str(e))

    def _parse_room_summary(self, raw):
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
            return {'summary': raw[:200] if raw else 'Summary unavailable', 'llm_generated': True}

    def _compute_room_score(self, room, user_prefs):
        score = 0
        try:
            budget_min = float(user_prefs.budget_min or 300)
            budget_max = float(user_prefs.budget_max or 1500)
            budget_mid = (budget_min + budget_max) / 2
            rent = float(room.rent_price)
            budget_diff = abs(rent - budget_mid)
            budget_range = max(budget_max - budget_min, 1)
            if budget_diff <= budget_range / 4:
                score += 40
            else:
                score += max(0, 40 - int((budget_diff / budget_range) * 40))
        except:
            score += 20
        try:
            if user_prefs.preferred_location:
                pref_loc = user_prefs.preferred_location.lower()
                room_loc = room.location.lower()
                if pref_loc in room_loc or room_loc in pref_loc:
                    score += 30
                elif pref_loc.split()[0] in room_loc:
                    score += 20
                else:
                    score += 10
            else:
                score += 15
        except:
            score += 15
        try:
            amenity_count = 0
            desired = ['wifi', 'ac', 'kitchen', 'parking']
            if room.amenities:
                amenities = room.amenities.lower()
                amenity_count = sum(1 for a in desired if a in amenities)
            score += min(20, amenity_count * 5)
        except:
            score += 10
        try:
            if room.bed_size in ['queen', 'double']:
                score += 5
            if room.furnishing_type == 'furnished':
                score += 5
        except:
            pass
        return int(min(100, score))
