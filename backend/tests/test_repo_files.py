"""한국어 Windows에서만 터지는 문제 방지.

아래 파일들은 Alembic·pip 같은 도구가 UTF-8이 아니라 OS 기본 인코딩(한국어 Windows는 cp949)으로 읽는다.
한글 주석이 하나라도 들어가면 Windows 팀원 PC에서 `npm run setup`이 UnicodeDecodeError로 실패한다.
(Mac/Linux는 OS 인코딩이 UTF-8이라 문제가 안 보이므로 테스트로 막아둔다)
"""

import pytest

from app.core.config import BACKEND_DIR

ASCII_ONLY_FILES = [
    "alembic.ini",
    "requirements.txt",
    "requirements-dev.txt",
    "app/db/migrations/script.py.mako",
]


@pytest.mark.parametrize("relative_path", ASCII_ONLY_FILES)
def test_file_is_ascii_only(relative_path: str) -> None:
    text = (BACKEND_DIR / relative_path).read_text(encoding="utf-8")
    bad_lines = [f"{no}: {line.strip()}" for no, line in enumerate(text.splitlines(), 1) if not line.isascii()]
    assert not bad_lines, f"{relative_path}에 한글 등 비ASCII 문자가 있음 (Windows에서 깨짐, 주석은 영어로):\n" + "\n".join(
        bad_lines
    )
