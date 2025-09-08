import json
import logging
import sys
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("secure-auth-service")


class SecurityEvent(BaseModel):
    """Security event model for structured logging"""

    event_type: str
    user_id: Optional[str] = None
    email: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    endpoint: Optional[str] = None
    success: bool = True
    details: Optional[str] = None
    timestamp: datetime = datetime.utcnow()


def log_security_event(event: SecurityEvent):
    """Log security events with structured data"""
    event_data = event.model_dump()

    # Convert datetime to ISO format string for JSON serialization
    if "timestamp" in event_data and event_data["timestamp"]:
        event_data["timestamp"] = event_data["timestamp"].isoformat()

    if event.success:
        logger.info(f"SECURITY_EVENT: {json.dumps(event_data)}")
    else:
        logger.warning(f"SECURITY_ALERT: {json.dumps(event_data)}")


def log_auth_success(user_id: str, email: str, ip_address: str, user_agent: str = None):
    """Log successful authentication"""
    event = SecurityEvent(
        event_type="auth_success",
        user_id=user_id,
        email=email,
        ip_address=ip_address,
        user_agent=user_agent,
        success=True,
    )
    log_security_event(event)


def log_auth_failure(email: str, ip_address: str, reason: str, user_agent: str = None):
    """Log failed authentication attempts"""
    event = SecurityEvent(
        event_type="auth_failure",
        email=email,
        ip_address=ip_address,
        user_agent=user_agent,
        success=False,
        details=reason,
    )
    log_security_event(event)


def log_account_lockout(email: str, ip_address: str, user_agent: str = None):
    """Log account lockout events"""
    event = SecurityEvent(
        event_type="account_lockout",
        email=email,
        ip_address=ip_address,
        user_agent=user_agent,
        success=False,
        details="Account locked due to multiple failed attempts",
    )
    log_security_event(event)


def log_rate_limit_exceeded(ip_address: str, endpoint: str, user_agent: str = None):
    """Log rate limit violations"""
    event = SecurityEvent(
        event_type="rate_limit_exceeded",
        ip_address=ip_address,
        endpoint=endpoint,
        user_agent=user_agent,
        success=False,
        details="Rate limit exceeded",
    )
    log_security_event(event)


def log_user_action(
    action: str, user_id: str, target_user_id: str = None, ip_address: str = None
):
    """Log user management actions"""
    event = SecurityEvent(
        event_type="user_action",
        user_id=user_id,
        ip_address=ip_address,
        success=True,
        details=f"Action: {action}, Target: {target_user_id or 'self'}",
    )
    log_security_event(event)
