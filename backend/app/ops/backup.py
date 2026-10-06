"""운영 DB 백업. 서버 모드(npm run serve)가 켜질 때마다 DB 구조 업데이트 전에 자동으로 실행된다.

    python -m app.ops.backup     # 지금 설정의 SQLite DB → {data_dir}/backups/app-날짜-시각.db

- 파일을 그냥 복사하지 않고 SQLite 백업 기능을 쓴다 → WAL 파일에 남아 있던 최근 저장분까지 빠짐없이 들어간 사본
- 최근 10개만 남기고 오래된 것부터 지운다
- 영수증 사진(storage)은 포함하지 않는다 (지워지는 일이 거의 없음) → 사진까지 보관하려면 서버를 끄고 폴더째 복사
- 되돌리기: 서버를 끄고 백업 파일을 {data_dir}/app.db 로 덮어쓴 뒤 다시 켜기
"""

import sqlite3
import sys
from contextlib import closing
from datetime import datetime
from pathlib import Path

from sqlalchemy import make_url

from app.core.config import settings
from app.core.timezone import KST

KEEP = 10


def backup_sqlite(db_file: Path, backup_dir: Path, keep: int = KEEP) -> Path | None:
    """백업 파일 경로. DB 파일이 아직 없으면(첫 실행) None"""
    if not db_file.is_file():
        return None
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / f"app-{datetime.now(KST):%Y%m%d-%H%M%S}.db"
    with closing(sqlite3.connect(db_file)) as source, closing(sqlite3.connect(target)) as copy:
        source.backup(copy)
    for old in sorted(backup_dir.glob("app-*.db"))[:-keep]:
        old.unlink()
    return target


def main() -> int:
    url = make_url(settings.database_url)
    if url.get_backend_name() != "sqlite" or not url.database:
        print("SQLite가 아니라서 자동 백업은 건너뜁니다 (DB 자체 백업 기능을 쓰세요)")
        return 0
    target = backup_sqlite(Path(url.database), settings.data_path / "backups")
    print(f"DB 백업: {target}" if target else "DB 백업: 아직 DB가 없어서 건너뜀 (첫 실행)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
