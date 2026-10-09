"""5단계: 승인·반려·제출 취소·승인 취소·환급 완료(+취소), 정산 요약, 한 번에 환급, 예산 기간·경고"""

from fastapi.testclient import TestClient

from tests.conftest import ORGS, create_org, signup, upload_receipt, url, valid_body


def submitted(client: TestClient, team: dict, who: str = "alice", payer: str = "앨리스") -> dict:
    """업로드 → 저장(생수 2,400 간식 + A4용지 6,500 비품 = 8,900원) → 제출"""
    expense = upload_receipt(client, team[who], team["org_id"]).json()
    assert client.put(url(team, expense["id"]), json=valid_body(team, payer=payer), headers=team[who]).status_code == 200
    response = client.post(url(team, expense["id"], "/submit"), headers=team[who])
    assert response.status_code == 200, response.text
    return response.json()


def act(client: TestClient, team: dict, who: str, expense: dict, action: str, body: dict | None = None):
    path = {"reimburse": "/reimbursement", "unreimburse": "/reimbursement"}.get(action, f"/{action}")
    target = url(team, expense["id"], path)
    if action == "unreimburse":
        return client.delete(target, headers=team[who])
    if action in ("approve", "reject", "unapprove"):
        return client.post(target, json=body or {}, headers=team[who])
    return client.post(target, headers=team[who])


def history(detail: dict) -> list[tuple[str, str, str | None]]:
    return [(h["action"], h["actor"]["name"], h["comment"]) for h in detail["history"]]


def flags(detail: dict) -> set[str]:
    return {k for k in ("can_edit", "can_withdraw", "can_review", "can_unapprove", "can_reimburse", "can_unreimburse") if detail[k]}


# ---------- 상태 바꾸기 ----------


def test_submit_approve_reimburse_flow(client: TestClient, team: dict) -> None:
    expense = submitted(client, team)
    detail = lambda who: client.get(url(team, expense["id"]), headers=team[who]).json()  # noqa: E731

    # 제출되면 승인자도 봄
    assert [e["id"] for e in client.get(url(team), headers=team["approver"]).json()] == [expense["id"]]
    assert flags(detail("approver")) == {"can_review"}
    assert flags(detail("alice")) == {"can_withdraw"}
    assert flags(detail("owner")) == {"can_review", "can_withdraw"}

    approved = act(client, team, "approver", expense, "approve", {"comment": " 확인했어요 "}).json()
    assert approved["status"] == "APPROVED"
    assert flags(approved) == {"can_unapprove"}  # 승인자는 환급 처리 못 함
    assert flags(detail("owner")) == {"can_unapprove", "can_reimburse"}
    assert flags(detail("alice")) == set()

    done = act(client, team, "owner", expense, "reimburse").json()
    assert done["reimbursed_at"] is not None
    assert done["reimbursed_by"]["name"] == "총무"
    assert flags(done) == {"can_unreimburse"}  # 돌려준 뒤엔 승인 취소 불가
    assert history(done) == [("SUBMIT", "앨리스", None), ("APPROVE", "승인자", "확인했어요"), ("REIMBURSE", "총무", None)]
    assert client.get(url(team), headers=team["alice"]).json()[0]["reimbursed_at"] is not None

    # 같은 걸 두 번, 순서가 틀린 요청은 409
    assert act(client, team, "owner", expense, "reimburse").status_code == 409
    response = act(client, team, "approver", expense, "unapprove")
    assert response.status_code == 409
    assert "환급 완료를 먼저 취소" in response.json()["detail"]

    # 잘못 눌렀으면 되돌리기: 환급 취소 → 승인 취소 → 다시 승인 대기
    undone = act(client, team, "owner", expense, "unreimburse").json()
    assert undone["reimbursed_at"] is None and undone["reimbursed_by"] is None
    back = act(client, team, "approver", expense, "unapprove", {"comment": "금액 다시 확인"}).json()
    assert back["status"] == "SUBMITTED"
    assert [a for a, _, _ in history(back)] == ["SUBMIT", "APPROVE", "REIMBURSE", "UNREIMBURSE", "UNAPPROVE"]
    assert act(client, team, "owner", expense, "unreimburse").status_code == 409


def test_roles_for_review_and_reimbursement(client: TestClient, team: dict) -> None:
    expense = submitted(client, team)
    # 구성원은 승인·반려 불가 (내 지출이어도)
    assert act(client, team, "alice", expense, "approve").status_code == 403
    assert act(client, team, "alice", expense, "reject", {"reason": "x"}).status_code == 403
    assert act(client, team, "approver", expense, "approve").status_code == 200
    # 환급 처리는 총무만
    assert act(client, team, "approver", expense, "reimburse").status_code == 403
    assert act(client, team, "alice", expense, "reimburse").status_code == 403
    assert act(client, team, "approver", expense, "approve").status_code == 409  # 이미 승인됨

    # 총무는 자기 지출도 승인 가능 (기록은 남음)
    own = submitted(client, team, who="owner", payer="총무")
    approved = act(client, team, "owner", own, "approve").json()
    assert history(approved)[-1] == ("APPROVE", "총무", None)

    # 다른 조직 사람은 404
    outsider = signup(client, "outsider@example.com")
    create_org(client, outsider, "다른 동아리")
    assert client.post(url(team, expense["id"], "/approve"), json={}, headers=outsider).status_code == 404


def test_reject_then_fix_and_resubmit(client: TestClient, team: dict) -> None:
    expense = submitted(client, team)
    assert act(client, team, "approver", expense, "reject", {"reason": "   "}).status_code == 422  # 사유 필수
    rejected = act(client, team, "approver", expense, "reject", {"reason": "영수증 사진이 흐려요"}).json()
    assert rejected["status"] == "REJECTED"
    assert rejected["reject_reason"] == "영수증 사진이 흐려요"
    assert flags(rejected) == set()

    # 올린 사람이 고쳐서 다시 제출 (승인자는 못 고침)
    assert flags(client.get(url(team, expense["id"]), headers=team["alice"]).json()) == {"can_edit"}
    body = valid_body(team) | {"store_name": "행복마트 본점"}
    assert client.put(url(team, expense["id"]), json=body, headers=team["approver"]).status_code == 403
    assert client.put(url(team, expense["id"]), json=body, headers=team["alice"]).status_code == 200
    again = client.post(url(team, expense["id"], "/submit"), headers=team["alice"]).json()
    assert again["status"] == "SUBMITTED"
    assert again["reject_reason"] is None  # 사유는 기록에만
    assert history(again) == [
        ("SUBMIT", "앨리스", None),
        ("REJECT", "승인자", "영수증 사진이 흐려요"),
        ("SUBMIT", "앨리스", None),
    ]

    # 반려된 지출은 삭제도 가능
    other = submitted(client, team)
    act(client, team, "approver", other, "reject", {"reason": "중복"})
    assert client.delete(url(team, other["id"]), headers=team["alice"]).status_code == 204


def test_withdraw_before_review(client: TestClient, team: dict) -> None:
    expense = submitted(client, team)
    assert act(client, team, "approver", expense, "withdraw").status_code == 403  # 올린 사람·총무만
    assert act(client, team, "bob", expense, "withdraw").status_code == 404  # 못 보는 사람

    draft = act(client, team, "alice", expense, "withdraw").json()
    assert draft["status"] == "DRAFT"
    assert flags(draft) == {"can_edit"}
    assert history(draft)[-1] == ("WITHDRAW", "앨리스", None)
    # 작성 중으로 돌아가면 승인자에겐 다시 안 보임
    assert client.get(url(team, expense["id"]), headers=team["approver"]).status_code == 404

    client.post(url(team, expense["id"], "/submit"), headers=team["alice"])
    act(client, team, "approver", expense, "approve")
    assert act(client, team, "alice", expense, "withdraw").status_code == 409  # 승인된 뒤엔 취소 불가


# ---------- 정산 ----------


def settlement(client: TestClient, team: dict, who: str) -> dict:
    response = client.get(f"{ORGS}/{team['org_id']}/settlement", headers=team[who])
    assert response.status_code == 200, response.text
    return response.json()


def payer_rows(data: dict) -> list[tuple[str, int, list[int], int, int]]:
    return [
        (p["payer"]["name"], p["to_reimburse"], [e["id"] for e in p["expenses"]], p["awaiting_approval"], p["awaiting_count"])
        for p in data["payers"]
    ]


def test_settlement_by_payer_and_bulk_reimburse(client: TestClient, team: dict) -> None:
    e1, e2, e3 = submitted(client, team), submitted(client, team), submitted(client, team)
    e4 = submitted(client, team, who="bob", payer="밥")
    for expense in (e1, e2, e4):
        act(client, team, "approver", expense, "approve")

    org_view = settlement(client, team, "owner")
    assert org_view["scope"] == "org"
    assert (org_view["to_reimburse"], org_view["to_reimburse_count"]) == (26_700, 3)
    assert (org_view["awaiting_approval"], org_view["awaiting_count"]) == (8_900, 1)
    assert payer_rows(org_view) == [
        ("앨리스", 17_800, [e1["id"], e2["id"]], 8_900, 1),
        ("밥", 8_900, [e4["id"]], 0, 0),
    ]
    first = org_view["payers"][0]["expenses"][0]
    assert (first["store_name"], first["amount"]) == ("행복마트 테스트점", 8_900)
    assert org_view["me"]["to_reimburse"] == 0  # 총무 본인 몫
    assert settlement(client, team, "approver")["scope"] == "org"

    # 구성원은 내 몫만
    alice_view = settlement(client, team, "alice")
    assert alice_view["scope"] == "me"
    assert payer_rows(alice_view) == [("앨리스", 17_800, [e1["id"], e2["id"]], 8_900, 1)]
    assert (alice_view["to_reimburse"], alice_view["me"]["to_reimburse"]) == (17_800, 17_800)
    assert settlement(client, team, "bob")["me"]["to_reimburse"] == 8_900

    reimburse = f"{ORGS}/{team['org_id']}/settlement/reimburse"
    alice_id, bob_id = team["members"]["앨리스"], team["members"]["밥"]

    def bulk(who: str, payer: int, ids: list[int]):
        return client.post(reimburse, json={"payer_membership_id": payer, "expense_ids": ids}, headers=team[who])

    assert bulk("approver", alice_id, [e1["id"]]).status_code == 403
    # 화면에서 본 목록과 서버 상태가 다르면 하나도 안 바꿈
    assert bulk("owner", alice_id, [e1["id"], e4["id"]]).status_code == 409  # 다른 사람 지출 섞임
    assert bulk("owner", alice_id, [e1["id"], e3["id"]]).status_code == 409  # 아직 승인 대기
    assert bulk("owner", alice_id, [e1["id"], 999_999]).status_code == 409
    assert bulk("owner", alice_id, []).status_code == 422
    assert settlement(client, team, "owner")["to_reimburse"] == 26_700

    result = bulk("owner", alice_id, [e1["id"], e2["id"]])
    assert result.status_code == 200, result.text
    assert result.json() == {"count": 2, "amount": 17_800}
    after = settlement(client, team, "owner")
    assert payer_rows(after) == [("밥", 8_900, [e4["id"]], 0, 0), ("앨리스", 0, [], 8_900, 1)]
    assert bulk("owner", alice_id, [e1["id"]]).status_code == 409  # 이미 보냄
    detail = client.get(url(team, e1["id"]), headers=team["alice"]).json()
    assert detail["reimbursed_by"]["name"] == "총무"
    assert history(detail)[-1] == ("REIMBURSE", "총무", None)
    assert bulk("owner", bob_id, [e4["id"]]).json()["amount"] == 8_900


# ---------- 예산 기간·경고 ----------


def test_budget_usage_period_and_approval_warning(client: TestClient, team: dict) -> None:
    org_id, owner = team["org_id"], team["owner"]
    snack = team["category_ids"][1]
    client.patch(f"{ORGS}/{org_id}/categories/{snack}", json={"budget_amount": 3_000}, headers=owner)

    first = submitted(client, team)  # 간식 2,400 (결제일 2026-09-28)
    act(client, team, "approver", first, "approve")
    second = submitted(client, team)

    warnings = client.get(url(team, second["id"]), headers=team["approver"]).json()["budget_warnings"]
    assert warnings == [
        {"category_id": snack, "category_name": "간식·음료", "budget": 3_000, "spent": 2_400, "this_amount": 2_400, "over_by": 1_800}
    ]
    assert client.get(url(team, second["id"]), headers=team["alice"]).json()["budget_warnings"] == []  # 승인할 사람만

    usage = {c["category_id"]: c for c in settlement(client, team, "alice")["categories"]}  # 구성원도 예산은 봄
    assert {k: usage[snack][k] for k in ("budget", "spent", "awaiting", "remaining", "state")} == {
        "budget": 3_000,
        "spent": 2_400,
        "awaiting": 2_400,
        "remaining": 600,
        "state": "AT_RISK",
    }
    data = settlement(client, team, "owner")
    assert (data["period"], data["budget_total"], data["spent_total"], data["awaiting_total"]) == (None, 3_000, 8_900, 8_900)

    # 예산 기간: 총무만, 시작·끝 같이, 순서 확인
    target = f"{ORGS}/{org_id}"
    assert client.patch(target, json={"budget_period_start": "2026-10-01", "budget_period_end": "2026-12-31"}, headers=team["approver"]).status_code == 403
    assert client.patch(target, json={"budget_period_start": "2026-10-01"}, headers=owner).status_code == 422
    assert client.patch(target, json={"budget_period_start": "2026-12-31", "budget_period_end": "2026-10-01"}, headers=owner).status_code == 422
    updated = client.patch(target, json={"budget_period_start": "2026-10-01", "budget_period_end": "2026-12-31"}, headers=owner)
    assert updated.status_code == 200, updated.text
    assert (updated.json()["budget_period_start"], updated.json()["budget_period_end"]) == ("2026-10-01", "2026-12-31")
    assert client.get(target, headers=team["alice"]).json()["budget_period_start"] == "2026-10-01"

    # 9월 28일 결제는 기간 밖 → 집행액 0, 경고 없음. 돌려줄 돈은 기간과 상관없음
    data = settlement(client, team, "owner")
    assert data["period"] == {"start": "2026-10-01", "end": "2026-12-31"}
    assert {c["category_id"]: c["spent"] for c in data["categories"]}[snack] == 0
    assert data["to_reimburse"] == 8_900
    assert client.get(url(team, second["id"]), headers=team["approver"]).json()["budget_warnings"] == []

    # 이름만 바꾸면 기간은 그대로, 둘 다 null이면 기간 없음
    renamed = client.patch(target, json={"name": "컴공 학생회 2학기"}, headers=owner).json()
    assert (renamed["name"], renamed["budget_period_start"]) == ("컴공 학생회 2학기", "2026-10-01")
    cleared = client.patch(target, json={"budget_period_start": None, "budget_period_end": None}, headers=owner).json()
    assert cleared["budget_period_start"] is None
    assert settlement(client, team, "owner")["period"] is None
