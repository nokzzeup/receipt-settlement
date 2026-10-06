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


def test_login_is_throttled_after_repeated_failures(client: TestClient) -> None:
    signup(client, "victim@example.com", password="correct-horse")
    wrong = {"email": "victim@example.com", "password": "wrong-password"}

    for _ in range(10):
        assert client.post(LOGIN, json=wrong).status_code == 401
    # 10번 틀린 뒤에는 맞는 비밀번호여도 잠시 차단
    blocked = client.post(LOGIN, json={"email": "victim@example.com", "password": "correct-horse"})
    assert blocked.status_code == 429
    assert "분 뒤에 다시 시도" in blocked.json()["detail"]
    assert int(blocked.headers["retry-after"]) > 0

    # 다른 계정은 이 IP의 전체 한도(30번) 전까지는 영향 없음
    signup(client, "other@example.com", password="correct-horse")
    assert client.post(LOGIN, json={"email": "other@example.com", "password": "correct-horse"}).status_code == 200


def test_failure_limiter_window_and_clear() -> None:
    from app.core.ratelimit import FailureLimiter

    limiter = FailureLimiter(limit=2, window_seconds=60)
    limiter.record("k", now=0)
    assert limiter.retry_after("k", now=1) == 0
    limiter.record("k", now=10)
    assert limiter.retry_after("k", now=20) == 40  # 첫 실패(0초)가 60초 창에서 빠질 때까지
    assert limiter.retry_after("k", now=61) == 0  # 시간이 지나면 풀림
    limiter.record("k", now=62)
    limiter.record("k", now=63)
    limiter.clear("k")  # 로그인 성공
    assert limiter.retry_after("k", now=64) == 0
