"""
Database Models Test Suite

Tests for all SQLAlchemy models to verify:
- Model creation and validation
- Relationship integrity  
- Password hashing
- Query methods
- Serialization

Usage:
    pytest backend/tests/test_models.py -v
"""

import pytest
from datetime import datetime, timedelta
import json
from backend.app import create_app, db
from backend.models import (
    User, UserPreference, PreferenceVector,
    Room, CompatibilityScore, ConflictLog,
    Recommendation, AuditLog
)


@pytest.fixture
def app():
    """Create test app with in-memory SQLite database"""
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


class TestUserModel:
    """Tests for User model"""
    
    def test_user_creation(self, app):
        """Test basic user creation"""
        with app.app_context():
            user = User(
                email='test@example.com',
                name='Test User',
                phone='+1234567890',
                gender='male'
            )
            user.set_password('SecurePass123!')
            db.session.add(user)
            db.session.commit()
            
            assert user.user_id is not None
            assert user.email == 'test@example.com'
            assert user.check_password('SecurePass123!')
            assert not user.check_password('WrongPassword')
    
    def test_user_validation(self, app):
        """Test user validation"""
        with app.app_context():
            # Missing required fields
            user = User()
            is_valid, errors = user.validate()
            assert not is_valid
            assert len(errors) > 0
            
            # Invalid email
            user = User(email='notanemail', name='Test')
            is_valid, errors = user.validate()
            assert not is_valid
    
    def test_password_hashing(self, app):
        """Test password is properly hashed"""
        with app.app_context():
            user = User(email='test@example.com', name='Test')
            user.set_password('MyPassword123!')
            
            # Password should not be stored in plaintext
            assert user.password_hash != 'MyPassword123!'
            assert user.password_hash is not None
    
    def test_user_to_dict(self, app):
        """Test user serialization"""
        with app.app_context():
            user = User(
                email='test@example.com',
                name='Test User',
                phone='+1234567890',
                gender='male'
            )
            db.session.add(user)
            db.session.commit()
            
            user_dict = user.to_dict()
            assert user_dict['email'] == 'test@example.com'
            assert user_dict['name'] == 'Test User'
            assert 'password_hash' not in user_dict
    
    def test_get_by_email(self, app):
        """Test finding user by email"""
        with app.app_context():
            user = User(email='test@example.com', name='Test')
            db.session.add(user)
            db.session.commit()
            
            found = User.get_by_email('test@example.com')
            assert found is not None
            assert found.email == 'test@example.com'
            
            not_found = User.get_by_email('other@example.com')
            assert not_found is None


class TestUserPreferenceModel:
    """Tests for UserPreference model"""
    
    def test_preference_creation(self, app):
        """Test creating user preferences"""
        with app.app_context():
            user = User(email='test@example.com', name='Test')
            db.session.add(user)
            db.session.commit()
            
            pref = UserPreference(
                user_id=user.user_id,
                budget_min=800,
                budget_max=1200,
                preferred_location='San Francisco',
                preferred_room_type='Shared'
            )
            db.session.add(pref)
            db.session.commit()
            
            assert pref.preference_id is not None
            assert pref.budget_min == 800
    
    def test_preference_validation(self, app):
        """Test preference validation"""
        with app.app_context():
            # Budget min > max should fail
            pref = UserPreference(
                user_id=1,
                budget_min=2000,
                budget_max=800
            )
            is_valid, errors = pref.validate()
            assert not is_valid
            assert 'budget' in str(errors).lower()


class TestPreferenceVectorModel:
    """Tests for PreferenceVector model"""
    
    def test_vector_creation(self, app):
        """Test creating preference vector"""
        with app.app_context():
            user = User(email='test@example.com', name='Test')
            db.session.add(user)
            db.session.commit()
            
            vector = PreferenceVector(
                user_id=user.user_id,
                vector_data=[0.5, 0.7, 0.8, 0.6, 0.9],
                vector_norm=1.42
            )
            db.session.add(vector)
            db.session.commit()
            
            assert vector.vector_id is not None
            assert vector.vector_data == [0.5, 0.7, 0.8, 0.6, 0.9]
    
    def test_vector_staleness(self, app):
        """Test vector staleness detection"""
        with app.app_context():
            user = User(email='test@example.com', name='Test')
            db.session.add(user)
            db.session.commit()
            
            # Fresh vector
            vector = PreferenceVector(
                user_id=user.user_id,
                vector_data=[0.5, 0.7],
                vector_norm=0.86,
                last_updated=datetime.now()
            )
            db.session.add(vector)
            db.session.commit()
            
            assert not vector.is_stale(days=30)
            
            # Old vector
            vector.last_updated = datetime.now() - timedelta(days=31)
            assert vector.is_stale(days=30)
    
    def test_vector_similarity(self, app):
        """Test cosine similarity computation"""
        with app.app_context():
            user1 = User(email='user1@example.com', name='User 1')
            user2 = User(email='user2@example.com', name='User 2')
            db.session.add_all([user1, user2])
            db.session.commit()
            
            # Similar vectors should have high similarity
            vec1 = PreferenceVector(
                user_id=user1.user_id,
                vector_data=[0.8, 0.7, 0.9],
                vector_norm=1.42
            )
            vec2 = PreferenceVector(
                user_id=user2.user_id,
                vector_data=[0.75, 0.72, 0.88],
                vector_norm=1.41
            )
            db.session.add_all([vec1, vec2])
            db.session.commit()
            
            similarity = vec1.get_similarity_with(vec2)
            assert 0.99 < similarity <= 1.0  # Should be very high


class TestRoomModel:
    """Tests for Room model"""
    
    def test_room_creation(self, app):
        """Test creating a room"""
        with app.app_context():
            owner = User(email='owner@example.com', name='Owner')
            db.session.add(owner)
            db.session.commit()
            
            room = Room(
                owner_id=owner.user_id,
                title='Nice Room',
                location='San Francisco',
                address='123 Main St',
                room_type='Shared',
                rent_price=1000
            )
            db.session.add(room)
            db.session.commit()
            
            assert room.room_id is not None
            assert room.title == 'Nice Room'
    
    def test_room_budget_matching(self, app):
        """Test budget matching"""
        with app.app_context():
            owner = User(email='owner@example.com', name='Owner')
            db.session.add(owner)
            db.session.commit()
            
            room = Room(
                owner_id=owner.user_id,
                title='Room',
                location='SF',
                room_type='Shared',
                rent_price=1000,
                address='123 St'
            )
            db.session.add(room)
            db.session.commit()
            
            # Within range
            assert room.matches_budget(900, 1200)
            # OutOfRange
            assert not room.matches_budget(1100, 1500)
    
    def test_room_location_matching(self, app):
        """Test location matching"""
        with app.app_context():
            owner = User(email='owner@example.com', name='Owner')
            db.session.add(owner)
            db.session.commit()
            
            room = Room(
                owner_id=owner.user_id,
                title='Room',
                location='San Francisco',
                address='123 St',
                room_type='Shared',
                rent_price=1000
            )
            db.session.add(room)
            db.session.commit()
            
            # Case insensitive matching
            assert room.matches_location('san francisco')
            assert room.matches_location('San Francisco')
            assert not room.matches_location('New York')


class TestCompatibilityScoreModel:
    """Tests for CompatibilityScore model"""
    
    def test_score_creation(self, app):
        """Test creating compatibility score"""
        with app.app_context():
            user1 = User(email='user1@example.com', name='User 1')
            user2 = User(email='user2@example.com', name='User 2')
            db.session.add_all([user1, user2])
            db.session.commit()
            
            score = CompatibilityScore(
                user_a_id=user1.user_id,
                user_b_id=user2.user_id,
                overall_score=85
            )
            db.session.add(score)
            db.session.commit()
            
            assert score.score_id is not None
            assert score.overall_score == 85
    
    def test_score_strength_label(self, app):
        """Test score strength descriptions"""
        with app.app_context():
            user1 = User(email='user1@example.com', name='User 1')
            user2 = User(email='user2@example.com', name='User 2')
            db.session.add_all([user1, user2])
            db.session.commit()
            
            score = CompatibilityScore(
                user_a_id=user1.user_id,
                user_b_id=user2.user_id,
                overall_score=90
            )
            db.session.add(score)
            db.session.commit()
            
            label = score.get_strength_description()
            assert 'Excellent' in label


class TestRecommendationModel:
    """Tests for Recommendation model"""
    
    def test_recommendation_creation(self, app):
        """Test creating recommendation"""
        with app.app_context():
            requester = User(email='requester@example.com', name='Requester')
            match = User(email='match@example.com', name='Match')
            db.session.add_all([requester, match])
            db.session.commit()
            
            rec = Recommendation(
                requester_id=requester.user_id,
                match_type='roommate',
                match_id=match.user_id,
                match_score=80
            )
            db.session.add(rec)
            db.session.commit()
            
            assert rec.recommendation_id is not None
            assert rec.match_score == 80
    
    def test_recommendation_interaction(self, app):
        """Test marking recommendation as viewed/liked"""
        with app.app_context():
            requester = User(email='requester@example.com', name='Requester')
            match = User(email='match@example.com', name='Match')
            db.session.add_all([requester, match])
            db.session.commit()
            
            rec = Recommendation(
                requester_id=requester.user_id,
                match_type='roommate',
                match_id=match.user_id,
                match_score=80
            )
            db.session.add(rec)
            db.session.commit()
            
            # Mark as viewed
            rec.mark_viewed()
            assert rec.viewed_at is not None
            assert rec.get_interaction_status() == 'viewed'
            
            # Mark as liked
            rec.mark_liked()
            assert rec.liked == True
            assert rec.get_interaction_status() == 'liked'


class TestConflictLogModel:
    """Tests for ConflictLog model"""
    
    def test_conflict_creation(self, app):
        """Test creating conflict log"""
        with app.app_context():
            user1 = User(email='user1@example.com', name='User 1')
            user2 = User(email='user2@example.com', name='User 2')
            db.session.add_all([user1, user2])
            db.session.commit()
            
            conflict = ConflictLog(
                user_a_id=user1.user_id,
                user_b_id=user2.user_id,
                conflict_type='soft',
                severity=5,
                reason='Schedule mismatch'
            )
            db.session.add(conflict)
            db.session.commit()
            
            assert conflict.conflict_id is not None
            assert conflict.is_soft_conflict()
    
    def test_conflict_type_detection(self, app):
        """Test hard vs soft conflict detection"""
        with app.app_context():
            user1 = User(email='user1@example.com', name='User 1')
            user2 = User(email='user2@example.com', name='User 2')
            db.session.add_all([user1, user2])
            db.session.commit()
            
            hard_conflict = ConflictLog(
                user_a_id=user1.user_id,
                user_b_id=user2.user_id,
                conflict_type='hard',
                severity=9,
                reason='Pet policy mismatch'
            )
            db.session.add(hard_conflict)
            db.session.commit()
            
            assert hard_conflict.is_hard_conflict()
            assert not hard_conflict.is_soft_conflict()


class TestAuditLogModel:
    """Tests for AuditLog model"""
    
    def test_audit_creation(self, app):
        """Test creating audit log"""
        with app.app_context():
            audit = AuditLog(
                agent_name='Profiling Agent',
                action='user_registered',
                entity_type='user',
                entity_id=1,
                details=json.dumps({'email': 'test@example.com'})
            )
            db.session.add(audit)
            db.session.commit()
            
            assert audit.log_id is not None
            assert audit.agent_name == 'Profiling Agent'
    
    def test_audit_retrieval(self, app):
        """Test retrieving audit logs"""
        with app.app_context():
            # Create multiple logs
            for i in range(3):
                audit = AuditLog(
                    agent_name='Test Agent',
                    action=f'action_{i}',
                    entity_type='user',
                    entity_id=1
                )
                db.session.add(audit)
            db.session.commit()
            
            logs = AuditLog.get_logs_for_agent('Test Agent')
            assert len(logs) == 3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
