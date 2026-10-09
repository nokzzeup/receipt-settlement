"""6단계: 중복 영수증 감지 — 같은 파일 / 비슷한 사진(지문) / 가게·일시·합계 같음"""

import io

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.receipts.fingerprint import SIMILAR_MAX_DISTANCE, hamming_distance, perceptual_hash
from tests.conftest import upload_receipt, url, valid_body


def receipt_photo(seed: int, quality: int = 90, scale: float = 1.0) -> bytes:
    """줄 무늬가 다른 가짜 영수증 사진 (seed가 같으면 같은 그림)"""
    image = Image.new("RGB", (600, 900), (70, 60, 50))
    draw = ImageDraw.Draw(image)
    draw.rectangle((60, 40, 540, 860), fill=(245, 245, 240))
    for line in range(24):
        width = 80 + (seed * 37 + line * 53) % 380
        top = 70 + line * 32
        draw.rectangle((90, top, 90 + width, top + 12), fill=(40, 40, 40))
    if scale != 1.0:
        image = image.resize((int(600 * scale), int(900 * scale)))
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=quality)
    return buffer.getvalue()


def test_fingerprint_matches_resaved_photo_only() -> None:
    original = perceptual_hash(receipt_photo(1))
    resaved = perceptual_hash(receipt_photo(1, quality=35, scale=0.5))
    other = perceptual_hash(receipt_photo(2))
    assert original and resaved and other and len(original) == 64
    assert hamming_distance(original, resaved) <= SIMILAR_MAX_DISTANCE
    assert hamming_distance(original, other) > SIMILAR_MAX_DISTANCE * 2
    assert perceptual_hash(b"\xff\xd8\xff\xe0 not really a jpeg") is None


def duplicates(client: TestClient, team: dict, who: str, expense_id: int) -> list[tuple[int | None, str, str]]:
    detail = client.get(url(team, expense_id), headers=team[who]).json()
    return [(d["expense_id"], d["reason"], d["uploader_name"]) for d in detail["duplicates"]]


def test_same_file_and_similar_photo(client: TestClient, team: dict) -> None:
    org = team["org_id"]
    first = upload_receipt(client, team["alice"], org, receipt_photo(1)).json()
    assert first["duplicates"] == []

    # 같은 파일을 또 올림 → 바로 경고 (업로드 응답에도)
    again = upload_receipt(client, team["alice"], org, receipt_photo(1)).json()
    assert [(d["expense_id"], d["reason"]) for d in again["duplicates"]] == [(first["id"], "SAME_IMAGE")]
    assert again["duplicates"][0]["store_name"] == "행복마트 테스트점"

    # 메신저로 받아 다시 저장된 사진 (파일은 다름) → 비슷한 사진. 밥은 앨리스 지출을 못 보므로 링크(id) 없음
    resaved = upload_receipt(client, team["bob"], org, receipt_photo(1, quality=40, scale=0.6)).json()
    found = {(d["expense_id"], d["reason"], d["uploader_name"]) for d in resaved["duplicates"]}
    assert found == {(None, "SIMILAR_IMAGE", "앨리스")}

    # 앨리스 쪽에서도 밥의 것이 보임 (볼 수는 없으니 id 없음), 총무는 링크까지
    assert (None, "SIMILAR_IMAGE", "밥") in duplicates(client, team, "alice", first["id"])
    assert (resaved["id"], "SIMILAR_IMAGE", "밥") in duplicates(client, team, "owner", first["id"])


def test_same_details_from_another_photo(client: TestClient, team: dict) -> None:
    org = team["org_id"]
    # Mock OCR은 사진과 상관없이 같은 가게·일시·합계를 읽음 → 다른 사진이어도 '내용 같음'
    first = upload_receipt(client, team["alice"], org, receipt_photo(1)).json()
    second = upload_receipt(client, team["alice"], org, receipt_photo(2)).json()
    assert [(d["expense_id"], d["reason"]) for d in second["duplicates"]] == [(first["id"], "SAME_DETAILS")]

    # 띄어쓰기·초 단위가 달라도 같은 것으로 봄
    body = valid_body(team) | {"store_name": "행복마트  테스트 점", "paid_at": "2026-09-28T14:32:00+09:00", "total_amount": 25400}
    client.put(url(team, second["id"]), json=body, headers=team["alice"])
    assert duplicates(client, team, "alice", second["id"]) == [(first["id"], "SAME_DETAILS", "앨리스")]

    # 결제 시각(분)이나 합계가 다르면 아님
    client.put(url(team, second["id"]), json=body | {"paid_at": "2026-09-28T14:33:00+09:00"}, headers=team["alice"])
    assert duplicates(client, team, "alice", second["id"]) == []
    client.put(url(team, second["id"]), json=body | {"total_amount": 25300}, headers=team["alice"])
    assert duplicates(client, team, "alice", second["id"]) == []


def test_other_orgs_are_not_compared(client: TestClient, team: dict) -> None:
    from tests.conftest import create_org, signup

    upload_receipt(client, team["alice"], team["org_id"], receipt_photo(1))
    outsider = signup(client, "outsider@example.com")
    other = create_org(client, outsider, "다른 동아리")
    mine = upload_receipt(client, outsider, other["id"], receipt_photo(1)).json()
    assert mine["duplicates"] == []
