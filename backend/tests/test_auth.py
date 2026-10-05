from fastapi.testclient import TestClient

from tests.conftest import signup

SIGNUP = "/api/v1/auth/signup"
LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"


def test_signup_returns_token_and_me_works(client: TestClient) -> None:
    response = client.post(SIGNUP, json={"email": "Kim@Example.com", "password": "password123", "name": " 김총무 "})
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "kim@example.com"  # 소문자로 정규화
    assert body["user"]["name"] == "김총무"  # 앞뒤 공백 제거

    me = client.get(ME, headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "kim@example.com"
    assert "password_hash" not in me.json()


def test_signup_duplicate_email_is_rejected_case_insensitively(client: TestClient) -> None:
    signup(client, "dup@example.com")
    response = client.post(SIGNUP, json={"email": "DUP@example.com", "password": "password123", "name": "x"})
    assert response.status_code == 409


def test_signup_validates_input(client: TestClient) -> None:
    assert client.post(SIGNUP, json={"email": "a@example.com", "password": "short", "name": "x"}).status_code == 422
    assert client.post(SIGNUP, json={"email": "not-an-email", "password": "password123", "name": "x"}).status_code == 422
    assert client.post(SIGNUP, json={"email": "b@example.com", "password": "password123", "name": "  "}).status_code == 422


def test_login(client: TestClient) -> None:
    signup(client, "login@example.com", password="correct-horse")

    ok = client.post(LOGIN, json={"email": "LOGIN@example.com", "password": "correct-horse"})
    assert ok.status_code == 200
    assert client.get(ME, headers={"Authorization": f"Bearer {ok.json()['access_token']}"}).status_code == 200

    wrong_password = client.post(LOGIN, json={"email": "login@example.com", "password": "wrong-password"})
    unknown_email = client.post(LOGIN, json={"email": "nobody@example.com", "password": "correct-horse"})
    assert wrong_password.status_code == unknown_email.status_code == 401
    # 어느 쪽이 틀렸는지 구분해서 알려주지 않음
    assert wrong_password.json()["detail"] == unknown_email.json()["detail"]


def test_me_requires_valid_token(client: TestClient) -> None:
    assert client.get(ME).status_code == 401
    assert client.get(ME, headers={"Authorization": "Bearer not-a-token"}).status_code == 401
