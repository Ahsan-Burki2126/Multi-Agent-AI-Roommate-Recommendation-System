"""
Reset stale data and re-run the full pipeline for User 6 (John Smith).
Clears old conflicts, scores, and recommendations, then triggers the orchestrator.
"""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['FLASK_ENV'] = 'development'

from backend.app import create_app
from backend.database import db
from backend.models import CompatibilityScore, ConflictLog, Recommendation, PreferenceVector

app = create_app()

with app.app_context():
    # ── Step 1: Clear stale data ──
    print("=" * 60)
    print("STEP 1: Clearing stale data...")
    
    n_conflicts = ConflictLog.query.delete()
    n_scores = CompatibilityScore.query.delete()
    n_recs = Recommendation.query.delete()
    n_vectors = PreferenceVector.query.delete()
    db.session.commit()
    
    print(f"  Deleted: {n_conflicts} conflicts, {n_scores} scores, {n_recs} recommendations, {n_vectors} vectors")
    
    # ── Step 2: Re-run pipeline for User 6 ──
    print("\n" + "=" * 60)
    print("STEP 2: Running full pipeline for User 6 (John Smith)...")
    
    from backend.agents.agent_orchestrator import AgentOrchestrator
    
    orchestrator = AgentOrchestrator()
    start = time.time()
    result = orchestrator.find_matches_for_user(user_id=6)
    elapsed = time.time() - start
    
    print(f"\n  Pipeline completed in {elapsed:.1f}s")
    print(f"  Success: {result.get('success')}")
    print(f"  Recommendations: {len(result.get('recommendations', []))}")
    
    if result.get('metrics'):
        m = result['metrics']
        print(f"  Scores computed: {m.get('scores_computed', 'N/A')}")
        print(f"  Conflicts detected: {m.get('conflicts_detected', 'N/A')}")
    
    # Print recommendations
    recs = result.get('recommendations', [])
    print(f"\n  Top Recommendations for John Smith:")
    for i, rec in enumerate(recs[:10], 1):
        name = rec.get('user_name', 'Unknown')
        score = rec.get('score', 0)
        comps = rec.get('components', {})
        print(f"    {i}. {name} (score={score})")
        print(f"       lifestyle={comps.get('lifestyle', 0)} schedule={comps.get('schedule', 0)} "
              f"budget={comps.get('budget', 0)} habits={comps.get('habits', 0)} "
              f"age={comps.get('age_match', 0)}")
    
    # ── Step 3: Check DB state ──
    print("\n" + "=" * 60)
    print("STEP 3: Database state after pipeline:")
    
    total_scores = CompatibilityScore.query.count()
    total_conflicts = ConflictLog.query.count()
    hard_conflicts = ConflictLog.query.filter_by(conflict_type='Hard').count()
    soft_conflicts = ConflictLog.query.filter_by(conflict_type='Soft').count()
    total_recs = Recommendation.query.count()
    total_vectors = PreferenceVector.query.count()
    
    print(f"  Vectors: {total_vectors}")
    print(f"  Scores: {total_scores}")
    print(f"  Conflicts: {total_conflicts} (hard={hard_conflicts}, soft={soft_conflicts})")
    print(f"  Recommendations: {total_recs}")
    
    # User 6 specific
    u6_hard = ConflictLog.query.filter(
        ((ConflictLog.user_a_id == 6) | (ConflictLog.user_b_id == 6)),
        ConflictLog.conflict_type == 'Hard'
    ).count()
    u6_soft = ConflictLog.query.filter(
        ((ConflictLog.user_a_id == 6) | (ConflictLog.user_b_id == 6)),
        ConflictLog.conflict_type == 'Soft'
    ).count()
    print(f"\n  User 6 conflicts: hard={u6_hard}, soft={u6_soft}")
    
    # ── Step 4: Verify recommendation explanations ──
    print("\n" + "=" * 60)
    print("STEP 4: Checking recommendation explanations in DB:")
    
    db_recs = Recommendation.query.filter_by(requester_id=6).order_by(Recommendation.match_score.desc()).limit(5).all()
    for r in db_recs:
        try:
            exp = json.loads(r.explanation) if r.explanation else {}
        except:
            exp = {}
        breakdown = exp.get('score_breakdown', {})
        print(f"  Match {r.match_id}: score={r.match_score}")
        print(f"    breakdown: {breakdown}")
    
    print("\n>> Done!")
