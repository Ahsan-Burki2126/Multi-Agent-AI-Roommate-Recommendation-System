from backend.app import create_app
app = create_app()
with app.app_context():
    from backend.models import ConflictLog, CompatibilityScore
    hard = ConflictLog.query.filter(
        ((ConflictLog.user_a_id == 6) | (ConflictLog.user_b_id == 6)),
        ConflictLog.conflict_type == 'Hard'
    ).count()
    soft = ConflictLog.query.filter(
        ((ConflictLog.user_a_id == 6) | (ConflictLog.user_b_id == 6)),
        ConflictLog.conflict_type == 'Soft'
    ).count()
    all_hard = ConflictLog.query.filter_by(conflict_type='Hard').count()
    all_soft = ConflictLog.query.filter_by(conflict_type='Soft').count()
    print(f'User 6 conflicts: hard={hard}, soft={soft}')
    print(f'All conflicts: hard={all_hard}, soft={all_soft}')
    
    hards = ConflictLog.query.filter(
        ConflictLog.user_a_id == 6,
        ConflictLog.conflict_type == 'Hard'
    ).limit(5).all()
    for c in hards:
        print(f'  Hard: user 6 vs {c.user_b_id}: {c.description}')
