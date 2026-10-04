"""모든 모델을 여기서 import → Base.metadata에 등록된다.

Alembic(env.py)·앱(main.py)·테스트(conftest.py)는 반드시 `import app.models`를 먼저 해서
관계(relationship)가 문자열로 서로를 참조할 수 있게 한다.

공통 규칙
- 금액·수량 컬럼은 StrictInteger(app/db/types.py) → int가 아니면 저장 시 에러
  (PostgreSQL로 옮길 때 BIGINT로 바꾸면 SUM 결과가 Decimal이 되어 'int만' 규칙이 깨지니 INTEGER 유지)
- datetime 컬럼은 전부 UTCDateTime → 시간대 없는 값은 저장 시 에러, 읽으면 UTC 기준 aware datetime
- DB는 SQLite 기본. JSONB처럼 특정 DB 전용 타입은 쓰지 않는다 (PostgreSQL 전환 가능성 유지)
- 삭제 정책: ON DELETE CASCADE는 지출→품목·결재이력, 계정과목→매핑규칙에만 둔다.
  조직·멤버십·영수증·계정과목은 참조하는 데이터가 있으면 DB가 삭제를 막는다 (재무 기록 보존).
  조직 삭제·탈퇴 기능이 필요해지면 하드 삭제 대신 soft delete(컬럼 추가)로 간다.
"""

from app.models.approval_log import ApprovalLog
from app.models.category import Category
from app.models.enums import ApprovalAction, CategorySource, ExpenseStatus, MembershipRole
from app.models.expense import Expense, ExpenseItem
from app.models.mapping_rule import MappingRule
from app.models.organization import Membership, Organization
from app.models.receipt import Receipt
from app.models.user import User

__all__ = [
    "ApprovalAction",
    "ApprovalLog",
    "Category",
    "CategorySource",
    "Expense",
    "ExpenseItem",
    "ExpenseStatus",
    "MappingRule",
    "Membership",
    "MembershipRole",
    "Organization",
    "Receipt",
    "User",
]
