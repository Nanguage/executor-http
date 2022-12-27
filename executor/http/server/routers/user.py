from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..user_db.schemas import Token
from ..auth import get_db, auth_user, create_access_token
from ..user_db import crud

router = APIRouter(prefix="/user")


@router.post("/login")
async def login(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db)) -> Token:
    user = auth_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.id is not None:
        crud.create_user_login(db, user.id)
        db.commit()
    access_token = create_access_token(user.username)
    return Token(access_token=access_token)
