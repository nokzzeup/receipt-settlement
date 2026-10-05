from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, StringConstraints


def _lower(value: str) -> str:
    return value.lower()


# 대소문자만 다른 중복 가입 방지: 항상 소문자로 저장·비교
Email = Annotated[EmailStr, AfterValidator(_lower)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


class SignupRequest(BaseModel):
    email: Email
    password: str = Field(min_length=8, max_length=128, description="8자 이상")
    name: Name


class LoginRequest(BaseModel):
    email: Email
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
