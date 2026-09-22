from fastapi import APIRouter

from app.core.security import CurrentUser, authenticate, create_token
from app.models.auth import LoginRequest, LoginResponse, MeResponse, User

router = APIRouter()


@router.post("/auth/login", response_model=LoginResponse)
def login(body: LoginRequest) -> LoginResponse:
    user = authenticate(body.email, body.password)
    return LoginResponse(token=create_token(user.email), user=user)


@router.get("/auth/me", response_model=MeResponse)
def me(user: CurrentUser) -> MeResponse:
    return MeResponse(user=User(email=user.email, name=user.name))
