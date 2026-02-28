"""
Database utilities for connection, initialization, and migration
Handles SQLite initialization and PostgreSQL connection management
"""

import sqlite3
import os
from pathlib import Path
from sqlalchemy import text
from app import db


def init_db(app=None):
    """
    Initialize the database.
    - Creates tables from schema
    - Inserts seed data (optional)
    
    Args:
        app: Flask application instance (if None, uses default context)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Ensure database directory exists
        db_path = Path('database')
        db_path.mkdir(exist_ok=True)
        
        # Read and execute schema
        schema_path = Path('database/schema.sql')
        if not schema_path.exists():
            print(f"❌ Schema file not found: {schema_path}")
            return False
        
        with open(schema_path, 'r') as f:
            schema = f.read()
        
        # Execute schema (split by GO statement for compatibility)
        if app:
            with app.app_context():
                db.session.execute(text(schema))
                db.session.commit()
        else:
            # Direct SQLite execution
            conn = sqlite3.connect('database/roommate_system.db')
            cursor = conn.cursor()
            cursor.executescript(schema)
            conn.commit()
            conn.close()
        
        print("✅ Database initialized successfully")
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {str(e)}")
        return False


def reset_db(app=None, confirm=True):
    """
    Drop all tables and reinitialize.
    WARNING: This deletes all data!
    
    Args:
        app: Flask application instance
        confirm: Require confirmation before resetting
    
    Returns:
        bool: True if successful
    """
    if confirm:
        response = input("⚠️  This will delete ALL data. Type 'yes' to confirm: ")
        if response.lower() != 'yes':
            print("Reset cancelled")
            return False
    
    try:
        if app:
            with app.app_context():
                db.drop_all()
                db.session.commit()
        else:
            conn = sqlite3.connect('database/roommate_system.db')
            cursor = conn.cursor()
            
            # Drop all tables
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table'
            """)
            tables = cursor.fetchall()
            
            for table in tables:
                cursor.execute(f"DROP TABLE IF EXISTS {table[0]}")
            
            conn.commit()
            conn.close()
        
        # Reinitialize
        return init_db(app)
        
    except Exception as e:
        print(f"❌ Database reset failed: {str(e)}")
        return False


def seed_test_data(app=None):
    """
    Insert sample data for testing.
    Uses data from database/seed_data.sql
    
    Args:
        app: Flask application instance
    
    Returns:
        bool: True if successful
    """
    try:
        seed_path = Path('database/seed_data.sql')
        if not seed_path.exists():
            print("⚠️  Seed data file not found, skipping")
            return True
        
        with open(seed_path, 'r') as f:
            seed_data = f.read()
        
        if app:
            with app.app_context():
                db.session.execute(text(seed_data))
                db.session.commit()
        else:
            conn = sqlite3.connect('database/roommate_system.db')
            cursor = conn.cursor()
            cursor.executescript(seed_data)
            conn.commit()
            conn.close()
        
        print("✅ Test data seeded successfully")
        return True
        
    except Exception as e:
        print(f"❌ Seeding test data failed: {str(e)}")
        return False


def get_db_stats(app):
    """
    Get database statistics for monitoring
    
    Returns:
        dict: Statistics about tables, row counts, etc.
    """
    stats = {
        'users': 0,
        'rooms': 0,
        'preferences': 0,
        'scores': 0,
        'recommendations': 0,
        'conflicts': 0
    }
    
    try:
        with app.app_context():
            for table, _ in stats.items():
                result = db.session.execute(
                    text(f"SELECT COUNT(*) FROM {table}")
                ).fetchone()
                stats[table] = result[0] if result else 0
    except Exception as e:
        print(f"⚠️  Could not get DB stats: {str(e)}")
    
    return stats


def backup_db(backup_name='backup'):
    """
    Create a backup of the database
    
    Args:
        backup_name: Name of backup file (without extension)
    
    Returns:
        str: Path to backup file if successful, None otherwise
    """
    try:
        backup_dir = Path('backups')
        backup_dir.mkdir(exist_ok=True)
        
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = backup_dir / f"{backup_name}_{timestamp}.db"
        
        # Copy database file
        import shutil
        db_file = Path('database/roommate_system.db')
        if db_file.exists():
            shutil.copy2(db_file, backup_file)
            print(f"✅ Database backed up to: {backup_file}")
            return str(backup_file)
        else:
            print("⚠️  Database file not found for backup")
            return None
            
    except Exception as e:
        print(f"❌ Backup failed: {str(e)}")
        return None


def verify_db_health(app):
    """
    Check database integrity and consistency
    
    Args:
        app: Flask application instance
    
    Returns:
        dict: Health check results
    """
    health = {
        'status': 'healthy',
        'tables': [],
        'errors': []
    }
    
    try:
        with app.app_context():
            # Check table existence
            tables = [
                'users', 'user_preferences', 'preference_vectors',
                'rooms', 'compatibility_scores', 'conflict_log',
                'recommendations', 'interactions'
            ]
            
            for table in tables:
                try:
                    db.session.execute(text(f"SELECT COUNT(*) FROM {table} LIMIT 1"))
                    health['tables'].append({
                        'name': table,
                        'status': 'ok'
                    })
                except Exception as e:
                    health['tables'].append({
                        'name': table,
                        'status': 'error',
                        'error': str(e)
                    })
                    health['errors'].append(f"Table {table}: {str(e)}")
            
            if health['errors']:
                health['status'] = 'warning'
                
    except Exception as e:
        health['status'] = 'error'
        health['errors'].append(f"Connection error: {str(e)}")
    
    return health


def cleanup_old_data(app, days=90):
    """
    Remove old recommendation and audit logs
    Helps keep database size manageable
    
    Args:
        app: Flask application instance
        days: Delete records older than this many days
    
    Returns:
        int: Number of records deleted
    """
    try:
        with app.app_context():
            deleted = db.session.execute(text(f"""
                DELETE FROM recommendations 
                WHERE created_at < datetime('now', '-{int(days)} days')
            """)).rowcount
            
            deleted += db.session.execute(text(f"""
                DELETE FROM audit_log 
                WHERE timestamp < datetime('now', '-{int(days)} days')
            """)).rowcount
            
            db.session.commit()
            
            print(f"✅ Deleted {deleted} old records")
            return deleted
            
    except Exception as e:
        print(f"❌ Cleanup failed: {str(e)}")
        return 0


if __name__ == '__main__':
    """
    Database utility CLI
    
    Usage:
        python backend/utils/database.py init        - Initialize DB
        python backend/utils/database.py reset       - Reset DB
        python backend/utils/database.py seed        - Seed test data
        python backend/utils/database.py stats       - Show statistics
        python backend/utils/database.py backup      - Backup database
        python backend/utils/database.py health      - Health check
    """
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: database.py [init|reset|seed|stats|backup|health]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'init':
        init_db()
    elif command == 'reset':
        reset_db()
    elif command == 'seed':
        seed_test_data()
    elif command == 'stats':
        stats = get_db_stats(None)
        for table, count in stats.items():
            print(f"  {table}: {count} rows")
    elif command == 'backup':
        backup_db()
    elif command == 'health':
        health = verify_db_health(None)
        print(f"Status: {health['status']}")
        for table in health['tables']:
            print(f"  {table['name']}: {table['status']}")
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
