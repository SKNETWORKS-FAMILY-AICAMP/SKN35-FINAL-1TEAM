from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import UnauthorizedError
from app.core.security import decode_token
from app.db.session import SessionDep
from app.organizations import repository as user_repo
from app.organizations.models import User

bearer_scheme = HTTPBearer(auto_error=False)
BearerToken = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


async def get_current_user(db: SessionDep, credentials: BearerToken) -> User:
    if credentials is None:
        raise UnauthorizedError("로그인이 필요합니다.")

    try:
        user_id = decode_token(credentials.credentials, "access")
    except jwt.InvalidTokenError:
        raise UnauthorizedError("다시 로그인 해주세요.") from None

    user = await user_repo.get_active_user_by_id(db, user_id)

    if user is None:
        raise UnauthorizedError("다시 로그인 해주세요.")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
