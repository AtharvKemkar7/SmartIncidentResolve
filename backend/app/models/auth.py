from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=1)


class User(BaseModel):
    email: str
    name: str


class LoginResponse(BaseModel):
    token: str
    user: User


class MeResponse(BaseModel):
    user: User
