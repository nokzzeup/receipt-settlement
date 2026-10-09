"""기간별 리포트·엑셀 내보내기 (총무·승인자).

계산은 app/reports/summary.py (pytest). 기간 = 결제일(한국 날짜) 기준, 승인된 지출만 합계에 들어간다.
"""

import re
from datetime import UTC, date, datetime
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.deps import DbSession, ReviewerMembership
from app.models import Organization
from app.reports import CategoryInfo, ReportSummary, build_workbook, load_report_expenses, summarize
from app.schemas.expense import PersonOut
from app.schemas.report import ReportCategoryOut, ReportOut, ReportPayerOut
from app.settlement import load_categories

router = APIRouter(prefix="/orgs/{org_id}/reports", tags=["reports"])

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MAX_DAYS = 366 * 3

Start = Annotated[date, Query(description="시작일 (결제일 기준, 포함)")]
End = Annotated[date, Query(description="끝일 (포함)")]


def _check_period(start: date, end: date) -> None:
    if start > end:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "시작일이 끝일보다 늦습니다.")
    if (end - start).days > MAX_DAYS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "기간은 3년 이내로 정하세요.")


def _summary(db: DbSession, org_id: int, start: date, end: date) -> ReportSummary:
    _check_period(start, end)
    return summarize(load_report_expenses(db, org_id), start, end)


@router.get("")
def get_report(org_id: int, start: Start, end: End, me: ReviewerMembership, db: DbSession) -> ReportOut:
    summary = _summary(db, org_id, start, end)
    categories = {c.id: c for c in load_categories(db, org_id)}
    return ReportOut(
        start=start,
        end=end,
        approved_count=len(summary.expenses),
        approved_amount=summary.approved_amount,
        reimbursed_amount=summary.reimbursed_amount,
        unreimbursed_amount=summary.unreimbursed_amount,
        awaiting_count=summary.awaiting_count,
        awaiting_amount=summary.awaiting_amount,
        categories=[
            ReportCategoryOut(
                category_id=c.category_id,
                name=categories[c.category_id].name if c.category_id in categories else "미분류",
                amount=c.amount,
                item_count=c.item_count,
                budget=categories[c.category_id].budget_amount if c.category_id in categories else None,
            )
            for c in summary.categories
        ],
        payers=[
            ReportPayerOut(
                payer=PersonOut(membership_id=p.payer_id, name=p.payer_name),
                amount=p.amount,
                reimbursed=p.reimbursed,
                unreimbursed=p.unreimbursed,
                expense_count=p.expense_count,
            )
            for p in summary.payers
        ],
    )


def _safe_filename(text: str) -> str:
    return re.sub(r'[\\/:*?"<>|\r\n]+', "_", text).strip() or "조직"


@router.get(
    "/export",
    response_class=Response,
    responses={200: {"content": {XLSX_MEDIA_TYPE: {}}, "description": "엑셀 파일 (요약 + 지출 내역)"}},
)
def export_report(org_id: int, start: Start, end: End, me: ReviewerMembership, db: DbSession) -> Response:
    """리포트 엑셀 파일 (시트: 요약 / 지출 내역 — 품목 한 줄씩)"""
    summary = _summary(db, org_id, start, end)
    org = db.get_one(Organization, org_id)
    categories = [CategoryInfo(id=c.id, name=c.name, budget=c.budget_amount) for c in load_categories(db, org_id)]
    content = build_workbook(org.name, summary, categories, generated_at=datetime.now(UTC))
    filename = f"{_safe_filename(org.name)} 지출결산 {start:%Y%m%d}-{end:%Y%m%d}.xlsx"
    return Response(
        content=content,
        media_type=XLSX_MEDIA_TYPE,
        headers={
            # 한글 파일 이름은 filename*(UTF-8)로. 옛 브라우저용 filename은 영문
            "Content-Disposition": f"attachment; filename=\"report.xlsx\"; filename*=UTF-8''{quote(filename, safe='')}",
            "Cache-Control": "no-store",
        },
    )
