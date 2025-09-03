from fastapi import APIRouter, Depends, HTTPException, status, Request
from datetime import datetime, timedelta, timezone
from fastapi.responses import JSONResponse
from email.message import EmailMessage
import os, smtplib, secrets, re
from sqlmodel import select

from app.schemas.user import UserCreate
from app.schemas.token import Token
from app.db.session import get_session
from app.db.crud import create_user, authenticate_user, get_user_by_email
from app.core.security import create_access_token, create_refresh_token
from app.core.rate_limit import conditional_limit
from app.core.logging import log_auth_success, log_auth_failure, log_account_lockout, log_security_event, SecurityEvent
from app.db.models import User

router = APIRouter()



def validate_password_complexity(password: str) -> None:
    errors = []
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long.")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter.")
    if not re.search(r"[0-9]", password):
        errors.append("Password must contain at least one digit.")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        errors.append("Password must contain at least one special character.")
    if errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=" ".join(errors))


def send_verification_email(email: str, token: str):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    email_from = os.getenv("EMAIL_FROM", smtp_user)
    verify_url = f"http://localhost:8000/auth/verify-email?token={token}"
    subject = "Verify your email address"
    body = f"Welcome! Please verify your email by clicking this link: {verify_url}"
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = email_from
    msg["To"] = email
    msg.set_content(body)
    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
    except Exception as e:
        print(f"Failed to send email: {e}")

@router.post("/register", response_model=None, status_code=status.HTTP_201_CREATED)
@conditional_limit("5/minute")
async def register(request: Request, user_in: UserCreate, session=Depends(get_session)):
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")
    
    try:
        validate_password_complexity(user_in.password)
        existing = await create_user(session, user_in.email, user_in.password)
        # Generate verification token
        token = secrets.token_urlsafe(16)
        existing.email_verification_token = token
        existing.email_verified = False
        await session.commit()
        await session.refresh(existing)
        send_verification_email(existing.email, token)
        
        # Log successful registration
        log_security_event(SecurityEvent(
            event_type="user_registration",
            user_id=str(existing.id),
            email=existing.email,
            ip_address=client_ip,
            user_agent=user_agent,
            success=True,
            details="User registered successfully"
        ))
        
        return JSONResponse(status_code=status.HTTP_201_CREATED, content={"message": "user created, verification email sent", "id": str(existing.id)})
    except Exception as e:
        # Log failed registration
        log_security_event(SecurityEvent(
            event_type="user_registration",
            email=user_in.email,
            ip_address=client_ip,
            user_agent=user_agent,
            success=False,
            details=str(e)
        ))
        raise
@router.get("/verify-email")
async def verify_email(token: str, session=Depends(get_session)):
    result = await session.execute(select(User).where(User.email_verification_token == token))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
    user.email_verified = True
    user.email_verification_token = None
    await session.commit()
    return {"message": "Email verified successfully"}


@router.post("/login", response_model=Token)
@conditional_limit("10/minute")
async def login(request: Request, form_data: UserCreate, session=Depends(get_session)):
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")
    
    user = await get_user_by_email(session, form_data.email)
    now = datetime.now(timezone.utc)
    
    # Check if account is locked
    if user and user.locked_until:
        # Ensure locked_until is timezone-aware for comparison
        locked_until = user.locked_until
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        if locked_until > now:
            log_auth_failure(form_data.email, client_ip, "Account locked", user_agent)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Account locked until {locked_until}")
    
    # Authenticate user
    authed_user = await authenticate_user(session, form_data.email, form_data.password)
    if not authed_user:
        # Increment failed_attempts
        if user:
            user.failed_attempts += 1
            # Lock account if too many failed attempts
            if user.failed_attempts >= 5:
                user.locked_until = now + timedelta(minutes=15)
                user.failed_attempts = 0
                log_account_lockout(form_data.email, client_ip, user_agent)
            await session.commit()
            await session.refresh(user)
            
        log_auth_failure(form_data.email, client_ip, "Invalid credentials", user_agent)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect credentials")
    
    # Check if email is verified
    if not authed_user.email_verified:
        log_auth_failure(form_data.email, client_ip, "Email not verified", user_agent)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email not verified")
    
    # Reset failed_attempts on successful login
    authed_user.failed_attempts = 0
    authed_user.locked_until = None
    await session.commit()
    await session.refresh(authed_user)
    
    # Log successful login
    log_auth_success(str(authed_user.id), authed_user.email, client_ip, user_agent)
    
    access_token = create_access_token(subject=str(authed_user.id))
    refresh_token = create_refresh_token(subject=str(authed_user.id))
    return Token(access_token=access_token, refresh_token=refresh_token)

