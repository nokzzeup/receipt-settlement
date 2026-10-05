from fastapi.testclient import TestClient

from tests.conftest import signup

ORGS = "/api/v1/orgs"


def create_org(client: TestClient, headers: dict[str, str], name: str = "컴공 학생회") -> dict:
    response = client.post(ORGS, json={"name": name}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def join(client: TestClient, headers: dict[str, str], code: str):
    return client.post(f"{ORGS}/join", json={"invite_code": code}, headers=headers)


def test_create_org_makes_creator_treasurer(client: TestClient) -> None:
    owner = signup(client, "owner@example.com", "총무")
    org = create_org(client, owner)

    assert org["my_role"] == "TREASURER"
    assert len(org["invite_code"]) == 8

    orgs = client.get(ORGS, headers=owner).json()
    assert orgs == [{"id": org["id"], "name": "컴공 학생회", "my_role": "TREASURER", "member_count": 1}]


def test_join_with_invite_code(client: TestClient) -> None:
    owner = signup(client, "owner@example.com", "총무")
    member = signup(client, "member@example.com", "회원")
    org = create_org(client, owner)
    code = org["invite_code"]

    # 소문자·하이픈·공백이 섞여도 참여됨
    response = join(client, member, f" {code[:4].lower()}-{code[4:]} ")
    assert response.status_code == 200
    joined = response.json()
    assert joined["my_role"] == "MEMBER"
    assert joined["invite_code"] is None  # 총무가 아니면 초대 코드를 못 봄

    assert join(client, member, code).status_code == 409  # 이미 참여
    assert join(client, member, "WRONG123").status_code == 404

    members = client.get(f"{ORGS}/{org['id']}/members", headers=member).json()
    assert [(m["name"], m["role"]) for m in members] == [("총무", "TREASURER"), ("회원", "MEMBER")]
    assert client.get(ORGS, headers=owner).json()[0]["member_count"] == 2


def test_non_member_cannot_see_org(client: TestClient) -> None:
    owner = signup(client, "owner@example.com")
    outsider = signup(client, "outsider@example.com")
    org = create_org(client, owner)

    # 구성원이 아니면 조직이 있는지도 알 수 없게 404
    assert client.get(f"{ORGS}/{org['id']}", headers=outsider).status_code == 404
    assert client.get(f"{ORGS}/{org['id']}/members", headers=outsider).status_code == 404
    assert client.post(f"{ORGS}/{org['id']}/invite-code", headers=outsider).status_code == 404
    assert client.get(ORGS, headers=outsider).json() == []
    # 로그인 안 하면 401
    assert client.get(f"{ORGS}/{org['id']}").status_code == 401


def test_only_treasurer_can_regenerate_invite_code(client: TestClient) -> None:
    owner = signup(client, "owner@example.com")
    member = signup(client, "member@example.com")
    late = signup(client, "late@example.com")
    org = create_org(client, owner)
    old_code = org["invite_code"]
    join(client, member, old_code)

    assert client.post(f"{ORGS}/{org['id']}/invite-code", headers=member).status_code == 403

    response = client.post(f"{ORGS}/{org['id']}/invite-code", headers=owner)
    assert response.status_code == 200
    new_code = response.json()["invite_code"]
    assert new_code != old_code
    assert join(client, late, old_code).status_code == 404  # 이전 코드는 바로 무효
    assert join(client, late, new_code).status_code == 200


def test_role_change_rules(client: TestClient) -> None:
    owner = signup(client, "owner@example.com", "총무")
    member = signup(client, "member@example.com", "회원")
    org = create_org(client, owner)
    join(client, member, org["invite_code"])
    members = {m["name"]: m for m in client.get(f"{ORGS}/{org['id']}/members", headers=owner).json()}
    owner_mid = members["총무"]["membership_id"]
    member_mid = members["회원"]["membership_id"]
    url = f"{ORGS}/{org['id']}/members"

    # 구성원은 역할을 못 바꿈
    assert client.patch(f"{url}/{member_mid}", json={"role": "TREASURER"}, headers=member).status_code == 403
    # 마지막 총무는 내려갈 수 없음
    assert client.patch(f"{url}/{owner_mid}", json={"role": "MEMBER"}, headers=owner).status_code == 409
    # 총무가 다른 사람을 승인자로
    response = client.patch(f"{url}/{member_mid}", json={"role": "APPROVER"}, headers=owner)
    assert response.status_code == 200 and response.json()["role"] == "APPROVER"
    # 총무를 넘기고 나면 원래 총무는 내려갈 수 있음
    assert client.patch(f"{url}/{member_mid}", json={"role": "TREASURER"}, headers=owner).status_code == 200
    assert client.patch(f"{url}/{owner_mid}", json={"role": "MEMBER"}, headers=owner).status_code == 200
    # 이제 원래 총무는 권한이 없음
    assert client.post(f"{ORGS}/{org['id']}/invite-code", headers=owner).status_code == 403
    assert client.get(f"{ORGS}/{org['id']}", headers=member).json()["invite_code"] is not None
    # 없는 역할 값은 거부
    assert client.patch(f"{url}/{owner_mid}", json={"role": "ADMIN"}, headers=member).status_code == 422


def test_cannot_touch_member_of_another_org(client: TestClient) -> None:
    a = signup(client, "a@example.com")
    b = signup(client, "b@example.com")
    org_a = create_org(client, a, "A 동아리")
    org_b = create_org(client, b, "B 동아리")
    b_mid = client.get(f"{ORGS}/{org_b['id']}/members", headers=b).json()[0]["membership_id"]

    # A의 총무가 자기 조직 경로로 B 조직 구성원을 바꾸려 해도 404
    response = client.patch(f"{ORGS}/{org_a['id']}/members/{b_mid}", json={"role": "MEMBER"}, headers=a)
    assert response.status_code == 404
