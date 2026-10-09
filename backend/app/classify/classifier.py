"""품목명 → 계정과목 자동 분류 + 수정 학습.

고르는 순서 (먼저 걸리는 것으로 정함)
1. 조직 규칙, 이름이 똑같은 것   — 사용자가 고쳐준 결과. 같은 이름에 여러 계정과목이면 많이 고른 쪽, 같으면 최근 것
2. 조직 규칙, 이름에 들어 있는 것 — 키워드 3글자 이상만 (짧은 이름 하나로 엉뚱한 품목까지 끌려가는 것 방지)
3. 기본 규칙(defaults.py)        — 긴 키워드 우선. 그 묶음에 맞는 계정과목이 조직에 없으면 다음 키워드
4. 못 고르면 None (미분류 → 사용자가 고름)

학습: 제출할 때 사용자가 직접 고른(MANUAL) 품목을 조직 규칙으로 저장한다 (같은 것이면 hit_count + 1).
제출 시점에만 배우는 이유: 임시 저장은 여러 번 하므로 그때마다 세면 횟수가 부풀려짐.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.classify.defaults import DEFAULT_GROUPS, DefaultGroup
from app.classify.normalize import normalize_name
from app.models import Category, CategorySource, ExpenseItem, MappingRule

MIN_KEYWORD_LENGTH = 2  # 이보다 짧은 이름은 규칙으로 저장·비교하지 않음
MIN_CONTAINED_RULE_LENGTH = 3  # 조직 규칙을 '들어 있음'으로 쓸 때 최소 길이
MAX_KEYWORD_LENGTH = 100  # MappingRule.keyword 컬럼 길이
_OLDEST = datetime.min.replace(tzinfo=UTC)


@dataclass(frozen=True)
class CategoryRef:
    id: int
    name: str


@dataclass(frozen=True)
class LearnedRule:
    keyword: str  # normalize_name() 결과
    category_id: int
    hit_count: int
    updated_at: datetime | None = None
    id: int = 0


class Classifier:
    """한 조직의 계정과목·규칙으로 만든 분류기 (DB 없이 동작 → 단위 테스트 가능)"""

    def __init__(self, categories: Sequence[CategoryRef], rules: Sequence[LearnedRule] = ()) -> None:
        category_ids = {c.id for c in categories}
        # 많이 고른 것 → 최근 것 순. 다른 조직·지워진 계정과목을 가리키는 규칙은 무시
        self._rules = sorted(
            (r for r in rules if r.category_id in category_ids and len(r.keyword) >= MIN_KEYWORD_LENGTH),
            key=lambda r: (r.hit_count, r.updated_at or _OLDEST, r.id),
            reverse=True,
        )
        self._group_category = {
            group.key: category_id
            for group in DEFAULT_GROUPS
            if (category_id := _category_for_group(group, categories)) is not None
        }
        # (키워드, 묶음) — 긴 키워드 먼저. 같은 길이면 DEFAULT_GROUPS 순서
        self._keywords = sorted(
            (
                (keyword, group.key)
                for group in DEFAULT_GROUPS
                for keyword in {normalize_name(k) for k in group.keywords}
                if len(keyword) >= MIN_KEYWORD_LENGTH
            ),
            key=lambda pair: -len(pair[0]),
        )

    def classify(self, name: str) -> int | None:
        normalized = normalize_name(name)
        if len(normalized) < MIN_KEYWORD_LENGTH:
            return None
        for rule in self._rules:
            if rule.keyword == normalized:
                return rule.category_id
        contained = [
            r for r in self._rules if len(r.keyword) >= MIN_CONTAINED_RULE_LENGTH and r.keyword in normalized
        ]
        if contained:
            # 긴 키워드가 더 구체적. 같은 길이면 이미 정렬된 순서(많이 고른 것)대로
            return max(contained, key=lambda r: len(r.keyword)).category_id
        for keyword, group_key in self._keywords:
            if keyword in normalized and group_key in self._group_category:
                return self._group_category[group_key]
        return None


def _category_for_group(group: DefaultGroup, categories: Sequence[CategoryRef]) -> int | None:
    """이름이 묶음 낱말과 똑같은 계정과목 → 낱말이 들어 있는 계정과목(먼저 만든 것) 순"""
    aliases = [normalize_name(a) for a in group.aliases]
    normalized = [(c, normalize_name(c.name)) for c in sorted(categories, key=lambda c: c.id)]
    for category, name in normalized:
        if name in aliases:
            return category.id
    for category, name in normalized:
        if any(alias in name for alias in aliases):
            return category.id
    return None


# ---------- DB ----------


def load_classifier(db: Session, organization_id: int) -> Classifier:
    categories = [
        CategoryRef(id=row.id, name=row.name)
        for row in db.execute(select(Category.id, Category.name).where(Category.organization_id == organization_id))
    ]
    rules = [
        LearnedRule(
            keyword=row.keyword, category_id=row.category_id, hit_count=row.hit_count, updated_at=row.updated_at, id=row.id
        )
        for row in db.execute(
            select(
                MappingRule.id, MappingRule.keyword, MappingRule.category_id, MappingRule.hit_count, MappingRule.updated_at
            ).where(MappingRule.organization_id == organization_id, MappingRule.category_id.is_not(None))
        )
    ]
    return Classifier(categories, rules)


def classify_names(db: Session, organization_id: int, names: Sequence[str]) -> list[int | None]:
    if not names:
        return []
    classifier = load_classifier(db, organization_id)
    return [classifier.classify(name) for name in names]


def learn_from_items(db: Session, organization_id: int, items: Iterable[ExpenseItem]) -> None:
    """사용자가 직접 고른 품목 → 조직 규칙 생성/hit_count + 1 (한 지출 안의 같은 품목은 한 번만). commit은 호출한 쪽에서"""
    pairs = {
        (keyword, item.category_id)
        for item in items
        if item.category_source == CategorySource.MANUAL
        and item.category_id is not None
        and MIN_KEYWORD_LENGTH <= len(keyword := normalize_name(item.name)) <= MAX_KEYWORD_LENGTH
    }
    for keyword, category_id in sorted(pairs):
        rule = db.scalar(
            select(MappingRule).where(
                MappingRule.organization_id == organization_id,
                MappingRule.keyword == keyword,
                MappingRule.category_id == category_id,
            )
        )
        if rule is None:
            db.add(MappingRule(organization_id=organization_id, keyword=keyword, category_id=category_id, hit_count=1))
        else:
            rule.hit_count += 1
