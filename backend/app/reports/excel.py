"""리포트 → 엑셀(.xlsx) 파일. 시트 2개: 요약(합계·계정과목별·결제자별) / 지출 내역(품목 한 줄씩).

- 금액은 원 단위 정수 + 쉼표 서식. 합계·남은 예산은 엑셀 수식이라 표를 고치면 다시 계산된다
- 시각은 한국시간 (엑셀은 시간대를 모르므로 한국시간으로 바꿔서 시간대 없이 넣음)
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from app.core.timezone import KST
from app.reports.summary import ReportSummary

MONEY = "#,##0"
DATETIME = "yyyy-mm-dd hh:mm"
_HEADER_FILL = PatternFill("solid", fgColor="EEF0F3")
_TOTAL_FILL = PatternFill("solid", fgColor="F7F8FA")
_BOLD = Font(bold=True)
_MUTED = Font(color="5F6672")


@dataclass(frozen=True)
class CategoryInfo:
    id: int
    name: str
    budget: int | None


def _local(value: datetime | None) -> datetime | None:
    """한국시간 + 시간대 없이 + 초 아래는 버림 (엑셀은 시간대를 모름)"""
    return value.astimezone(KST).replace(tzinfo=None, microsecond=0) if value else None


def _period_text(summary: ReportSummary) -> str:
    return f"{summary.start:%Y-%m-%d} ~ {summary.end:%Y-%m-%d}"


def _header(ws: Worksheet, row: int, labels: Sequence[str]) -> None:
    for col, label in enumerate(labels, start=1):
        cell = ws.cell(row=row, column=col, value=label)
        cell.font = _BOLD
        cell.fill = _HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")


def _money(ws: Worksheet, row: int, col: int, value: int | str | None) -> None:
    cell = ws.cell(row=row, column=col, value=value)
    cell.number_format = MONEY


def _total_row(ws: Worksheet, row: int, columns: int) -> None:
    for col in range(1, columns + 1):
        ws.cell(row=row, column=col).fill = _TOTAL_FILL
        ws.cell(row=row, column=col).font = _BOLD


def _widths(ws: Worksheet, widths: Sequence[int]) -> None:
    for index, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(index)].width = width


def build_workbook(
    org_name: str, summary: ReportSummary, categories: Sequence[CategoryInfo], generated_at: datetime
) -> bytes:
    wb = Workbook()
    _summary_sheet(wb.active, org_name, summary, categories, generated_at)
    _detail_sheet(wb.create_sheet("지출 내역"), summary, {c.id: c.name for c in categories})
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _summary_sheet(
    ws: Worksheet, org_name: str, summary: ReportSummary, categories: Sequence[CategoryInfo], generated_at: datetime
) -> None:
    ws.title = "요약"
    _widths(ws, (26, 16, 18, 16, 10))
    ws["A1"] = f"{org_name} 지출 결산"
    ws["A1"].font = Font(size=16, bold=True)
    ws["A2"] = f"기간 {_period_text(summary)} · 결제일 기준 · 승인된 지출만 · 금액 단위 원"
    ws["A3"] = f"만든 시각 {_local(generated_at):%Y-%m-%d %H:%M} (한국시간)"
    ws["A2"].font = ws["A3"].font = _MUTED

    reimbursed_count = sum(1 for e in summary.expenses if e.reimbursed_at is not None)
    row = 5
    _header(ws, row, ("항목", "건수", "금액"))
    for label, count, amount in (
        ("승인된 지출", len(summary.expenses), summary.approved_amount),
        ("돌려준 돈", reimbursed_count, summary.reimbursed_amount),
        ("아직 안 돌려준 돈", len(summary.expenses) - reimbursed_count, summary.unreimbursed_amount),
        ("승인 대기 (위 합계에 안 들어감)", summary.awaiting_count, summary.awaiting_amount),
    ):
        row += 1
        ws.cell(row=row, column=1, value=label)
        ws.cell(row=row, column=2, value=count)
        _money(ws, row, 3, amount)

    # 계정과목별: 조직의 계정과목 전부(안 쓴 것도 0원으로) + 미분류가 있으면 마지막에
    row += 2
    ws.cell(row=row, column=1, value="계정과목별").font = Font(size=13, bold=True)
    row += 1
    _header(ws, row, ("계정과목", "집행액", "예산 (지금 설정)", "남은 예산", "품목 수"))
    totals = {c.category_id: c for c in summary.categories}
    first = row + 1
    lines = [(c.name, c.id, c.budget) for c in categories]
    if None in totals:
        lines.append(("미분류", None, None))
    for name, category_id, budget in lines:
        row += 1
        total = totals.get(category_id)
        ws.cell(row=row, column=1, value=name)
        _money(ws, row, 2, total.amount if total else 0)
        _money(ws, row, 3, budget)
        _money(ws, row, 4, f'=IF(C{row}="","",C{row}-B{row})')
        ws.cell(row=row, column=5, value=total.item_count if total else 0)
    last = row
    row += 1
    ws.cell(row=row, column=1, value="합계")
    _money(ws, row, 2, f"=SUM(B{first}:B{last})")
    _money(ws, row, 3, f"=SUM(C{first}:C{last})")
    ws.cell(row=row, column=5, value=f"=SUM(E{first}:E{last})")
    _total_row(ws, row, 5)
    row += 1
    note = ws.cell(row=row, column=1, value="예산은 지금 설정된 값이에요. 리포트 기간과 예산 기간이 다르면 비교에 주의하세요.")
    note.font = _MUTED

    # 결제자별
    row += 2
    ws.cell(row=row, column=1, value="결제자별 (돌려줄 돈)").font = Font(size=13, bold=True)
    row += 1
    _header(ws, row, ("결제자", "승인된 금액", "돌려준 금액", "남은 금액", "지출 수"))
    first = row + 1
    for payer in summary.payers:
        row += 1
        ws.cell(row=row, column=1, value=payer.payer_name)
        _money(ws, row, 2, payer.amount)
        _money(ws, row, 3, payer.reimbursed)
        _money(ws, row, 4, f"=B{row}-C{row}")
        ws.cell(row=row, column=5, value=payer.expense_count)
    if summary.payers:
        last = row
        row += 1
        ws.cell(row=row, column=1, value="합계")
        for col, letter in ((2, "B"), (3, "C"), (4, "D")):
            _money(ws, row, col, f"=SUM({letter}{first}:{letter}{last})")
        ws.cell(row=row, column=5, value=f"=SUM(E{first}:E{last})")
        _total_row(ws, row, 5)


DETAIL_COLUMNS = (
    ("지출 번호", 10),
    ("결제일시", 17),
    ("가게", 22),
    ("품목", 26),
    ("수량", 7),
    ("단가", 11),
    ("금액", 12),
    ("계정과목", 14),
    ("결제자", 10),
    ("올린 사람", 10),
    ("승인일시", 17),
    ("환급일시", 17),
)


def _detail_sheet(ws: Worksheet, summary: ReportSummary, category_names: dict[int, str]) -> None:
    _widths(ws, [width for _, width in DETAIL_COLUMNS])
    _header(ws, 1, [label for label, _ in DETAIL_COLUMNS])
    ws.freeze_panes = "A2"
    row = 1
    for expense in summary.expenses:
        for item in expense.items:
            row += 1
            values = (
                expense.id,
                _local(expense.paid_at),
                expense.store_name or "",
                item.name,
                item.quantity,
                item.unit_price,
                item.amount,
                category_names.get(item.category_id, "미분류") if item.category_id is not None else "미분류",
                expense.payer_name,
                expense.uploader_name,
                _local(expense.approved_at),
                _local(expense.reimbursed_at),
            )
            for col, value in enumerate(values, start=1):
                ws.cell(row=row, column=col, value=value)
            for col in (2, 11, 12):
                ws.cell(row=row, column=col).number_format = DATETIME
            for col in (6, 7):
                ws.cell(row=row, column=col).number_format = MONEY
    last = row
    if last >= 2:
        ws.auto_filter.ref = f"A1:{get_column_letter(len(DETAIL_COLUMNS))}{last}"
    row += 1
    ws.cell(row=row, column=4, value="합계")
    _money(ws, row, 7, f"=SUM(G2:G{max(last, 2)})" if last >= 2 else 0)
    _total_row(ws, row, len(DETAIL_COLUMNS))
