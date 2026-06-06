"""
Setup Validation Script

Validates the complete TradeMind AI foundation setup.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.logging import setup_logging, get_logger
from app.core.config import settings
from app.db.supabase import check_database_health
from app.integrations.redis_client import init_redis, check_redis_health, close_redis

setup_logging()
logger = get_logger(__name__)


def validate_configuration():
    """Validate configuration settings"""
    logger.info("Validating configuration...")
    
    try:
        logger.info(f"  App Name: {settings.APP_NAME}")
        logger.info(f"  Version: {settings.APP_VERSION}")
        logger.info(f"  Environment: {settings.ENVIRONMENT}")
        logger.info(f"  Log Level: {settings.LOG_LEVEL}")
        logger.info(f"  API Port: {settings.API_PORT}")
        logger.info("✓ Configuration valid")
        return True
    except Exception as e:
        logger.error(f"✗ Configuration validation failed: {e}")
        return False


def validate_database():
    """Validate database connectivity"""
    logger.info("Validating database connection...")
    
    healthy, message = check_database_health()
    
    if healthy:
        logger.info(f"✓ {message}")
        return True
    else:
        logger.error(f"✗ {message}")
        return False


def validate_redis():
    """Validate Redis connectivity"""
    logger.info("Validating Redis connection...")
    
    try:
        init_redis()
        healthy, message = check_redis_health()
        
        if healthy:
            logger.info(f"✓ {message}")
            return True
        else:
            logger.warning(f"⚠ {message} (non-critical)")
            return True  # Redis is optional
    except Exception as e:
        logger.warning(f"⚠ Redis validation failed: {e} (non-critical)")
        return True
    finally:
        close_redis()


def main():
    """Run all validation checks"""
    logger.info("=" * 60)
    logger.info("TradeMind AI - Foundation Setup Validation")
    logger.info("=" * 60)
    logger.info("")
    
    checks = [
        ("Configuration", validate_configuration),
        ("Database", validate_database),
        ("Redis", validate_redis),
    ]
    
    results = []
    
    for name, check_func in checks:
        logger.info("")
        result = check_func()
        results.append((name, result))
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("Validation Summary")
    logger.info("=" * 60)
    
    all_passed = True
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"  {name:20} {status}")
        if not result:
            all_passed = False
    
    logger.info("")
    
    if all_passed:
        logger.info("✓ All critical checks passed!")
        logger.info("")
        logger.info("Ready to start application:")
        logger.info("  Windows: run.bat")
        logger.info("  Linux/Mac: uvicorn app.main:app --reload --port 8001")
        logger.info("  Docker: docker-compose up --build")
        logger.info("")
        sys.exit(0)
    else:
        logger.error("✗ Some critical checks failed. Fix issues before starting.")
        logger.error("")
        sys.exit(1)


if __name__ == "__main__":
    main()
