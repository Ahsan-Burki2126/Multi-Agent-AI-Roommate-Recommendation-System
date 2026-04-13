"""
User Profiling Agent (LangChain-Powered)
Validates user data and generates AI-powered profile analysis.

Technology:
- LangChain Tools: validate_email, check_profile_completeness
- Google Gemini LLM: Profile analysis and improvement suggestions
- Rule-based fallback when LLM unavailable

Status: AGENT 1 of 6
"""

from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from backend.agents.base_agent import BaseAgent, AgentResult, AgentStatus
from backend.database import db
from backend.models import User
import re
import json
from datetime import datetime


class UserProfilingAgent(BaseAgent):
    """
    LangChain-powered user profiling agent.
    Validates data, checks completeness, and uses Gemini for profile analysis.
    """

    def __init__(self):
        super().__init__(
            'User Profiling Agent', '2.0',
            system_prompt=(
                "You are the User Profiling Agent in an AI-powered roommate matching system. "
                "Your role is to analyze user profiles and provide insights about their "
                "compatibility readiness. Evaluate data quality and suggest improvements."
            )
        )

        # LangChain chain for profile analysis
        self.analysis_chain = self._build_analysis_chain()

    def _build_analysis_chain(self):
        """Build LangChain chain for AI profile analysis."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human",
             "Analyze this user profile for roommate matching readiness. "
             "Profile: {profile_json}\n"
             "Completeness Score: {completeness_score}%\n"
             "Missing Fields: {missing_fields}\n\n"
             "Provide a brief JSON response with keys: "
             "'analysis' (2-3 sentence summary), "
             "'strengths' (list of profile strengths), "
             "'improvements' (list of suggested improvements), "
             "'matching_readiness' (score 0-100)."
             )
        ])
        return self.create_chain(prompt)

    def _register_tools(self):
        """Register LangChain tools for user profiling."""

        @tool
        def validate_email_format(email: str) -> str:
            """Validate email address format using regex pattern matching."""
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            is_valid = re.match(pattern, email.strip().lower()) is not None
            return json.dumps({'email': email, 'valid': is_valid})

        @tool
        def check_email_duplicate(email: str) -> str:
            """Check if an email address is already registered in the system."""
            exists = User.query.filter_by(email=email.strip().lower()).first() is not None
            return json.dumps({'email': email, 'duplicate': exists})

        @tool
        def compute_profile_completeness(user_id: int) -> str:
            """Compute profile completeness score for a user (0-100)."""
            user = User.query.get(user_id)
            if not user:
                return json.dumps({'error': 'User not found'})
            profile = {
                'email': user.email, 'full_name': user.full_name,
                'gender': user.gender, 'city': user.city,
                'phone': user.phone, 'bio': user.bio
            }
            required = ['email', 'full_name', 'gender', 'city']
            optional = ['phone', 'bio']
            missing = [f for f in required if not profile.get(f)]
            req_count = len(required) - len(missing)
            opt_count = sum(1 for f in optional if profile.get(f))
            score = int((req_count / len(required)) * 70 + (opt_count / len(optional)) * 30)
            return json.dumps({
                'user_id': user_id, 'score': score,
                'complete': len(missing) == 0, 'missing': missing
            })

        return [validate_email_format, check_email_duplicate, compute_profile_completeness]

    def execute(self, **inputs):
        """
        Validate and analyze user profile using LangChain tools + Gemini LLM.

        Inputs:
        - user_id (int): ID of user to profile
        - user_data (dict, optional): Raw user data to validate

        Returns:
            AgentResult with profile data and AI analysis
        """
        try:
            user_id = inputs.get('user_id')
            user_data = inputs.get('user_data')

            if not user_id and not user_data:
                return AgentResult(
                    self.name, AgentStatus.ERROR,
                    error="Must provide user_id or user_data"
                )

            # ── Tool: Load & validate user ──
            if user_id:
                user = User.query.get(user_id)
                if not user:
                    return AgentResult(
                        self.name, AgentStatus.ERROR,
                        error=f"User {user_id} not found"
                    )
                profile = self._profile_from_user(user)
            else:
                errors = self._validate_user_data(user_data)
                if errors:
                    return AgentResult(
                        self.name, AgentStatus.PARTIAL,
                        data={'user_data': user_data, 'errors': errors},
                        metadata={'validation_failed': True}
                    )
                profile = self._normalize_user_data(user_data)

            # ── Tool: Check completeness ──
            completeness = self._check_completeness(profile)

            # ── LLM: AI Profile Analysis (via LangChain chain) ──
            ai_analysis = None
            if self.analysis_chain:
                try:
                    llm_response = self.analysis_chain.invoke({
                        'profile_json': json.dumps(profile, default=str),
                        'completeness_score': completeness['score'],
                        'missing_fields': ', '.join(completeness['missing']) or 'None'
                    }, config={"callbacks": [self.callback_handler]})

                    ai_analysis = self._parse_llm_analysis(llm_response)
                except Exception as e:
                    self.logger.warning(f"LLM analysis failed, using fallback: {e}")

            # Fallback analysis if LLM unavailable
            if not ai_analysis:
                ai_analysis = self._fallback_analysis(profile, completeness)

            # Log decision
            self.log_decision(
                entity_type='user',
                entity_id=user_id or 0,
                action='profile_analyzed',
                details={
                    'completeness_score': completeness['score'],
                    'ai_analysis': ai_analysis,
                    'llm_used': ai_analysis.get('llm_generated', False)
                }
            )

            return AgentResult(
                self.name, AgentStatus.SUCCESS,
                data={**profile, 'ai_analysis': ai_analysis},
                metadata={
                    'profile_complete': completeness['complete'],
                    'completion_score': completeness['score'],
                    'missing_fields': completeness['missing'],
                    'llm_used': ai_analysis.get('llm_generated', False),
                    'tools_used': [t.name for t in self.tools]
                }
            )

        except Exception as e:
            return AgentResult(self.name, AgentStatus.ERROR, error=str(e))

    def _parse_llm_analysis(self, raw_response):
        """Parse LLM response into structured analysis."""
        try:
            cleaned = raw_response.strip()
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
                'analysis': raw_response[:300] if raw_response else 'Analysis unavailable',
                'strengths': [],
                'improvements': [],
                'matching_readiness': 50,
                'llm_generated': True
            }

    def _fallback_analysis(self, profile, completeness):
        """Rule-based fallback when LLM is unavailable."""
        strengths = []
        improvements = []

        if profile.get('email'):
            strengths.append('Valid email registered')
        if profile.get('full_name'):
            strengths.append('Full name provided')
        if profile.get('city'):
            strengths.append(f'Location set: {profile["city"]}')
        if profile.get('bio'):
            strengths.append('Bio written')

        if not profile.get('phone'):
            improvements.append('Add phone number for better connectivity')
        if not profile.get('bio'):
            improvements.append('Write a bio to help matches understand you')
        if not profile.get('city'):
            improvements.append('Set your city for location-based matching')

        return {
            'analysis': f"Profile is {completeness['score']}% complete. "
                       f"{'Ready for matching.' if completeness['complete'] else 'Needs completion for better results.'}",
            'strengths': strengths,
            'improvements': improvements,
            'matching_readiness': completeness['score'],
            'llm_generated': False
        }

    # ── Existing validation logic ──

    def _validate_user_data(self, user_data):
        errors = []
        if not user_data:
            return ['No user data provided']

        if 'email' in user_data:
            email = str(user_data['email']).strip().lower()
            if not self._is_valid_email(email):
                errors.append('Invalid email format')
            if User.query.filter_by(email=email).first():
                errors.append('Email already registered')
        else:
            errors.append('Email is required')

        if 'full_name' not in user_data or not str(user_data['full_name']).strip():
            errors.append('Full name is required')
        elif len(str(user_data['full_name']).strip()) < 2:
            errors.append('Full name must be at least 2 characters')

        if 'phone' in user_data and user_data['phone']:
            if not self._is_valid_phone(user_data['phone']):
                errors.append('Invalid phone format')

        if 'gender' in user_data:
            if user_data['gender'] not in ['M', 'F', 'Other']:
                errors.append('Invalid gender. Must be M, F, or Other')

        return errors

    def _normalize_user_data(self, user_data):
        return {
            'email': str(user_data.get('email', '')).strip().lower(),
            'full_name': str(user_data.get('full_name', '')).strip(),
            'gender': user_data.get('gender', 'Other'),
            'city': str(user_data.get('city', '')).strip().title(),
            'phone': str(user_data.get('phone', '')).strip() if user_data.get('phone') else None,
            'bio': str(user_data.get('bio', '')).strip() if user_data.get('bio') else None,
            'age': int(user_data.get('age')) if user_data.get('age') else None,
        }

    def _profile_from_user(self, user):
        return {
            'user_id': user.user_id,
            'email': user.email,
            'full_name': user.full_name,
            'gender': user.gender,
            'city': user.city,
            'phone': user.phone,
            'bio': user.bio,
            'age': user.age,
            'is_active': user.is_active,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'updated_at': user.updated_at.isoformat() if user.updated_at else None,
        }

    def _check_completeness(self, profile):
        required_fields = ['email', 'full_name', 'gender', 'city']
        optional_fields = ['phone', 'bio', 'age']
        missing = [f for f in required_fields if not profile.get(f)]
        present = len(required_fields) - len(missing)
        opt_present = sum(1 for f in optional_fields if profile.get(f))
        score = int((present / len(required_fields)) * 70 +
                   (opt_present / len(optional_fields)) * 30)
        return {'complete': len(missing) == 0, 'score': score, 'missing': missing}

    def _is_valid_email(self, email):
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def _is_valid_phone(self, phone):
        phone_str = str(phone).replace('-', '').replace('(', '').replace(')', ' ').replace('+', '')
        return len(phone_str.replace(' ', '')) >= 10
