from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from app.database import get_session_factory
from app.models.report import Report
from app.schemas.report import ReportDetail, ReportListResponse, ReportSummary

router = APIRouter()


@router.get("", response_model=ReportListResponse)
async def list_reports(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> ReportListResponse:
    """列出已归档到 MySQL 的技术报告。"""
    factory = get_session_factory()
    async with factory() as session:
        total_result = await session.execute(select(func.count(Report.id)))
        total = total_result.scalar_one()

        result = await session.execute(
            select(Report)
            .order_by(Report.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        reports = result.scalars().all()

        items = [
        ReportSummary(
            id=r.id,
            title=r.title,
            query=r.query,
            repo_owner=r.repo_owner,
            repo_name=r.repo_name,
            sub_type=r.sub_type,
            created_at=r.created_at,
        )
        for r in reports
    ]
    return ReportListResponse(total=total, items=items)


@router.get("/{report_id}", response_model=ReportDetail)
async def get_report(report_id: int) -> ReportDetail:
    """获取单份报告详情。"""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(Report).where(Report.id == report_id)
        )
        report = result.scalar_one_or_none()

    if report is None:
        raise HTTPException(status_code=404, detail=f"报告 {report_id} 不存在")

    return ReportDetail(
        id=report.id,
        title=report.title,
        content=report.content,
        query=report.query,
        repo_owner=report.repo_owner,
        repo_name=report.repo_name,
        sub_type=report.sub_type,
        sources=report.sources,
        created_at=report.created_at,
    )
