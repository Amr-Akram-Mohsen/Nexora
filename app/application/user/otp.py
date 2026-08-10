import random
import logging
from app.core.extensions import cache

logger = logging.getLogger(__name__)

OTP_TIMEOUT = 900  # 15 minutes

def generate_otp(email: str, intent: str) -> str:
    """
    Generates a 6-digit OTP code, stores it in cache for the specific intent,
    and returns it.
    Intent examples: 'register', 'reset', 'update_email'
    """
    code = f"{random.randint(100000, 999999)}"
    key = f"otp:{intent}:{email}"
    cache.set(key, code, timeout=OTP_TIMEOUT)
    logger.info("[AUTH] Generated %s OTP for %s", intent, email)
    return code

def verify_otp(email: str, intent: str, code: str) -> bool:
    """
    Verifies the OTP code for the given email and intent.
    Deletes it upon successful verification to prevent reuse.
    """
    if not code:
        return False
        
    key = f"otp:{intent}:{email}"
    stored = cache.get(key)
    
    if stored and stored == str(code).strip():
        cache.delete(key)
        logger.info("[AUTH] Successfully verified %s OTP for %s", intent, email)
        return True
        
    logger.warning("[AUTH] Failed to verify %s OTP for %s", intent, email)
    return False
