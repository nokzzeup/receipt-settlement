"""계정과목(= 예산 항목) 관리.

권한
- 목록: 그 조직 구성원 누구나 (품목의 계정과목을 고를 때 필요)
- 추가·수정·삭제: 총무만
- 품목에서 쓰고 있는 계정과목은 삭제 불가(409) → 이름을 바꿔서 쓰게 한다 (재무 기록 보존)
"""

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.api.deps import CurrentMembership, DbSession, TreasurerMembership
from app.models import Category, ExpenseItem
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate

router = APIRouter(prefix="/orgs/{org_id}/categories", tags=["categories"])


def _get_category(db: DbSession, org_id: int, category_id: int) -> Category:
    category = db.get(Category, category_id)
    if category is None or category.organization_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "계정과목을 찾을 수 없습니다.")
    return category


def _ensure_name_free(db: DbSession, org_id: int, name: str, exclude_id: int | None = None) -> None:
    query = select(Category.id).where(Category.organization_id == org_id, Category.name == name)
    if exclude_id is not None:
        query = query.where(Category.id != exclude_id)
    if db.scalar(query) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"'{name}' 계정과목이 이미 있습니다.")


@router.get("")
def list_categories(org_id: int, me: CurrentMembership, db: DbSession) -> list[CategoryOut]:
    """만든 순서대로"""
    rows = db.scalars(select(Category).where(Category.organization_id == org_id).order_by(Category.id))
    return [CategoryOut.model_validate(c) for c in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_category(org_id: int, body: CategoryCreate, me: TreasurerMembership, db: DbSession) -> CategoryOut:
    _ensure_name_free(db, org_id, body.name)
    category = Category(organization_id=org_id, name=body.name, budget_amount=body.budget_amount)
    db.add(category)
    db.commit()
    return CategoryOut.model_validate(category)


@router.patch("/{category_id}")
def update_category(
    org_id: int, category_id: int, body: CategoryUpdate, me: TreasurerMembership, db: DbSession
) -> CategoryOut:
    category = _get_category(db, org_id, category_id)
    if body.name is not None and body.name != category.name:
        _ensure_name_free(db, org_id, body.name, exclude_id=category.id)
        category.name = body.name
    if "budget_amount" in body.model_fields_set:  # null을 보냈으면 예산 해제
        category.budget_amount = body.budget_amount
    db.commit()
    return CategoryOut.model_validate(category)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(org_id: int, category_id: int, me: TreasurerMembership, db: DbSession) -> Response:
    category = _get_category(db, org_id, category_id)
    in_use = db.scalar(select(ExpenseItem.id).where(ExpenseItem.category_id == category.id).limit(1))
    if in_use is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "품목에서 쓰고 있는 계정과목은 삭제할 수 없습니다. 이름을 바꿔서 쓰세요."
        )
    db.delete(category)  # 이 계정과목을 가리키는 매핑 규칙은 DB가 같이 지움 (ON DELETE CASCADE)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
