from datetime import date, datetime
from typing import Annotated, Self

from pydantic import BaseModel, StringConstraints, model_validator

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
    # 지금 예산 기간 (한국 날짜, 양 끝 포함). 둘 다 null = 기간 없음(전체 누적)
    budget_period_start: date | None
    budget_period_end: date | None
    created_at: datetime


class OrgUpdate(BaseModel):
    """조직 설정 (총무). 보낸 칸만 바꾼다. 예산 기간은 시작·끝을 같이 보내고, 둘 다 null이면 기간 없음"""

    name: OrgName | None = None
    budget_period_start: date | None = None
    budget_period_end: date | None = None

    @model_validator(mode="after")
    def _check_period(self) -> Self:
        fields = self.model_fields_set & {"budget_period_start", "budget_period_end"}
        if not fields:
            return self
        if len(fields) == 1 or (self.budget_period_start is None) != (self.budget_period_end is None):
            raise ValueError("예산 기간은 시작일과 끝일을 같이 정하세요.")
        if self.budget_period_start and self.budget_period_end and self.budget_period_start > self.budget_period_end:
            raise ValueError("예산 기간의 시작일이 끝일보다 늦습니다.")
        return self


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
