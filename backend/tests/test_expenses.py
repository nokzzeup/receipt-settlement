from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1 import expenses as expenses_api
from app.main import app
from app.models import ApprovalLog, Expense, Receipt
from app.ocr import OcrEngine, OcrRawResult, get_ocr_engine
from tests.conftest import FAKE_JPEG, ORGS, create_org, join_org, signup, upload_receipt


class FailingOcrEngine(OcrEngine):
    name = "broken"

    def recognize(self, image_bytes: bytes) -> OcrRawResult:
        raise RuntimeError("모델 로딩 실패")


@pytest.fixture
def team(client: TestClient) -> dict:
    """총무 / 승인자 / 구성원 2명 + 조직"""
    owner = signup(client, "owner@example.com", "총무")
    approver = signup(client, "approver@example.com", "승인자")
    alice = signup(client, "alice@example.com", "앨리스")
    bob = signup(client, "bob@example.com", "밥")
    org = create_org(client, owner)
    for headers in (approver, alice, bob):
        join_org(client, headers, org["invite_code"])
    members = {m["name"]: m for m in client.get(f"{ORGS}/{org['id']}/members", headers=owner).json()}
    client.patch(
        f"{ORGS}/{org['id']}/members/{members['승인자']['membership_id']}", json={"role": "APPROVER"}, headers=owner
    )
    categories = client.get(f"{ORGS}/{org['id']}/categories", headers=owner).json()
    return {
        "org_id": org["id"],
        "owner": owner,
        "approver": approver,
        "alice": alice,
        "bob": bob,
        "members": {name: m["membership_id"] for name, m in members.items()},
        "category_ids": [c["id"] for c in categories],
    }


def url(team: dict, expense_id: int | None = None, suffix: str = "") -> str:
    base = f"{ORGS}/{team['org_id']}/expenses"
    return base if expense_id is None else f"{base}/{expense_id}{suffix}"


def valid_body(team: dict, payer: str = "앨리스") -> dict:
    snack, office = team["category_ids"][1], team["category_ids"][2]
    return {
        "store_name": "행복마트 테스트점",
        "paid_at": "2026-09-28T14:32:00+09:00",
        "total_amount": 25400,
        "payer_membership_id": team["members"][payer],
        "items": [
            {"name": "생수 2L", "quantity": 2, "unit_price": 1200, "amount": 2400, "category_id": snack},
            {"name": "A4용지", "quantity": 1, "unit_price": 6500, "amount": 6500, "category_id": office},
        ],
    }


# ---------- 업로드 ----------


def test_upload_creates_draft_from_ocr(client: TestClient, team: dict, storage_dir: Path, db_session: Session) -> None:
    response = upload_receipt(client, team["alice"], team["org_id"])
    assert response.status_code == 201, response.text
    expense = response.json()

    assert expense["status"] == "DRAFT"
    assert expense["can_edit"] is True
    assert expense["payer"] == {"membership_id": team["members"]["앨리스"], "name": "앨리스"}
    assert expense["uploader"]["name"] == "앨리스"
    receipt = expense["receipt"]
    assert receipt["store_name"] == "행복마트 테스트점"
    assert receipt["paid_at"] == "2026-09-28T05:32:05Z"  # 저장·응답은 UTC, 화면에서 한국시간으로
    assert receipt["total_amount"] == 25400
    assert receipt["ocr_failed"] is False
    assert [i["name"] for i in expense["items"]] == ["생수 2L", "A4용지 500매", "종이컵 50입", "과자 세트"]
    assert all(i["category_id"] is None for i in expense["items"])
    assert expense["amount"] == 25400

    # 카드번호는 응답에도 DB에도 마스킹된 상태로만
    assert "카드번호 ****-****-****-3456" in receipt["ocr_text"]
    stored = db_session.get(Receipt, receipt["id"])
    assert "9410" not in str(stored.ocr_raw)
    assert len(stored.image_hash) == 64

    # 원본 이미지는 storage/receipts/{조직 id}/ 아래에
    saved = list((storage_dir / "receipts" / str(team["org_id"])).iterdir())
    assert len(saved) == 1
    assert saved[0].read_bytes() == FAKE_JPEG
    assert stored.image_path == f"receipts/{team['org_id']}/{saved[0].name}"


def test_upload_rejects_bad_files(client: TestClient, team: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    alice, org_id = team["alice"], team["org_id"]

    assert upload_receipt(client, alice, org_id, b"").status_code == 400
    assert upload_receipt(client, alice, org_id, b"GIF89a" + b"\x00" * 20, "a.gif").status_code == 415
    heic = b"\x00\x00\x00\x18ftypheic" + b"\x00" * 20
    response = upload_receipt(client, alice, org_id, heic, "IMG_0001.HEIC")
    assert response.status_code == 415
    assert "HEIC" in response.json()["detail"]

    monkeypatch.setattr(expenses_api, "MAX_UPLOAD_BYTES", 100)
    assert upload_receipt(client, alice, org_id, FAKE_JPEG + b"\x00" * 100).status_code == 413

    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
    assert upload_receipt(client, alice, org_id, png, "a.png").status_code == 201

    outsider = signup(client, "outsider@example.com")
    assert upload_receipt(client, outsider, org_id).status_code == 404


def test_upload_still_works_when_ocr_fails(client: TestClient, team: dict) -> None:
    app.dependency_overrides[get_ocr_engine] = FailingOcrEngine
    response = upload_receipt(client, team["alice"], team["org_id"])

    assert response.status_code == 201
    expense = response.json()
    assert expense["receipt"]["ocr_failed"] is True
    assert expense["receipt"]["ocr_text"] == []
    assert expense["items"] == []
    assert expense["amount"] == 0


# ---------- 보기 권한 ----------


def test_members_see_only_their_own_expenses(client: TestClient, team: dict) -> None:
    expense = upload_receipt(client, team["alice"], team["org_id"]).json()

    for who in ("alice", "owner", "approver"):
        assert client.get(url(team, expense["id"]), headers=team[who]).status_code == 200
        assert [e["id"] for e in client.get(url(team), headers=team[who]).json()] == [expense["id"]]

    # 다른 구성원은 남의 지출을 못 봄 (있는지도 모르게 404)
    assert client.get(url(team, expense["id"]), headers=team["bob"]).status_code == 404
    assert client.get(url(team, expense["id"], "/image"), headers=team["bob"]).status_code == 404
    assert client.get(url(team), headers=team["bob"]).json() == []

    # 결제자로 지정되면 볼 수 있음
    client.put(url(team, expense["id"]), json=valid_body(team, payer="밥"), headers=team["alice"])
    assert client.get(url(team, expense["id"]), headers=team["bob"]).status_code == 200
    summary = client.get(url(team), headers=team["bob"]).json()[0]
    assert summary["payer"]["name"] == "밥"
    assert summary["amount"] == 8900
    assert summary["item_count"] == 2
    assert summary["uncategorized_count"] == 0

    outsider = signup(client, "outsider@example.com")
    assert client.get(url(team), headers=outsider).status_code == 404


def test_receipt_image_download(client: TestClient, team: dict) -> None:
    expense = upload_receipt(client, team["alice"], team["org_id"]).json()

    response = client.get(url(team, expense["id"], "/image"), headers=team["approver"])
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == FAKE_JPEG


# ---------- 저장 ----------


def test_update_replaces_fields_and_items(client: TestClient, team: dict) -> None:
    expense = upload_receipt(client, team["alice"], team["org_id"]).json()
    body = valid_body(team, payer="밥")
    body["store_name"] = "  "  # 빈 값은 null로

    response = client.put(url(team, expense["id"]), json=body, headers=team["alice"])
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["receipt"]["store_name"] is None
    assert updated["receipt"]["paid_at"] == "2026-09-28T05:32:00Z"
    assert updated["payer"]["name"] == "밥"
    assert [(i["name"], i["amount"], i["category_source"]) for i in updated["items"]] == [
        ("생수 2L", 2400, "MANUAL"),
        ("A4용지", 6500, "MANUAL"),
    ]
    assert updated["amount"] == 8900
    assert datetime.fromisoformat(updated["updated_at"]) >= datetime.fromisoformat(expense["updated_at"])

    # 미분류로 되돌리면 category_source도 null
    body["items"][0]["category_id"] = None
    again = client.put(url(team, expense["id"]), json=body, headers=team["alice"]).json()
    assert again["items"][0]["category_source"] is None


def test_update_validates_values(client: TestClient, team: dict) -> None:
    expense = upload_receipt(client, team["alice"], team["org_id"]).json()
    target = url(team, expense["id"])

    def put(**changes: object) -> int:
        body = valid_body(team) | changes
        return client.put(target, json=body, headers=team["alice"]).status_code

    assert put(total_amount=25400.5) == 422  # 금액은 int만
    assert put(total_amount=-1) == 422
    assert put(paid_at="2026-09-28T14:32:00") == 422  # 시간대 없는 시각
    assert put(items=[{"name": "", "amount": 100}]) == 422
    assert put(items=[{"name": "물", "quantity": 0, "amount": 100}]) == 422
    assert put(items=[{"name": "할인", "amount": -500}]) == 200  # 할인 줄은 음수 가능

    # 다른 조직의 구성원·계정과목은 못 씀
    outsider = signup(client, "outsider@example.com")
    other_org = create_org(client, outsider, "다른 동아리")
    other_members = client.get(f"{ORGS}/{other_org['id']}/members", headers=outsider).json()
    other_category = client.get(f"{ORGS}/{other_org['id']}/categories", headers=outsider).json()[0]
    assert put(payer_membership_id=other_members[0]["membership_id"]) == 422
    assert put(items=[{"name": "물", "amount": 100, "category_id": other_category["id"]}]) == 422


def test_only_uploader_or_treasurer_can_edit_drafts(client: TestClient, team: dict) -> None:
    expense = upload_receipt(client, team["alice"], team["org_id"]).json()
    body = valid_body(team)

    # 승인자는 볼 수는 있지만 남의 작성 중 지출은 못 고침
    detail = client.get(url(team, expense["id"]), headers=team["approver"]).json()
    assert detail["can_edit"] is False
    assert client.put(url(team, expense["id"]), json=body, headers=team["approver"]).status_code == 403
    assert client.get(url(team, expense["id"]), headers=team["owner"]).json()["can_edit"] is True
    assert client.put(url(team, expense["id"]), json=body, headers=team["owner"]).status_code == 200


# ---------- 제출 ----------


def test_submit_lists_what_is_missing(client: TestClient, team: dict) -> None:
    expense = upload_receipt(client, team["alice"], team["org_id"]).json()
    submit = url(team, expense["id"], "/submit")

    # 업로드 직후: 품목 계정과목이 비어 있음
    response = client.post(submit, headers=team["alice"])
    assert response.status_code == 422
    assert "계정과목을 정하지 않은 품목이 4개" in response.json()["detail"]

    body = valid_body(team)
    body |= {"store_name": None, "paid_at": None, "total_amount": 1000}
    client.put(url(team, expense["id"]), json=body, headers=team["alice"])
    detail = client.post(submit, headers=team["alice"]).json()["detail"]
    assert "가게명·결제일시" in detail
    assert "청구 금액(8,900원)이 영수증 합계(1,000원)보다 큽니다." in detail


def test_submit_then_locked(client: TestClient, team: dict, db_session: Session) -> None:
    expense = upload_receipt(client, team["alice"], team["org_id"]).json()
    client.put(url(team, expense["id"]), json=valid_body(team), headers=team["alice"])

    response = client.post(url(team, expense["id"], "/submit"), headers=team["alice"])
    assert response.status_code == 200, response.text
    submitted = response.json()
    assert submitted["status"] == "SUBMITTED"
    assert submitted["can_edit"] is False

    logs = db_session.scalars(select(ApprovalLog).where(ApprovalLog.expense_id == expense["id"])).all()
    assert [(log.action, log.actor_membership_id) for log in logs] == [("SUBMIT", team["members"]["앨리스"])]

    # 제출하면 수정·삭제·재제출 불가
    assert client.put(url(team, expense["id"]), json=valid_body(team), headers=team["alice"]).status_code == 409
    assert client.delete(url(team, expense["id"]), headers=team["alice"]).status_code == 409
    assert client.post(url(team, expense["id"], "/submit"), headers=team["alice"]).status_code == 409


# ---------- 삭제 ----------


def test_delete_draft_removes_receipt_and_image(
    client: TestClient, team: dict, storage_dir: Path, db_session: Session
) -> None:
    expense = upload_receipt(client, team["alice"], team["org_id"]).json()
    client.put(url(team, expense["id"]), json=valid_body(team), headers=team["alice"])
    folder = storage_dir / "receipts" / str(team["org_id"])
    assert len(list(folder.iterdir())) == 1

    assert client.delete(url(team, expense["id"]), headers=team["bob"]).status_code == 404  # 못 보는 사람
    assert client.delete(url(team, expense["id"]), headers=team["approver"]).status_code == 403
    assert client.delete(url(team, expense["id"]), headers=team["alice"]).status_code == 204

    assert client.get(url(team, expense["id"]), headers=team["alice"]).status_code == 404
    assert db_session.get(Expense, expense["id"]) is None
    assert db_session.get(Receipt, expense["receipt"]["id"]) is None
    assert list(folder.iterdir()) == []
