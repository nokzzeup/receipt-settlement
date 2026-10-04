"""품목 → 계정과목 자동 분류 (4단계, 담당: 이성민).

- 입력: 품목명 + 조직 → 출력: category_id (+ category_source=AUTO)
- 규칙 조회 순서 예시: 조직 규칙(MappingRule.organization_id = 조직) → 전역 규칙(category_name으로 조직 계정과목 매칭)
- 사용자가 계정과목을 수정하면 조직 규칙을 생성/hit_count 증가 (수정 학습)
"""
