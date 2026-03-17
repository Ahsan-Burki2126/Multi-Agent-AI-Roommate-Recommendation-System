"""
End-to-end test suite for Multi-Agent AI Roommate Recommendation System
Tests the full pipeline: auth → preferences → vectorization → matching → recommendations

Run:
    cd roommate-matching-system
    python run_tests.py
"""

import sys
import os
import json
import logging

# Suppress verbose SQL logs
logging.getLogger('sqlalchemy').setLevel(logging.ERROR)
logging.getLogger('agent').setLevel(logging.WARNING)
logging.getLogger('langchain').setLevel(logging.WARNING)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from backend.config import DevelopmentConfig
DevelopmentConfig.SQLALCHEMY_ECHO = False

from backend.app import create_app

PASS = 0
FAIL = 0

def test(name, condition, detail=''):
    global PASS, FAIL
    status = 'PASS' if condition else 'FAIL'
    if condition:
        PASS += 1
        print(f'  [PASS] {name}')
    else:
        FAIL += 1
        print(f'  [FAIL] {name}' + (f': {detail}' if detail else ''))


def run_all_tests():
    global PASS, FAIL
    app = create_app('development')

    with app.app_context():
        from backend.models.user import User
        from backend.models.preference import UserPreference, PreferenceVector
        from backend.models.score import CompatibilityScore

        print("\n=== 1. Database Content Tests ===")
        total_users = User.query.count()
        survey_users = User.query.filter(User.email.like('%@survey.iub.edu.pk')).count()
        prefs_count = UserPreference.query.count()

        test("Survey users loaded (>300)", survey_users > 300, f"got {survey_users}")
        test("Preferences exist for survey users", prefs_count > 300, f"got {prefs_count}")
        test("Total users in DB >= survey users", total_users >= survey_users)

        print("\n=== 2. Agent: Preference Analysis (Vectorization) ===")
        from backend.agents.preference_analysis_agent import PreferenceAnalysisAgent

        sample_user = User.query.filter(User.email.like('%@survey.iub.edu.pk')).first()
        agent = PreferenceAnalysisAgent()
        result = agent.execute(user_id=sample_user.user_id, force_recompute=True)

        test("Preference analysis succeeds", result.is_success(), result.error)
        test("Vector data returned", result.data and 'vector' in result.data,
             str(result.data)[:100])
        if result.data and 'vector' in result.data:
            vec = result.data['vector']
            test("Vector has 6 dimensions", len(vec) == 6, f"got {len(vec)}")
            test("All vector values in [0,1]", all(0 <= v <= 1 for v in vec),
                 f"values: {vec}")

        # Check vector was saved to DB
        pv = PreferenceVector.query.filter_by(user_id=sample_user.user_id).first()
        test("Preference vector saved to DB", pv is not None)

        print("\n=== 3. Agent: Compatibility Scoring ===")
        from backend.agents.compatibility_scoring_agent import CompatibilityScoringAgent

        users = User.query.filter(User.email.like('%@survey.iub.edu.pk')).limit(5).all()

        # Vectorize user 2 first
        a2_result = agent.execute(user_id=users[1].user_id, force_recompute=True)

        scoring_agent = CompatibilityScoringAgent()
        score_result = scoring_agent.execute(
            user_a_id=users[0].user_id,
            user_b_id=users[1].user_id,
            use_cache=False
        )

        test("Compatibility scoring succeeds", score_result.is_success(), score_result.error)
        if score_result.is_success():
            score = score_result.data.get('overall_score', 0)
            test("Score in range [0, 100]", 0 <= score <= 100, f"got {score}")
            test("Score components present", 'component_scores' in score_result.data)

        print("\n=== 4. Agent: Conflict Detection ===")
        from backend.agents.conflict_detection_agent import ConflictDetectionAgent

        conflict_agent = ConflictDetectionAgent()
        conflict_result = conflict_agent.execute(
            user_a_id=users[0].user_id,
            user_b_id=users[1].user_id
        )

        test("Conflict detection succeeds", conflict_result.is_success(), conflict_result.error)
        if conflict_result.is_success():
            test("Conflict data returned", conflict_result.data is not None)
            test("Has hard_conflicts key", 'hard_conflicts' in (conflict_result.data or {}))
            test("Has soft_conflicts key", 'soft_conflicts' in (conflict_result.data or {}))

        print("\n=== 5. Agent: Recommendation Engine ===")
        from backend.agents.recommendation_engine_agent import RecommendationEngineAgent

        rec_agent = RecommendationEngineAgent()
        rec_result = rec_agent.execute(
            user_id=users[0].user_id,
            min_score=30,
            limit=10
        )

        test("Recommendation engine succeeds", rec_result.is_success(), rec_result.error)
        if rec_result.is_success():
            recs = rec_result.data.get('recommendations', [])
            test("At least 1 recommendation returned", len(recs) >= 1, f"got {len(recs)}")
            if recs:
                r = recs[0]
                test("Recommendation has user_id", 'user_id' in r)
                test("Recommendation has score", 'score' in r)
                test("Recommendation has explanation", 'explanation' in r)
                test("Explanation has summary", 'summary' in (r.get('explanation') or {}))

        print("\n=== 6. Full Orchestrator Pipeline ===")
        from backend.agents.agent_orchestrator import AgentOrchestrator

        orch = AgentOrchestrator()
        pipeline_result = orch.find_matches_for_user(users[0].user_id, min_score=30)

        test("Pipeline returns success", pipeline_result.get('success'),
             str(pipeline_result.get('error', '')))
        test("Pipeline has recommendations key", 'recommendations' in pipeline_result)
        test("Pipeline has metrics", 'metrics' in pipeline_result)

        if pipeline_result.get('recommendations'):
            recs = pipeline_result['recommendations']
            test("Pipeline found matches", len(recs) > 0, f"got {len(recs)}")
            metrics = pipeline_result.get('metrics', {})
            test("Scores were computed", (metrics.get('scores_computed') or 0) > 0)
            test("All 5 agents executed",
                 len(metrics.get('agents_executed', [])) == 5,
                 str(metrics.get('agents_executed', [])))

        print("\n=== 7. Flask API Endpoints ===")
        client = app.test_client()

        # Health
        resp = client.get('/health')
        test("GET /health returns 200", resp.status_code == 200)

        # Register new user
        resp = client.post('/auth/register', json={
            'email': 'test.fyp.runner@example.com',
            'password': 'Test@123456',
            'full_name': 'Test FYP Runner',
            'gender': 'M'
        })
        test("POST /auth/register", resp.status_code in (200, 201, 409),
             f"status={resp.status_code}")

        # Login
        resp = client.post('/auth/login', json={
            'email': 'abdul.ahad.0002@survey.iub.edu.pk',
            'password': 'Survey@2024'
        })
        test("POST /auth/login returns 200", resp.status_code == 200,
             f"status={resp.status_code}")

        if resp.status_code == 200:
            token = resp.get_json().get('access_token')
            headers = {'Authorization': f'Bearer {token}'}

            # Verify auth
            resp = client.get('/auth/verify', headers=headers)
            test("GET /auth/verify returns 200", resp.status_code == 200)

            # Get user preferences
            uid = resp.get_json().get('user_id') if resp.status_code == 200 else users[0].user_id
            resp = client.get(f'/preferences/user/{uid}', headers=headers)
            test("GET /preferences/user/<id> returns 200", resp.status_code == 200,
                 f"status={resp.status_code}")

            # Orchestrate matches
            resp = client.post('/orchestrate/matches',
                               json={'user_id': uid, 'min_score': 30},
                               headers=headers)
            test("POST /orchestrate/matches returns 200", resp.status_code == 200,
                 f"status={resp.status_code} body={resp.get_data(as_text=True)[:200]}")

            if resp.status_code == 200:
                data = resp.get_json()
                test("Orchestrate returns recommendations",
                     len(data.get('recommendations', [])) > 0,
                     f"count={len(data.get('recommendations', []))}")

        print(f"\n{'='*50}")
        print(f"Results: {PASS} passed, {FAIL} failed out of {PASS+FAIL} tests")
        if FAIL == 0:
            print("ALL TESTS PASSED - System is fully operational!")
        else:
            print(f"{FAIL} test(s) failed - check output above")
        print('='*50)

        return FAIL == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
