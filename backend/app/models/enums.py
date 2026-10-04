"""도메인 Enum. DB에는 문자열(VARCHAR + CHECK 제약)로 저장한다.

PostgreSQL 네이티브 ENUM을 쓰지 않는 이유: 값을 추가·변경할 때 Alembic autogenerate가
네이티브 ENUM 변경을 감지하지 못해 마이그레이션을 손으로 써야 함. (도메인 모델이 아직 초안이라 변경 가능성 큼)
"""

from enum import StrEnum


class MembershipRole(StrEnum):
    TREASURER = "TREASURER"  # 총무
    APPROVER = "APPROVER"  # 승인자
    MEMBER = "MEMBER"  # 구성원


class ExpenseStatus(StrEnum):
    DRAFT = "DRAFT"  # 작성 중 (OCR 확인·수정 단계)
    SUBMITTED = "SUBMITTED"  # 제출됨 → 승인 대기
    APPROVED = "APPROVED"  # 승인됨 → 환급 대상
    REJECTED = "REJECTED"  # 반려됨 (reject_reason)


class CategorySource(StrEnum):
    AUTO = "AUTO"  # 매핑 규칙으로 자동 분류
    MANUAL = "MANUAL"  # 사용자가 직접 지정/수정


class ApprovalAction(StrEnum):
    SUBMIT = "SUBMIT"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REIMBURSE = "REIMBURSE"  # 환급 완료 처리
