from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import SQLModel
from app.schemas.user import UserCreate
from app.schemas.token import Token
from app.db.session import get_session
from app.db.crud import create_user, authenticate_user
from app.core.security import create_access_token, create_refresh_token
from fastapi.responses import JSONResponse

router = APIRouter()

@router.post("/register", response_model=None, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, session=Depends(get_session)):
    existing = await create_user(session, user_in.email, user_in.password)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"message": "user created", "id": str(existing.id)})

@router.post("/login", response_model=Token)
async def login(form_data: UserCreate, session=Depends(get_session)):
    user = await authenticate_user(session, form_data.email, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect credentials")
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))
    return Token(access_token=access_token, refresh_token=refresh_token)

