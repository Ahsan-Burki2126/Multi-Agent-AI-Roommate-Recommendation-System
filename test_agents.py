"""Quick test to verify agent pipeline works correctly."""
import os, sys, json
import numpy as np
from datetime import datetime

# Ensure proper imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app import create_app
app = create_app()

with app.app_context():
    from backend.database import db
    from backend.models import User, UserPreference, PreferenceVector, CompatibilityScore, ConflictLog
    
    # Step 1: Verify test users exist
    users = User.query.filter(User.user_id >= 6).all()
    print(f"=== Test Users: {len(users)} ===")
    
    users_with_prefs = []
    for u in users[:5]:
        prefs = UserPreference.query.filter_by(user_id=u.user_id).first()
        has_prefs = "YES" if prefs else "NO"
        print(f"  {u.user_id}: {u.full_name} ({u.email}) city={u.city} prefs={has_prefs}")
        if prefs:
            users_with_prefs.append(u)
    
    if len(users_with_prefs) < 2:
        print("ERROR: Need at least 2 users with preferences!")
        sys.exit(1)
    
    # Step 2: Vectorize all users with preferences (fast, no LLM)
    print(f"\n=== Vectorizing Users ===")
    all_users_with_prefs = []
    for u in users:
        prefs = UserPreference.query.filter_by(user_id=u.user_id).first()
        if not prefs:
            continue
        all_users_with_prefs.append(u)
        
        # Check if vector exists
        existing = PreferenceVector.query.filter_by(user_id=u.user_id).first()
        if existing:
            continue
        
        # Create vector (same logic as preference_analysis_agent)
        vector_data = [
            float(prefs.budget_min or 500) / 2000.0,
            float(prefs.budget_max or 1500) / 3000.0,
            (prefs.age_min or 20) / 60.0,
            (prefs.noise_tolerance or 5) / 10.0,
            1.0 if prefs.smoking_ok else 0.0,
            1.0 if prefs.pets_ok else 0.0,
        ]
        vector_norm = float(np.linalg.norm(vector_data))
        
        vec = PreferenceVector(
            user_id=u.user_id,
            vector_data=vector_data,
            vector_norm=vector_norm,
            preference_weights={
                'cosine_similarity': 0.3,
                'lifestyle_match': 0.2,
                'schedule_compatibility': 0.2,
                'budget_alignment': 0.15,
                'habits_alignment': 0.15
            },
            computed_at=datetime.utcnow()
        )
        db.session.add(vec)
    
    db.session.commit()
    vec_count = PreferenceVector.query.count()
    print(f"  Vectors created: {vec_count}")
    print(f"  Users with preferences: {len(all_users_with_prefs)}")
    
    # Step 3: Test Scoring Agent for a specific pair
    print(f"\n=== Testing Compatibility Scoring Agent ===")
    from backend.agents.compatibility_scoring_agent import CompatibilityScoringAgent
    scoring_agent = CompatibilityScoringAgent()
    
    # Pick two users with preferences
    user_a = all_users_with_prefs[0]
    user_b = all_users_with_prefs[1]
    print(f"  Scoring: {user_a.full_name} vs {user_b.full_name}")
    
    result = scoring_agent.execute(user_a_id=user_a.user_id, user_b_id=user_b.user_id, use_cache=False)
    print(f"  Status: {result.status.value}")
    if result.data:
        print(f"  Overall Score: {result.data.get('overall_score')}")
        print(f"  Lifestyle: {result.data.get('lifestyle_score')}")
        print(f"  Schedule: {result.data.get('schedule_score')}")
        print(f"  Budget: {result.data.get('budget_score')}")
        print(f"  Habits: {result.data.get('habits_score')}")
        print(f"  Age Match: {result.data.get('age_match_score')}")
    if result.error:
        print(f"  ERROR: {result.error}")
    
    # Step 4: Test Conflict Detection Agent
    print(f"\n=== Testing Conflict Detection Agent ===")
    from backend.agents.conflict_detection_agent import ConflictDetectionAgent
    conflict_agent = ConflictDetectionAgent()
    
    result = conflict_agent.execute(user_a_id=user_a.user_id, user_b_id=user_b.user_id)
    print(f"  Status: {result.status.value}")
    if result.data:
        print(f"  Conflicts found: {result.data.get('conflicts_found', 0)}")
        for c in result.data.get('conflicts', []):
            print(f"    - [{c.get('type')}] {c.get('description')} (severity={c.get('severity')})")
    if result.error:
        print(f"  ERROR: {result.error}")
    
    # Step 5: Test with a known conflicting pair
    # Find a user with Night Shift and a user with 9-5 Job
    print(f"\n=== Finding Conflicting Pair ===")
    night_user = None
    day_user = None
    for u in all_users_with_prefs:
        prefs = UserPreference.query.filter_by(user_id=u.user_id).first()
        if prefs and prefs.schedule == 'Night Shift' and not night_user:
            night_user = u
        elif prefs and prefs.schedule == '9-5 Job' and not day_user:
            day_user = u
    
    if night_user and day_user:
        print(f"  Night shift: {night_user.full_name}")
        print(f"  Day job: {day_user.full_name}")
        
        # Score them
        result = scoring_agent.execute(user_a_id=night_user.user_id, user_b_id=day_user.user_id, use_cache=False)
        if result.data:
            print(f"  Schedule Score: {result.data.get('schedule_score')} (should be low ~30)")
            print(f"  Overall: {result.data.get('overall_score')}")
        
        # Detect conflicts
        result = conflict_agent.execute(user_a_id=night_user.user_id, user_b_id=day_user.user_id)
        if result.data:
            print(f"  Conflicts: {result.data.get('conflicts_found', 0)}")
            for c in result.data.get('conflicts', []):
                print(f"    - [{c.get('type')}] {c.get('description')}")
    else:
        print("  Could not find conflicting pair")
    
    # Step 6: Score summary
    print(f"\n=== DB Summary ===")
    print(f"  Total scores: {CompatibilityScore.query.count()}")
    print(f"  Total conflicts: {ConflictLog.query.count()}")
    print(f"  Total vectors: {PreferenceVector.query.count()}")
    
    print("\n=== DONE ===")
