from fastapi.testclient import TestClient

from app.classify.defaults import DEFAULT_CATEGORY_NAMES
from tests.conftest import ORGS, create_org, join_org, signup, upload_receipt


def categories_url(org_id: int) -> str:
    return f"{ORGS}/{org_id}/categories"


def test_new_org_gets_default_categories(client: TestClient) -> None:
    owner = signup(client, "owner@example.com")
    member = signup(client, "member@example.com")
    org = create_org(client, owner)
    join_org(client, member, org["invite_code"])

    # 구성원도 목록은 볼 수 있음 (품목 계정과목 고를 때 필요)
    response = client.get(categories_url(org["id"]), headers=member)
    assert response.status_code == 200
    assert [c["name"] for c in response.json()] == list(DEFAULT_CATEGORY_NAMES)
    assert all(c["budget_amount"] is None for c in response.json())


def test_treasurer_manages_categories(client: TestClient) -> None:
    owner = signup(client, "owner@example.com")
    org = create_org(client, owner)
    url = categories_url(org["id"])

    created = client.post(url, json={"name": "  행사비 ", "budget_amount": 300000}, headers=owner)
    assert created.status_code == 201
    category = created.json()
    assert category["name"] == "행사비"
    assert category["budget_amount"] == 300000

    # 같은 이름은 중복 불가
    assert client.post(url, json={"name": "행사비"}, headers=owner).status_code == 409
    assert client.patch(f"{url}/{category['id']}", json={"name": "식비"}, headers=owner).status_code == 409

    # 보낸 필드만 바뀜 / null 이면 예산 해제
    renamed = client.patch(f"{url}/{category['id']}", json={"name": "행사·회의비"}, headers=owner).json()
    assert renamed == {"id": category["id"], "name": "행사·회의비", "budget_amount": 300000}
    cleared = client.patch(f"{url}/{category['id']}", json={"budget_amount": None}, headers=owner).json()
    assert cleared["budget_amount"] is None

    # 금액은 0 이상 정수만
    for bad in (1000.5, "1000", -1):
        assert client.post(url, json={"name": f"x{bad}", "budget_amount": bad}, headers=owner).status_code == 422

    assert client.delete(f"{url}/{category['id']}", headers=owner).status_code == 204
    assert "행사·회의비" not in [c["name"] for c in client.get(url, headers=owner).json()]


def test_only_treasurer_can_change_categories(client: TestClient) -> None:
    owner = signup(client, "owner@example.com")
    member = signup(client, "member@example.com")
    outsider = signup(client, "outsider@example.com")
    org = create_org(client, owner)
    join_org(client, member, org["invite_code"])
    url = categories_url(org["id"])
    first_id = client.get(url, headers=owner).json()[0]["id"]

    assert client.post(url, json={"name": "새 항목"}, headers=member).status_code == 403
    assert client.patch(f"{url}/{first_id}", json={"name": "바꿈"}, headers=member).status_code == 403
    assert client.delete(f"{url}/{first_id}", headers=member).status_code == 403
    assert client.get(url, headers=outsider).status_code == 404

    # 다른 조직의 계정과목 id로는 접근 불가
    other_org = create_org(client, outsider, "다른 동아리")
    other_id = client.get(categories_url(other_org["id"]), headers=outsider).json()[0]["id"]
    assert client.patch(f"{url}/{other_id}", json={"name": "탈취"}, headers=owner).status_code == 404
    assert client.delete(f"{url}/{other_id}", headers=owner).status_code == 404


def test_category_in_use_cannot_be_deleted(client: TestClient) -> None:
    owner = signup(client, "owner@example.com")
    org = create_org(client, owner)
    url = categories_url(org["id"])
    category_id = client.get(url, headers=owner).json()[0]["id"]

    expense = upload_receipt(client, owner, org["id"]).json()
    body = {
        "store_name": "가게",
        "payer_membership_id": expense["payer"]["membership_id"],
        "items": [{"name": "도시락", "amount": 5000, "category_id": category_id}],
    }
    assert client.put(f"{ORGS}/{org['id']}/expenses/{expense['id']}", json=body, headers=owner).status_code == 200

    response = client.delete(f"{url}/{category_id}", headers=owner)
    assert response.status_code == 409
    assert "이름을 바꿔서" in response.json()["detail"]
