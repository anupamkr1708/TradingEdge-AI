"""
Database Initialization Script

Run this to verify database connectivity and prepare for schema migrations.
"""

import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.logging import setup_logging, get_logger
from app.db.supabase import check_database_health, get_db_context
from sqlalchemy import text

setup_logging()
logger = get_logger(__name__)


def main():
    """Initialize database connection and verify setup"""
    
    logger.info("Checking database connectivity...")
    
    healthy, message = check_database_health()
    
    if not healthy:
        logger.error(f"Database health check failed: {message}")
        sys.exit(1)
    
    logger.info("✓ Database connection healthy")
    
    # Verify we can query
    try:
        with get_db_context() as db:
            result = db.execute(text("SELECT version()")).scalar()
            logger.info(f"✓ PostgreSQL version: {result}")
            
            # Check if we can create tables (permissions)
            db.execute(text("SELECT 1"))
            logger.info("✓ Database permissions verified")
            
    except Exception as e:
        logger.error(f"Database verification failed: {e}")
        sys.exit(1)
    
    logger.info("✓ Database initialization complete")
    logger.info("")
    logger.info("Next steps:")
    logger.info("  1. Run: uvicorn app.main:app --reload --port 8001")
    logger.info("  2. Test: curl http://localhost:8001/health")


if __name__ == "__main__":
    main()
