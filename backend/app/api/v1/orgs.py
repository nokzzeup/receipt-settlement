"""조직: 생성, 내 조직 목록, 초대 코드 참여/재발급, 구성원·역할 관리.

권한 요약
- 조직 생성자는 총무(TREASURER), 초대 코드로 들어온 사람은 구성원(MEMBER)
- 조직 정보·구성원 목록: 그 조직 구성원 누구나 (구성원이 아니면 404)
- 초대 코드 보기·재발급, 역할 변경: 총무만 (403)
- 총무는 항상 1명 이상 남아야 함 (마지막 총무의 역할은 못 바꿈)
"""

import secrets

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import CurrentMembership, CurrentUser, DbSession, TreasurerMembership
from app.models import Membership, MembershipRole, Organization, User
from app.schemas.org import InviteCodeOut, JoinRequest, MemberOut, OrgCreate, OrgDetail, OrgSummary, RoleUpdate

router = APIRouter(prefix="/orgs", tags=["orgs"])

# 헷갈리는 글자(0/O, 1/I/L) 제외 → 말로 불러주거나 손으로 받아 적어도 안 틀리게
INVITE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
INVITE_LENGTH = 8


def _new_invite_code(db: DbSession) -> str:
    while True:
        code = "".join(secrets.choice(INVITE_ALPHABET) for _ in range(INVITE_LENGTH))
        if db.scalar(select(Organization.id).where(Organization.invite_code == code)) is None:
            return code


def _normalize_code(raw: str) -> str:
    return raw.replace("-", "").replace(" ", "").upper()


def _org_detail(org: Organization, membership: Membership) -> OrgDetail:
    return OrgDetail(
        id=org.id,
        name=org.name,
        my_role=membership.role,
        invite_code=org.invite_code if membership.role == MembershipRole.TREASURER else None,
        created_at=org.created_at,
    )


def _member_out(membership: Membership, user: User) -> MemberOut:
    return MemberOut(
        membership_id=membership.id,
        user_id=user.id,
        name=user.name,
        email=user.email,
        role=membership.role,
        joined_at=membership.created_at,
    )


@router.get("")
def list_my_orgs(user: CurrentUser, db: DbSession) -> list[OrgSummary]:
    """내가 속한 조직 목록 (최근 참여 순)"""
    member_count = (
        select(func.count(Membership.id))
        .where(Membership.organization_id == Organization.id)
        .correlate(Organization)
        .scalar_subquery()
    )
    rows = db.execute(
        select(Organization, Membership.role, member_count)
        .join(Membership, Membership.organization_id == Organization.id)
        .where(Membership.user_id == user.id)
        .order_by(Membership.created_at.desc(), Membership.id.desc())
    ).all()
    return [OrgSummary(id=org.id, name=org.name, my_role=role, member_count=count) for org, role, count in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_org(body: OrgCreate, user: CurrentUser, db: DbSession) -> OrgDetail:
    """조직 생성 → 만든 사람이 총무"""
    org = Organization(name=body.name, invite_code=_new_invite_code(db), created_by=user)
    membership = Membership(organization=org, user=user, role=MembershipRole.TREASURER)
    db.add_all([org, membership])
    db.commit()
    db.refresh(org)
    return _org_detail(org, membership)


@router.post("/join")
def join_org(body: JoinRequest, user: CurrentUser, db: DbSession) -> OrgDetail:
    """초대 코드로 참여 → 구성원(MEMBER). 대소문자·하이픈·공백은 무시"""
    org = db.scalar(select(Organization).where(Organization.invite_code == _normalize_code(body.invite_code)))
    if org is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "초대 코드가 올바르지 않습니다. 총무에게 최신 코드를 확인하세요.")
    exists = db.scalar(
        select(Membership.id).where(Membership.organization_id == org.id, Membership.user_id == user.id)
    )
    if exists is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 참여한 조직입니다.")
    membership = Membership(organization=org, user=user, role=MembershipRole.MEMBER)
    db.add(membership)
    db.commit()
    return _org_detail(org, membership)


@router.get("/{org_id}")
def get_org(org_id: int, me: CurrentMembership, db: DbSession) -> OrgDetail:
    return _org_detail(db.get_one(Organization, org_id), me)


@router.post("/{org_id}/invite-code")
def regenerate_invite_code(org_id: int, me: TreasurerMembership, db: DbSession) -> InviteCodeOut:
    """초대 코드 재발급 (총무). 이전 코드는 즉시 무효"""
    org = db.get_one(Organization, org_id)
    org.invite_code = _new_invite_code(db)
    db.commit()
    return InviteCodeOut(invite_code=org.invite_code)


@router.get("/{org_id}/members")
def list_members(org_id: int, me: CurrentMembership, db: DbSession) -> list[MemberOut]:
    role_order = {MembershipRole.TREASURER: 0, MembershipRole.APPROVER: 1, MembershipRole.MEMBER: 2}
    rows = db.execute(
        select(Membership, User).join(User, User.id == Membership.user_id).where(Membership.organization_id == org_id)
    ).all()
    rows.sort(key=lambda r: (role_order[r[0].role], r[0].created_at, r[0].id))
    return [_member_out(m, u) for m, u in rows]


@router.patch("/{org_id}/members/{membership_id}")
def update_member_role(
    org_id: int, membership_id: int, body: RoleUpdate, me: TreasurerMembership, db: DbSession
) -> MemberOut:
    """구성원 역할 변경 (총무). 총무를 여러 명 둘 수 있지만 0명이 되게는 못 함"""
    target = db.get(Membership, membership_id)
    if target is None or target.organization_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "구성원을 찾을 수 없습니다.")
    if target.role == MembershipRole.TREASURER and body.role != MembershipRole.TREASURER:
        treasurers = db.scalar(
            select(func.count(Membership.id)).where(
                Membership.organization_id == org_id, Membership.role == MembershipRole.TREASURER
            )
        )
        if treasurers <= 1:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "총무가 최소 1명은 있어야 합니다. 다른 사람을 먼저 총무로 지정하세요."
            )
    target.role = body.role
    db.commit()
    return _member_out(target, target.user)
