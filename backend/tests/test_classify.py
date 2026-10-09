"""품목 → 계정과목 자동 분류 (4단계) — 정규화, 기본 규칙, 조직 규칙(학습), 업로드·제출 연동"""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.classify import CategoryRef, Classifier, LearnedRule, normalize_name
from app.classify.defaults import DEFAULT_CATEGORY_NAMES
from app.models import MappingRule
from tests.conftest import ORGS, create_org, signup, upload_receipt

# 기본 계정과목: 1 식비, 2 간식·음료, 3 비품·소모품, 4 인쇄·홍보, 5 교통비, 6 기타
DEFAULTS = [CategoryRef(id=i, name=name) for i, name in enumerate(DEFAULT_CATEGORY_NAMES, start=1)]
FOOD, SNACK, SUPPLIES, PRINT, TRANSPORT, ETC = range(1, 7)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("제주 삼다수 2L", "제주삼다수"),
        ("제주삼다수500ml", "제주삼다수"),
        ("[1+1] 포카칩(대)", "포카칩"),
        ("A4용지 500매", "a용지"),
        ("종이컵 50입", "종이컵"),
        ("ＫＴＸ 승차권", "ktx승차권"),  # 전각 → 반각, 소문자
        ("(행사)", "행사"),  # 괄호를 빼면 아무것도 안 남으면 괄호 속을 살림
        ("1,200", ""),
    ],
)
def test_normalize_name(name: str, expected: str) -> None:
    assert normalize_name(name) == expected


def test_default_rules_cover_mock_receipt_and_common_items() -> None:
    classifier = Classifier(DEFAULTS)
    assert [classifier.classify(n) for n in ("생수 2L", "A4용지 500매", "종이컵 50입", "과자 세트")] == [
        SNACK,
        SUPPLIES,
        SUPPLIES,
        SNACK,
    ]
    assert classifier.classify("아이스 아메리카노") == SNACK
    assert classifier.classify("참치김밥") == FOOD
    assert classifier.classify("컬러 출력 10장") == PRINT
    assert classifier.classify("카카오T 택시") == TRANSPORT
    # 긴 키워드가 이김: 복사지(비품) > 복사(인쇄)
    assert classifier.classify("복사지 A4") == SUPPLIES
    assert classifier.classify("흑백 복사") == PRINT
    # 모르는 품목·너무 짧은 이름은 미분류
    assert classifier.classify("알 수 없는 물건") is None
    assert classifier.classify("물") is None
    assert classifier.classify("") is None


def test_default_rules_follow_renamed_or_missing_categories() -> None:
    # 총무가 이름을 바꿔도 묶음 낱말이 들어 있으면 그 계정과목
    renamed = [CategoryRef(10, "회식·식대"), CategoryRef(11, "간식비"), CategoryRef(12, "사무용품")]
    classifier = Classifier(renamed)
    assert classifier.classify("떡볶이") == 10
    assert classifier.classify("콜라 1.5L") == 11
    assert classifier.classify("볼펜") == 12

    # 맞는 계정과목이 없는 묶음은 건너뛰고 다음 키워드로 (종이컵=비품 없음 → 커피=간식)
    no_supplies = [CategoryRef(20, "식비"), CategoryRef(21, "간식·음료")]
    assert Classifier(no_supplies).classify("커피 종이컵") == 21
    assert Classifier(no_supplies).classify("종이컵") is None
    assert Classifier([]).classify("생수") is None

    # 이름이 똑같은 계정과목이 '들어 있는' 계정과목보다 먼저
    both = [CategoryRef(30, "행사 식비"), CategoryRef(31, "식비")]
    assert Classifier(both).classify("도시락") == 31


def test_learned_rules_come_before_defaults() -> None:
    rules = [LearnedRule(keyword="생수", category_id=ETC, hit_count=1)]
    classifier = Classifier(DEFAULTS, rules)
    assert classifier.classify("생수 500ml") == ETC  # 이름이 같음 (용량은 무시)
    assert classifier.classify("탄산 생수") == SNACK  # 2글자 규칙은 '들어 있음'으로 안 씀 → 기본 규칙

    rules = [LearnedRule(keyword="아메리카노", category_id=ETC, hit_count=1)]
    assert Classifier(DEFAULTS, rules).classify("아이스 아메리카노") == ETC  # 3글자 이상은 들어 있어도 적용


def test_learned_rules_pick_majority_then_latest() -> None:
    old, new = datetime(2026, 10, 1, tzinfo=UTC), datetime(2026, 10, 2, tzinfo=UTC)
    majority = [
        LearnedRule("생수", ETC, hit_count=3, updated_at=new),
        LearnedRule("생수", FOOD, hit_count=1, updated_at=new),
    ]
    assert Classifier(DEFAULTS, majority).classify("생수") == ETC

    tie = [LearnedRule("생수", ETC, hit_count=1, updated_at=old), LearnedRule("생수", FOOD, hit_count=1, updated_at=new)]
    assert Classifier(DEFAULTS, tie).classify("생수") == FOOD

    # 이 조직에 없는(지워진) 계정과목을 가리키는 규칙은 무시
    stale = [LearnedRule("생수", 999, hit_count=5)]
    assert Classifier(DEFAULTS, stale).classify("생수") == SNACK


# ---------- 업로드·제출 연동 ----------


def _items(expense: dict) -> list[tuple[str, int | None, str | None]]:
    return [(i["name"], i["category_id"], i["category_source"]) for i in expense["items"]]


@pytest.fixture
def org(client: TestClient) -> dict:
    owner = signup(client, "owner@example.com", "총무")
    created = create_org(client, owner)
    categories = {c["name"]: c["id"] for c in client.get(f"{ORGS}/{created['id']}/categories", headers=owner).json()}
    return {"id": created["id"], "owner": owner, "categories": categories}


def _put_body(expense: dict, items: list[dict]) -> dict:
    receipt = expense["receipt"]
    return {
        "store_name": receipt["store_name"],
        "paid_at": receipt["paid_at"],
        "total_amount": receipt["total_amount"],
        "payer_membership_id": expense["payer"]["membership_id"],
        "items": items,
    }


def test_upload_classifies_items_automatically(client: TestClient, org: dict) -> None:
    expense = upload_receipt(client, org["owner"], org["id"]).json()
    c = org["categories"]
    assert _items(expense) == [
        ("생수 2L", c["간식·음료"], "AUTO"),
        ("A4용지 500매", c["비품·소모품"], "AUTO"),
        ("종이컵 50입", c["비품·소모품"], "AUTO"),
        ("과자 세트", c["간식·음료"], "AUTO"),
    ]


def test_corrections_are_learned_on_submit_only(client: TestClient, org: dict, db_session: Session) -> None:
    c, owner, org_id = org["categories"], org["owner"], org["id"]
    expense = upload_receipt(client, owner, org_id).json()
    items = [
        {k: i[k] for k in ("name", "quantity", "unit_price", "amount", "category_id")} for i in expense["items"]
    ]
    items[0]["category_id"] = c["기타"]  # 생수: 간식·음료 → 기타 (고침)
    target = f"{ORGS}/{org_id}/expenses/{expense['id']}"

    saved = client.put(target, json=_put_body(expense, items), headers=owner).json()
    assert [i["category_source"] for i in saved["items"]] == ["MANUAL", "AUTO", "AUTO", "AUTO"]

    def rules() -> list[tuple[str, int, int]]:
        rows = db_session.scalars(select(MappingRule).where(MappingRule.organization_id == org_id))
        return sorted((r.keyword, r.category_id, r.hit_count) for r in rows)

    # 임시 저장만으로는 안 배움 (여러 번 저장해도 횟수가 안 부풀게)
    assert rules() == []
    assert client.post(f"{target}/submit", headers=owner).status_code == 200
    # 고친 품목만 규칙이 됨. 자동 분류를 그대로 둔 품목은 저장 안 함
    assert rules() == [("생수", c["기타"], 1)]

    # 다음 영수증부터 반영
    again = upload_receipt(client, owner, org_id).json()
    assert _items(again)[0] == ("생수 2L", c["기타"], "AUTO")

    # 다른 조직에는 영향 없음
    other_owner = signup(client, "other@example.com", "다른 총무")
    other = create_org(client, other_owner, "다른 동아리")
    other_categories = {
        x["name"]: x["id"] for x in client.get(f"{ORGS}/{other['id']}/categories", headers=other_owner).json()
    }
    other_expense = upload_receipt(client, other_owner, other["id"]).json()
    assert _items(other_expense)[0] == ("생수 2L", other_categories["간식·음료"], "AUTO")


def test_deleting_category_removes_its_rules(client: TestClient, org: dict, db_session: Session) -> None:
    owner, org_id = org["owner"], org["id"]
    extra = client.post(f"{ORGS}/{org_id}/categories", json={"name": "행사비"}, headers=owner).json()
    db_session.add(MappingRule(organization_id=org_id, keyword="생수", category_id=extra["id"], hit_count=1))
    db_session.commit()

    assert client.delete(f"{ORGS}/{org_id}/categories/{extra['id']}", headers=owner).status_code == 204
    assert db_session.scalars(select(MappingRule).where(MappingRule.organization_id == org_id)).all() == []
    assert _items(upload_receipt(client, owner, org_id).json())[0][1] == org["categories"]["간식·음료"]
