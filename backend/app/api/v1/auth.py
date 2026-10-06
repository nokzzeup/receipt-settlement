import math

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DbSession
from app.core.ratelimit import login_failures_by_account, login_failures_by_ip
from app.core.security import create_access_token, hash_password, verify_password, verify_password_for_missing_user
from app.models import User
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

EMAIL_TAKEN = "이미 가입된 이메일입니다."


def _token_response(user: User) -> TokenResponse:
    return TokenResponse(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, db: DbSession) -> TokenResponse:
    """회원가입 후 바로 로그인 상태(토큰 발급)"""
    if db.scalar(select(User.id).where(User.email == body.email)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, EMAIL_TAKEN)
    user = User(email=body.email, password_hash=hash_password(body.password), name=body.name)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # 동시에 같은 이메일로 가입한 경우
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, EMAIL_TAKEN) from None
    return _token_response(user)


@router.post("/login", responses={429: {"description": "로그인 실패가 너무 많아 잠시 차단됨"}})
def login(body: LoginRequest, request: Request, db: DbSession) -> TokenResponse:
    ip = request.client.host if request.client else "unknown"
    account_key = f"{ip}|{body.email}"
    wait = max(login_failures_by_account.retry_after(account_key), login_failures_by_ip.retry_after(ip))
    if wait:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"로그인 실패가 너무 많아요. {math.ceil(wait / 60)}분 뒤에 다시 시도하세요.",
            headers={"Retry-After": str(wait)},
        )

    user = db.scalar(select(User).where(User.email == body.email))
    if user is None:
        verify_password_for_missing_user(body.password)
    if user is None or not verify_password(body.password, user.password_hash):
        login_failures_by_account.record(account_key)
        login_failures_by_ip.record(ip)
        # 이메일이 틀렸는지 비밀번호가 틀렸는지 구분해서 알려주지 않음 (가입 여부 노출 방지)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "이메일 또는 비밀번호가 올바르지 않습니다.")
    login_failures_by_account.clear(account_key)
    return _token_response(user)


@router.get("/me")
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
