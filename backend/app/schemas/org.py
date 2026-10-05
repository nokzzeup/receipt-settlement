from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, StringConstraints

from app.models.enums import MembershipRole

OrgName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class OrgCreate(BaseModel):
    name: OrgName


class JoinRequest(BaseModel):
    invite_code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]


class OrgSummary(BaseModel):
    """내 조직 목록의 한 줄"""

    id: int
    name: str
    my_role: MembershipRole
    member_count: int


class OrgDetail(BaseModel):
    id: int
    name: str
    my_role: MembershipRole
    # 총무에게만 보임 (다른 역할이면 null)
    invite_code: str | None
    created_at: datetime


class InviteCodeOut(BaseModel):
    invite_code: str


class MemberOut(BaseModel):
    membership_id: int
    user_id: int
    name: str
    email: str
    role: MembershipRole
    joined_at: datetime


class RoleUpdate(BaseModel):
    role: MembershipRole
