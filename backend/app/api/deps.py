"""라우터에서 쓰는 공통 의존성.

    def handler(db: DbSession, user: CurrentUser): ...                       # 로그인만 필요
    def handler(org_id: int, me: CurrentMembership): ...                     # 그 조직 구성원만
    def handler(org_id: int, me: TreasurerMembership): ...                   # 그 조직 총무만
    def handler(org_id: int, me: Annotated[Membership, Depends(require_roles(A, B))]): ...

권한은 항상 "조직 멤버십 + 역할"로 서버에서 확인한다. 경로에 {org_id}가 있는 API는
CurrentMembership(또는 역할 의존성)을 반드시 거쳐야 다른 조직 데이터에 접근할 수 없다.
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Path, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import Membership, MembershipRole, User
from app.models.enums import ROLE_LABELS
from app.ocr import OcrEngine, get_ocr_engine

DbSession = Annotated[Session, Depends(get_db)]
OcrEngineDep = Annotated[OcrEngine, Depends(get_ocr_engine)]

_bearer = HTTPBearer(auto_error=False, description="로그인/회원가입 응답의 access_token")


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"})


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise _unauthorized("로그인이 필요합니다.")
    user_id = decode_access_token(credentials.credentials)
    user = db.get(User, user_id) if user_id is not None else None
    if user is None:
        raise _unauthorized("로그인이 만료되었거나 올바르지 않습니다. 다시 로그인하세요.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_membership(
    org_id: Annotated[int, Path(description="조직 id")],
    user: CurrentUser,
    db: DbSession,
) -> Membership:
    membership = db.scalar(
        select(Membership).where(Membership.organization_id == org_id, Membership.user_id == user.id)
    )
    if membership is None:
        # 구성원이 아니면 조직이 있는지조차 알려주지 않는다 (403 대신 404)
        raise HTTPException(status.HTTP_404_NOT_FOUND, "조직을 찾을 수 없습니다.")
    return membership


CurrentMembership = Annotated[Membership, Depends(get_current_membership)]


def require_roles(*roles: MembershipRole) -> Callable[[Membership], Membership]:
    allowed = set(roles)
    labels = "·".join(ROLE_LABELS[r] for r in roles)

    def dependency(membership: CurrentMembership) -> Membership:
        if membership.role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"{labels}만 할 수 있는 작업입니다.")
        return membership

    return dependency


TreasurerMembership = Annotated[Membership, Depends(require_roles(MembershipRole.TREASURER))]
