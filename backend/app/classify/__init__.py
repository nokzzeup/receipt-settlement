"""품목 → 계정과목 자동 분류 (4단계, 담당: 이성민).

- 업로드 때 receipts/intake.py가 classify_names()로 품목마다 계정과목을 정한다 (category_source=AUTO)
- 제출 때 api/v1/expenses.py가 learn_from_items()로 사용자가 고친 품목을 조직 규칙으로 저장한다
- 규칙 순서·학습 기준은 classifier.py, 기본 키워드는 defaults.py, 이름 비교 기준은 normalize.py
"""

from app.classify.classifier import Classifier, CategoryRef, LearnedRule, classify_names, learn_from_items
from app.classify.normalize import normalize_name

__all__ = ["CategoryRef", "Classifier", "LearnedRule", "classify_names", "learn_from_items", "normalize_name"]
