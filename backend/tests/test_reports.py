"""6단계: 기간별 리포트 계산·API·엑셀 파일"""

from datetime import UTC, date, datetime
from io import BytesIO
from urllib.parse import unquote

from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app.core.timezone import KST
from app.models.enums import ExpenseStatus
from app.reports import ReportExpense, ReportItem, summarize
from tests.conftest import ORGS, upload_receipt, url, valid_body

FOOD, SNACK = 1, 2
SEP, OCT = date(2026, 9, 1), date(2026, 9, 30)


def expense(
    id: int,
    payer: int = 10,
    status: ExpenseStatus = ExpenseStatus.APPROVED,
    paid_at: datetime | None = datetime(2026, 9, 15, 12, 0, tzinfo=KST),
    reimbursed: bool = False,
    items: tuple[tuple[int | None, int], ...] = ((FOOD, 10_000),),
) -> ReportExpense:
    return ReportExpense(
        id=id,
        status=status,
        store_name=f"가게{id}",
        paid_at=paid_at,
        payer_id=payer,
        payer_name=f"사람{payer}",
        uploader_name="올린이",
        approved_at=None,
        reimbursed_at=datetime(2026, 10, 1, tzinfo=UTC) if reimbursed else None,
        items=tuple(ReportItem(name="품목", quantity=1, unit_price=None, amount=a, category_id=c) for c, a in items),
    )


def test_summarize_counts_approved_in_period_only() -> None:
    expenses = [
        expense(1, payer=10, items=((FOOD, 10_000), (SNACK, 3_000))),
        expense(2, payer=10, reimbursed=True, items=((FOOD, 5_000), (FOOD, -500))),
        expense(3, payer=20, items=((SNACK, 7_000),)),
        expense(4, payer=20, status=ExpenseStatus.SUBMITTED, items=((FOOD, 9_999),)),  # 대기 → 따로
        expense(5, payer=20, paid_at=datetime(2026, 10, 1, 0, 0, tzinfo=KST)),  # 기간 밖 (다음 날 0시)
        expense(6, payer=20, paid_at=datetime(2026, 8, 31, 23, 59, tzinfo=KST)),  # 기간 밖
        expense(7, payer=20, status=ExpenseStatus.DRAFT),
        expense(8, payer=20, paid_at=None),
    ]
    report = summarize(expenses, SEP, OCT)

    assert [e.id for e in report.expenses] == [1, 2, 3]
    assert (report.approved_amount, report.reimbursed_amount, report.unreimbursed_amount) == (24_500, 4_500, 20_000)
    assert (report.awaiting_count, report.awaiting_amount) == (1, 9_999)
    assert [(c.category_id, c.amount, c.item_count) for c in report.categories] == [(FOOD, 14_500, 3), (SNACK, 10_000, 2)]
    assert [(p.payer_id, p.amount, p.reimbursed, p.unreimbursed, p.expense_count) for p in report.payers] == [
        (10, 17_500, 4_500, 13_000, 2),
        (20, 7_000, 0, 7_000, 1),
    ]


def test_summarize_utc_boundary_and_empty() -> None:
    # UTC 9월 30일 15:00 = 한국 10월 1일 0시 → 9월 리포트 밖
    late = expense(1, paid_at=datetime(2026, 9, 30, 15, 0, tzinfo=UTC))
    early = expense(2, paid_at=datetime(2026, 8, 31, 15, 0, tzinfo=UTC))  # = 한국 9월 1일 0시 → 안
    report = summarize([late, early], SEP, OCT)
    assert [e.id for e in report.expenses] == [2]

    empty = summarize([], SEP, OCT)
    assert (empty.approved_amount, empty.categories, empty.payers) == (0, (), ())


# ---------- API ----------


def report_url(team: dict, suffix: str = "") -> str:
    return f"{ORGS}/{team['org_id']}/reports{suffix}"


def approved_expense(client: TestClient, team: dict, payer: str = "앨리스") -> int:
    expense_id = upload_receipt(client, team["alice"], team["org_id"]).json()["id"]
    client.put(url(team, expense_id), json=valid_body(team, payer=payer), headers=team["alice"])
    client.post(url(team, expense_id, "/submit"), headers=team["alice"])
    assert client.post(url(team, expense_id, "/approve"), json={}, headers=team["approver"]).status_code == 200
    return expense_id


def test_report_api(client: TestClient, team: dict) -> None:
    first = approved_expense(client, team)
    approved_expense(client, team, payer="밥")
    client.post(url(team, first, "/reimbursement"), headers=team["owner"])
    pending = upload_receipt(client, team["alice"], team["org_id"]).json()["id"]
    client.put(url(team, pending), json=valid_body(team), headers=team["alice"])
    client.post(url(team, pending, "/submit"), headers=team["alice"])

    params = {"start": "2026-09-01", "end": "2026-09-30"}
    response = client.get(report_url(team), params=params, headers=team["approver"])
    assert response.status_code == 200, response.text
    data = response.json()
    assert (data["approved_count"], data["approved_amount"]) == (2, 17_800)
    assert (data["reimbursed_amount"], data["unreimbursed_amount"]) == (8_900, 8_900)
    assert (data["awaiting_count"], data["awaiting_amount"]) == (1, 8_900)
    assert [(c["name"], c["amount"], c["item_count"]) for c in data["categories"]] == [
        ("비품·소모품", 13_000, 2),
        ("간식·음료", 4_800, 2),
    ]
    assert [(p["payer"]["name"], p["amount"], p["reimbursed"]) for p in data["payers"]] == [
        ("앨리스", 8_900, 8_900),
        ("밥", 8_900, 0),
    ]

    # 결제일(9월 28일)이 기간 밖이면 0
    october = client.get(report_url(team), params={"start": "2026-10-01", "end": "2026-10-31"}, headers=team["owner"])
    assert october.json()["approved_amount"] == 0

    # 구성원은 못 봄, 기간 확인
    assert client.get(report_url(team), params=params, headers=team["alice"]).status_code == 403
    bad = client.get(report_url(team), params={"start": "2026-10-01", "end": "2026-09-01"}, headers=team["owner"])
    assert bad.status_code == 422
    assert client.get(report_url(team), params={"start": "2020-01-01", "end": "2026-01-01"}, headers=team["owner"]).status_code == 422


def test_export_excel(client: TestClient, team: dict) -> None:
    approved_expense(client, team)
    approved_expense(client, team, payer="밥")
    params = {"start": "2026-09-01", "end": "2026-09-30"}
    response = client.get(report_url(team, "/export"), params=params, headers=team["owner"])
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    disposition = response.headers["content-disposition"]
    assert unquote(disposition.split("filename*=UTF-8''")[1]) == "컴공 학생회 지출결산 20260901-20260930.xlsx"
    assert client.get(report_url(team, "/export"), params=params, headers=team["bob"]).status_code == 403

    book = load_workbook(BytesIO(response.content))
    assert book.sheetnames == ["요약", "지출 내역"]
    summary = book["요약"]
    assert summary["A1"].value == "컴공 학생회 지출 결산"
    rows = {row[0]: row[1:] for row in summary.iter_rows(min_row=6, max_row=9, values_only=True)}
    assert rows["승인된 지출"][:2] == (2, 17_800)
    assert rows["아직 안 돌려준 돈"][:2] == (2, 17_800)

    detail = book["지출 내역"]
    header = [c.value for c in detail[1]]
    assert header[:7] == ["지출 번호", "결제일시", "가게", "품목", "수량", "단가", "금액"]
    lines = [row for row in detail.iter_rows(min_row=2, values_only=True) if isinstance(row[0], int)]
    assert len(lines) == 4  # 지출 2건 × 품목 2개
    assert {row[6] for row in lines} == {2_400, 6_500}
    assert all(isinstance(row[6], int) for row in lines)
    assert lines[0][1] == datetime(2026, 9, 28, 14, 32)  # 한국시간, 시간대 없이
    total_row = detail.max_row
    assert detail.cell(row=total_row, column=4).value == "합계"
    assert detail.cell(row=total_row, column=7).value == f"=SUM(G2:G{total_row - 1})"
    assert detail.freeze_panes == "A2"
