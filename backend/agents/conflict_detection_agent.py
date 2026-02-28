"""
Conflict Detection Agent (LangChain-Powered)
Identifies deal-breaker incompatibilities between users or users and rooms.

Technology:
- LangChain Tools: check_smoking, check_pets, check_budget, check_cleanliness
- Google Gemini LLM: Conflict severity assessment and resolution advice
- Rule-based fallback when LLM unavailable

Status: AGENT 5 of 6
"""

from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from backend.agents.base_agent import BaseAgent, AgentResult, AgentStatus
from backend.database import db
from backend.models import User, UserPreference, Room, ConflictLog
from datetime import datetime
import json


class ConflictDetectionAgent(BaseAgent):
    """
    LangChain-powered conflict detection agent.
    Identifies hard/soft conflicts and uses Gemini for resolution advice.
    """

    def __init__(self):
        super().__init__(
            'Conflict Detection Agent', '2.0',
            system_prompt=(
                "You are the Conflict Detection Agent in an AI roommate matching system. "
                "You analyze potential conflicts between roommate candidates and provide "
                "severity assessments and practical resolution advice. "
                "Hard conflicts are deal-breakers, soft conflicts are discussion points."
            )
        )
        self.conflict_chain = self._build_conflict_chain()

    def _build_conflict_chain(self):
        """Build LangChain chain for conflict analysis."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human",
             "Analyze these conflicts between two potential roommates:\n"
             "User A: {user_a_info}\n"
             "User B: {user_b_info}\n"
             "Hard Conflicts (deal-breakers): {hard_conflicts}\n"
             "Soft Conflicts (warnings): {soft_conflicts}\n\n"
             "Provide a brief JSON response with keys: "
             "'severity_assessment' (1-2 sentence overall assessment), "
             "'can_resolve' (boolean - can these conflicts be worked out?), "
             "'resolution_tips' (list of 2-3 practical tips), "
             "'risk_level' ('low', 'medium', 'high', 'critical'), "
             "'recommendation' ('proceed', 'proceed with caution', or 'avoid')."
             )
        ])
        return self.create_chain(prompt)

    def _register_tools(self):
        """Register LangChain tools for conflict detection."""

        @tool
        def check_smoking_conflict(smoking_ok_a: bool, smoking_ok_b: bool,
                                    name_a: str, name_b: str) -> str:
            """Check for smoking preference conflicts between two users."""
            if smoking_ok_a == smoking_ok_b:
                return json.dumps({'conflict': False, 'type': None})
            if not smoking_ok_a and smoking_ok_b:
                return json.dumps({
                    'conflict': True, 'type': 'soft', 'severity': 6,
                    'reason': f"{name_a} does not accept smoking, but {name_b} smokes"
                })
            return json.dumps({
                'conflict': True, 'type': 'soft', 'severity': 6,
                'reason': f"{name_b} does not accept smoking, but {name_a} smokes"
            })

        @tool
        def check_pet_conflict(pets_ok_a: bool, pets_ok_b: bool,
                                name_a: str, name_b: str) -> str:
            """Check for pet preference conflicts between two users."""
            if pets_ok_a == pets_ok_b:
                return json.dumps({'conflict': False, 'type': None})
            if not pets_ok_a and pets_ok_b:
                return json.dumps({
                    'conflict': True, 'type': 'hard', 'severity': 9,
                    'reason': f"{name_a} does not accept pets, but {name_b} has/wants pets"
                })
            return json.dumps({
                'conflict': True, 'type': 'hard', 'severity': 9,
                'reason': f"{name_b} does not accept pets, but {name_a} has/wants pets"
            })

        @tool
        def check_budget_conflict(a_min: float, a_max: float,
                                   b_min: float, b_max: float) -> str:
            """Check for budget range overlap conflict between two users."""
            if a_max < b_min or b_max < a_min:
                return json.dumps({
                    'conflict': True, 'type': 'hard', 'severity': 8,
                    'reason': f"Budget ranges do not overlap: ${a_min}-${a_max} vs ${b_min}-${b_max}"
                })
            return json.dumps({'conflict': False, 'type': None})

        @tool
        def check_cleanliness_conflict(clean_a: float, clean_b: float) -> str:
            """Check for cleanliness preference gap between two users."""
            gap = abs(clean_a - clean_b)
            if gap > 5:
                return json.dumps({
                    'conflict': True, 'type': 'soft', 'severity': 5,
                    'reason': f"Cleanliness preference gap: {clean_a}/10 vs {clean_b}/10"
                })
            return json.dumps({'conflict': False, 'type': None})

        return [check_smoking_conflict, check_pet_conflict, check_budget_conflict, check_cleanliness_conflict]

    def execute(self, **inputs):
        """
        Detect conflicts between entities.

        Inputs:
        - user_a_id, user_b_id: User-user conflict check
        - user_id, room_id: User-room conflict check

        Returns:
            AgentResult with conflict report and AI analysis
        """
        try:
            user_a_id = inputs.get('user_a_id')
            user_b_id = inputs.get('user_b_id')
            user_id = inputs.get('user_id')
            room_id = inputs.get('room_id')

            if user_a_id and user_b_id:
                return self._check_user_user_conflicts(user_a_id, user_b_id)
            elif user_id and room_id:
                return self._check_user_room_conflicts(user_id, room_id)
            else:
                return AgentResult(
                    self.name, AgentStatus.ERROR,
                    error="Must provide either (user_a_id, user_b_id) or (user_id, room_id)"
                )
        except Exception as e:
            return AgentResult(self.name, AgentStatus.ERROR, error=str(e))

    def _check_user_user_conflicts(self, user_a_id, user_b_id):
        try:
            user_a = User.query.get(user_a_id)
            user_b = User.query.get(user_b_id)
            if not user_a or not user_b:
                return AgentResult(self.name, AgentStatus.ERROR, error="One or both users not found")

            prefs_a = UserPreference.query.filter_by(user_id=user_a_id).first()
            prefs_b = UserPreference.query.filter_by(user_id=user_b_id).first()

            existing_conflict = ConflictLog.query.filter(
                ((ConflictLog.user_a_id == user_a_id) & (ConflictLog.user_b_id == user_b_id)) |
                ((ConflictLog.user_a_id == user_b_id) & (ConflictLog.user_b_id == user_a_id))
            ).first()

            hard_conflicts = []
            soft_conflicts = []

            if prefs_a and prefs_b:
                # ── Tool: Smoking check (Soft – lifestyle difference, not a dealbreaker) ──
                if prefs_a.smoking_ok == False and prefs_b.smoking_ok == True:
                    soft_conflicts.append({
                        'type': 'smoking_mismatch', 'severity': 6,
                        'reason': f"{user_a.full_name} does not accept smoking, but {user_b.full_name} smokes"
                    })
                elif prefs_a.smoking_ok == True and prefs_b.smoking_ok == False:
                    soft_conflicts.append({
                        'type': 'smoking_mismatch', 'severity': 6,
                        'reason': f"{user_b.full_name} does not accept smoking, but {user_a.full_name} smokes"
                    })

                # ── Tool: Pets check ──
                if prefs_a.pets_ok == False and prefs_b.pets_ok == True:
                    hard_conflicts.append({
                        'type': 'pets_mismatch', 'severity': 9,
                        'reason': f"{user_a.full_name} does not accept pets, but {user_b.full_name} has/wants pets"
                    })
                elif prefs_a.pets_ok == True and prefs_b.pets_ok == False:
                    hard_conflicts.append({
                        'type': 'pets_mismatch', 'severity': 9,
                        'reason': f"{user_b.full_name} does not accept pets, but {user_a.full_name} has/wants pets"
                    })

                # ── Tool: Budget check ──
                try:
                    a_min = float(prefs_a.budget_min or 300)
                    a_max = float(prefs_a.budget_max or 1500)
                    b_min = float(prefs_b.budget_min or 300)
                    b_max = float(prefs_b.budget_max or 1500)
                    if a_max < b_min or b_max < a_min:
                        hard_conflicts.append({
                            'type': 'budget_mismatch', 'severity': 8,
                            'reason': f"Budget ranges do not overlap: ${a_min}-${a_max} vs ${b_min}-${b_max}"
                        })
                except:
                    pass

                # ── Tool: Cleanliness check ──
                try:
                    clean_map = {'Very Clean': 10, 'Clean': 7, 'Average': 5, 'Relaxed': 2}
                    clean_a = clean_map.get(prefs_a.cleanliness_level, 5)
                    clean_b = clean_map.get(prefs_b.cleanliness_level, 5)
                    gap = abs(clean_a - clean_b)
                    if gap >= 5:
                        soft_conflicts.append({
                            'type': 'cleanliness_mismatch', 'severity': 5,
                            'reason': f"Major cleanliness gap: {prefs_a.cleanliness_level or 'Unknown'} vs {prefs_b.cleanliness_level or 'Unknown'}"
                        })
                    elif gap >= 3:
                        soft_conflicts.append({
                            'type': 'cleanliness_gap', 'severity': 4,
                            'reason': f"Cleanliness preference difference: {prefs_a.cleanliness_level or 'Unknown'} vs {prefs_b.cleanliness_level or 'Unknown'}"
                        })
                except:
                    pass

                # ── Tool: Schedule check (Soft – different schedules can coexist) ──
                try:
                    if prefs_a.schedule and prefs_b.schedule:
                        schedule_conflicts = {
                            ('Night Shift', '9-5 Job'), ('9-5 Job', 'Night Shift')
                        }
                        if (prefs_a.schedule, prefs_b.schedule) in schedule_conflicts:
                            soft_conflicts.append({
                                'type': 'schedule_mismatch', 'severity': 5,
                                'reason': f"Opposing schedules: {prefs_a.schedule} vs {prefs_b.schedule}"
                            })
                        elif prefs_a.schedule != prefs_b.schedule:
                            soft_conflicts.append({
                                'type': 'schedule_difference', 'severity': 3,
                                'reason': f"Different schedules: {prefs_a.schedule} vs {prefs_b.schedule}"
                            })
                except:
                    pass

                # ── Tool: Noise tolerance check ──
                try:
                    noise_a = int(prefs_a.noise_tolerance or 5)
                    noise_b = int(prefs_b.noise_tolerance or 5)
                    noise_gap = abs(noise_a - noise_b)
                    if noise_gap >= 9:
                        hard_conflicts.append({
                            'type': 'noise_mismatch', 'severity': 8,
                            'reason': f"Extreme noise tolerance gap: {noise_a}/10 vs {noise_b}/10"
                        })
                    elif noise_gap >= 5:
                        soft_conflicts.append({
                            'type': 'noise_difference', 'severity': 4,
                            'reason': f"Noise tolerance difference: {noise_a}/10 vs {noise_b}/10"
                        })
                except:
                    pass

                # ── Tool: Gender preference check ──
                try:
                    if prefs_a.gender_preference and prefs_a.gender_preference != 'Any':
                        if user_b.gender and user_b.gender != prefs_a.gender_preference:
                            soft_conflicts.append({
                                'type': 'gender_pref_mismatch', 'severity': 6,
                                'reason': f"{user_a.full_name} prefers {prefs_a.gender_preference} roommate, but {user_b.full_name} is {user_b.gender}"
                            })
                    if prefs_b.gender_preference and prefs_b.gender_preference != 'Any':
                        if user_a.gender and user_a.gender != prefs_b.gender_preference:
                            soft_conflicts.append({
                                'type': 'gender_pref_mismatch', 'severity': 6,
                                'reason': f"{user_b.full_name} prefers {prefs_b.gender_preference} roommate, but {user_a.full_name} is {user_a.gender}"
                            })
                except:
                    pass

                # Age check
                try:
                    a_min_age = float(prefs_a.age_min or 18)
                    a_max_age = float(prefs_a.age_max or 65)
                    b_min_age = float(prefs_b.age_min or 18)
                    b_max_age = float(prefs_b.age_max or 65)
                    if a_max_age < b_min_age or b_max_age < a_min_age:
                        soft_conflicts.append({
                            'type': 'age_mismatch', 'severity': 3,
                            'reason': "Age preferences don't overlap"
                        })
                except:
                    pass

            has_hard = len(hard_conflicts) > 0

            # Log to database
            if hard_conflicts or soft_conflicts:
                # Delete old conflicts for this pair first
                ConflictLog.query.filter(
                    ((ConflictLog.user_a_id == user_a_id) & (ConflictLog.user_b_id == user_b_id)) |
                    ((ConflictLog.user_a_id == user_b_id) & (ConflictLog.user_b_id == user_a_id))
                ).delete()
                # Log each conflict separately for better tracking
                for c in hard_conflicts + soft_conflicts:
                    conflict = ConflictLog(
                        user_a_id=user_a_id, user_b_id=user_b_id,
                        conflict_type='Hard' if c in hard_conflicts else 'Soft',
                        severity=c['severity'],
                        description=c['reason']
                    )
                    db.session.add(conflict)
                db.session.commit()

            # ── LLM: Conflict analysis (Gemini) ──
            ai_analysis = None
            if (hard_conflicts or soft_conflicts) and self.conflict_chain:
                try:
                    llm_response = self.conflict_chain.invoke({
                        'user_a_info': f"{user_a.full_name} ({user_a.city or 'unknown'})",
                        'user_b_info': f"{user_b.full_name} ({user_b.city or 'unknown'})",
                        'hard_conflicts': json.dumps(hard_conflicts) if hard_conflicts else 'None',
                        'soft_conflicts': json.dumps(soft_conflicts) if soft_conflicts else 'None'
                    }, config={"callbacks": [self.callback_handler]})
                    ai_analysis = self._parse_conflict_analysis(llm_response)
                except Exception as e:
                    self.logger.warning(f"LLM conflict analysis failed: {e}")

            if not ai_analysis:
                ai_analysis = self._fallback_conflict_analysis(hard_conflicts, soft_conflicts)

            # Log decision
            self.log_decision(
                entity_type='conflict',
                entity_id=existing_conflict.conflict_id if existing_conflict else user_a_id,
                action='detected_conflicts',
                details={
                    'user_a_id': user_a_id, 'user_b_id': user_b_id,
                    'hard_conflicts': len(hard_conflicts),
                    'soft_conflicts': len(soft_conflicts),
                    'ai_analysis': ai_analysis
                }
            )

            return AgentResult(
                self.name, AgentStatus.SUCCESS,
                data={
                    'user_a_id': user_a_id, 'user_b_id': user_b_id,
                    'has_hard_conflicts': has_hard,
                    'has_soft_conflicts': len(soft_conflicts) > 0,
                    'hard_conflicts': hard_conflicts,
                    'soft_conflicts': soft_conflicts,
                    'total_conflicts': len(hard_conflicts) + len(soft_conflicts),
                    'ai_analysis': ai_analysis,
                    'checked_at': datetime.utcnow().isoformat()
                },
                metadata={
                    'conflict_blocking': has_hard,
                    'llm_used': ai_analysis.get('llm_generated', False),
                    'tools_used': [t.name for t in self.tools]
                }
            )

        except Exception as e:
            return AgentResult(self.name, AgentStatus.ERROR, error=str(e))

    def _check_user_room_conflicts(self, user_id, room_id):
        try:
            user = User.query.get(user_id)
            room = Room.query.get(room_id)
            if not user or not room:
                return AgentResult(self.name, AgentStatus.ERROR, error="User or room not found")

            prefs = UserPreference.query.filter_by(user_id=user_id).first()
            hard_conflicts = []
            soft_conflicts = []

            if prefs:
                if not prefs.smoking_ok and room.smoking_allowed:
                    hard_conflicts.append({
                        'type': 'smoking_not_allowed', 'severity': 10,
                        'reason': "User does not accept smoking, but room allows it"
                    })
                if not prefs.pets_ok and room.pets_allowed:
                    hard_conflicts.append({
                        'type': 'pets_not_allowed', 'severity': 9,
                        'reason': "User does not accept pets, but room allows them"
                    })
                try:
                    rent = float(room.rent_price)
                    budget_min = float(prefs.budget_min or 300)
                    budget_max = float(prefs.budget_max or 1500)
                    if rent < budget_min or rent > budget_max:
                        hard_conflicts.append({
                            'type': 'budget_out_of_range', 'severity': 8,
                            'reason': f"Rent ${rent} is outside budget range ${budget_min}-${budget_max}"
                        })
                except:
                    pass

            has_hard = len(hard_conflicts) > 0
            return AgentResult(
                self.name, AgentStatus.SUCCESS,
                data={
                    'user_id': user_id, 'room_id': room_id,
                    'has_hard_conflicts': has_hard,
                    'hard_conflicts': hard_conflicts,
                    'soft_conflicts': soft_conflicts,
                    'suitable': not has_hard,
                    'checked_at': datetime.utcnow().isoformat()
                },
                metadata={'blocking': has_hard, 'tools_used': [t.name for t in self.tools]}
            )
        except Exception as e:
            return AgentResult(self.name, AgentStatus.ERROR, error=str(e))

    def _parse_conflict_analysis(self, raw):
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
                'severity_assessment': raw[:200] if raw else 'Analysis unavailable',
                'llm_generated': True
            }

    def _fallback_conflict_analysis(self, hard, soft):
        if hard:
            return {
                'severity_assessment': f"Found {len(hard)} deal-breaker conflict(s). These are fundamental incompatibilities.",
                'can_resolve': False,
                'resolution_tips': ['Consider other matches', 'These differences are non-negotiable'],
                'risk_level': 'critical' if len(hard) > 1 else 'high',
                'recommendation': 'avoid',
                'llm_generated': False
            }
        elif soft:
            return {
                'severity_assessment': f"Found {len(soft)} minor concern(s). These can be discussed.",
                'can_resolve': True,
                'resolution_tips': ['Discuss expectations early', 'Set ground rules together'],
                'risk_level': 'medium' if len(soft) > 1 else 'low',
                'recommendation': 'proceed with caution',
                'llm_generated': False
            }
        return {
            'severity_assessment': 'No conflicts detected.',
            'can_resolve': True, 'resolution_tips': [],
            'risk_level': 'low', 'recommendation': 'proceed',
            'llm_generated': False
        }
