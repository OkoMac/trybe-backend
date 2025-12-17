"""Report endpoints - Templates, generation, exports, and scheduling"""

import uuid
import math
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks, Response
from sqlalchemy import select, func, and_, or_, desc, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.report import (
    ReportTemplate,
    Report,
    ReportSchedule,
    ReportTypeEnum,
    ExportFormatEnum,
    ReportStatusEnum
)
from app.schemas.report import (
    # Template schemas
    ReportTemplateCreate,
    ReportTemplateUpdate,
    ReportTemplateResponse,
    ReportTemplateListResponse,
    # Report schemas
    ReportCreate,
    ReportFromTemplate,
    ReportResponse,
    ReportListResponse,
    ReportSummary,
    # Schedule schemas
    ReportScheduleCreate,
    ReportScheduleUpdate,
    ReportScheduleResponse,
    ReportScheduleListResponse,
    # Export schemas
    ExportRequest,
    ExportResponse,
    # Statistics schemas
    ReportStatistics,
    TemplateUsageStats
)
from app.services.report_service import ReportService

router = APIRouter()


# ============================================================================
# Report Template Endpoints
# ============================================================================

@router.post("/templates", response_model=ReportTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_report_template(
    template: ReportTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new report template"""

    new_template = ReportTemplate(
        id=uuid.uuid4(),
        name=template.name,
        description=template.description,
        report_type=template.report_type,
        created_by_id=current_user.id,
        fields=template.fields,
        filters=template.filters,
        sort_by=template.sort_by,
        sort_order=template.sort_order,
        group_by=template.group_by,
        aggregations=template.aggregations,
        chart_type=template.chart_type,
        chart_config=template.chart_config,
        is_public=template.is_public,
        shared_with_user_ids=template.shared_with_user_ids,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.add(new_template)
    await db.commit()
    await db.refresh(new_template)

    return new_template


@router.get("/templates", response_model=ReportTemplateListResponse)
async def list_report_templates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    report_type: Optional[ReportTypeEnum] = None,
    is_public: Optional[bool] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List report templates accessible to current user"""

    # Build query - show templates created by user, public templates, or shared with user
    query = select(ReportTemplate).where(
        or_(
            ReportTemplate.created_by_id == current_user.id,
            ReportTemplate.is_public == True,
            text(f"'{current_user.id}'::uuid = ANY(shared_with_user_ids)")
        )
    )

    # Apply filters
    filters = []

    if report_type:
        filters.append(ReportTemplate.report_type == report_type)

    if is_public is not None:
        filters.append(ReportTemplate.is_public == is_public)

    if search:
        filters.append(
            or_(
                ReportTemplate.name.ilike(f"%{search}%"),
                ReportTemplate.description.ilike(f"%{search}%")
            )
        )

    if filters:
        query = query.where(and_(*filters))

    # Get total count
    count_query = select(func.count()).select_from(ReportTemplate).where(query.whereclause)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Apply pagination
    query = query.order_by(desc(ReportTemplate.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    # Execute query
    result = await db.execute(query)
    templates = result.scalars().all()

    return ReportTemplateListResponse(
        templates=templates,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0
    )


@router.get("/templates/{template_id}", response_model=ReportTemplateResponse)
async def get_report_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific report template"""

    query = select(ReportTemplate).where(ReportTemplate.id == template_id)
    result = await db.execute(query)
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report template not found"
        )

    # Check access permissions
    if not (
        template.created_by_id == current_user.id
        or template.is_public
        or (template.shared_with_user_ids and current_user.id in template.shared_with_user_ids)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this report template"
        )

    return template


@router.patch("/templates/{template_id}", response_model=ReportTemplateResponse)
async def update_report_template(
    template_id: uuid.UUID,
    template_update: ReportTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a report template (creator only)"""

    query = select(ReportTemplate).where(ReportTemplate.id == template_id)
    result = await db.execute(query)
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report template not found"
        )

    # Only creator can update
    if template.created_by_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the template creator can update it"
        )

    # Update fields
    update_data = template_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    template.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(template)

    return template


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a report template (creator only)"""

    query = select(ReportTemplate).where(ReportTemplate.id == template_id)
    result = await db.execute(query)
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report template not found"
        )

    # Only creator can delete
    if template.created_by_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the template creator can delete it"
        )

    await db.delete(template)
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================================
# Report Generation Endpoints
# ============================================================================

@router.post("/generate", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def generate_report_from_template(
    report_request: ReportFromTemplate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate a report from a template"""

    # Get template
    query = select(ReportTemplate).where(ReportTemplate.id == report_request.template_id)
    result = await db.execute(query)
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report template not found"
        )

    # Check access
    if not (
        template.created_by_id == current_user.id
        or template.is_public
        or (template.shared_with_user_ids and current_user.id in template.shared_with_user_ids)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this report template"
        )

    # Create report
    report = await ReportService.create_report_from_template(
        db=db,
        template=template,
        user_id=current_user.id,
        export_format=report_request.export_format,
        parameter_overrides=report_request.parameters
    )

    # Process report in background
    background_tasks.add_task(ReportService.process_report_background, report.id)

    return report


@router.post("/export", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_ad_hoc_report(
    export_request: ExportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create an ad-hoc report without a template"""

    # Create report record
    report = Report(
        id=uuid.uuid4(),
        name=f"Ad-hoc {export_request.report_type.value} Report - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
        report_type=export_request.report_type,
        template_id=None,
        generated_by_id=current_user.id,
        export_format=export_request.export_format,
        parameters={
            "fields": export_request.fields,
            "filters": export_request.filters,
            "sort_by": export_request.sort_by,
            "sort_order": export_request.sort_order,
            "limit": export_request.limit
        },
        status=ReportStatusEnum.pending,
        progress_percentage=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.add(report)
    await db.commit()
    await db.refresh(report)

    # Process report in background
    background_tasks.add_task(ReportService.process_report_background, report.id)

    return report


@router.get("/reports", response_model=ReportListResponse)
async def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    report_type: Optional[ReportTypeEnum] = None,
    status: Optional[ReportStatusEnum] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List reports generated by current user"""

    query = select(Report).where(Report.generated_by_id == current_user.id)

    # Apply filters
    filters = []

    if report_type:
        filters.append(Report.report_type == report_type)

    if status:
        filters.append(Report.status == status)

    if filters:
        query = query.where(and_(*filters))

    # Get total count
    count_query = select(func.count()).select_from(Report).where(query.whereclause)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Apply pagination
    query = query.order_by(desc(Report.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    # Execute query
    result = await db.execute(query)
    reports = result.scalars().all()

    return ReportListResponse(
        reports=reports,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0
    )


@router.get("/reports/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific report"""

    query = select(Report).where(Report.id == report_id)
    result = await db.execute(query)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )

    # Only generator can access
    if report.generated_by_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this report"
        )

    return report


@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download a generated report file"""

    query = select(Report).where(Report.id == report_id)
    result = await db.execute(query)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )

    # Only generator can download
    if report.generated_by_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this report"
        )

    # Check if report is completed
    if report.status != ReportStatusEnum.completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Report is not ready for download. Current status: {report.status}"
        )

    # Check if expired
    if report.expires_at and report.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Report has expired"
        )

    # Update download stats
    report.downloaded_at = datetime.utcnow()
    report.download_count += 1
    await db.commit()

    # In production, return file from cloud storage
    # For now, return a placeholder response
    return {
        "message": "Report download ready",
        "report_id": str(report.id),
        "file_path": report.file_path,
        "file_size_bytes": report.file_size_bytes,
        "download_url": report.download_url,
        "note": "In production, this would stream the file directly"
    }


@router.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a generated report"""

    query = select(Report).where(Report.id == report_id)
    result = await db.execute(query)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )

    # Only generator can delete
    if report.generated_by_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this report"
        )

    await db.delete(report)
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================================
# Report Schedule Endpoints
# ============================================================================

@router.post("/schedules", response_model=ReportScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_report_schedule(
    schedule: ReportScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a scheduled report"""

    # Verify template exists and user has access
    query = select(ReportTemplate).where(ReportTemplate.id == schedule.template_id)
    result = await db.execute(query)
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report template not found"
        )

    # Check access
    if not (
        template.created_by_id == current_user.id
        or template.is_public
        or (template.shared_with_user_ids and current_user.id in template.shared_with_user_ids)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this report template"
        )

    # Create schedule
    new_schedule = ReportSchedule(
        id=uuid.uuid4(),
        template_id=schedule.template_id,
        created_by_id=current_user.id,
        name=schedule.name,
        frequency=schedule.frequency,
        export_format=schedule.export_format,
        day_of_week=schedule.day_of_week,
        day_of_month=schedule.day_of_month,
        time_of_day=schedule.time_of_day,
        timezone=schedule.timezone,
        recipient_user_ids=schedule.recipient_user_ids,
        recipient_emails=schedule.recipient_emails,
        is_active=True,
        run_count=0,
        consecutive_failures=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    # Calculate next run time
    new_schedule.next_run_at = await ReportService.calculate_next_run_time(new_schedule)

    db.add(new_schedule)
    await db.commit()
    await db.refresh(new_schedule)

    return new_schedule


@router.get("/schedules", response_model=ReportScheduleListResponse)
async def list_report_schedules(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List report schedules created by current user"""

    query = select(ReportSchedule).where(ReportSchedule.created_by_id == current_user.id)

    # Apply filters
    if is_active is not None:
        query = query.where(ReportSchedule.is_active == is_active)

    # Get total count
    count_query = select(func.count()).select_from(ReportSchedule).where(query.whereclause)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Apply pagination
    query = query.order_by(desc(ReportSchedule.next_run_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    # Execute query
    result = await db.execute(query)
    schedules = result.scalars().all()

    return ReportScheduleListResponse(
        schedules=schedules,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0
    )


@router.get("/schedules/{schedule_id}", response_model=ReportScheduleResponse)
async def get_report_schedule(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific report schedule"""

    query = select(ReportSchedule).where(ReportSchedule.id == schedule_id)
    result = await db.execute(query)
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report schedule not found"
        )

    # Only creator can access
    if schedule.created_by_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this report schedule"
        )

    return schedule


@router.patch("/schedules/{schedule_id}", response_model=ReportScheduleResponse)
async def update_report_schedule(
    schedule_id: uuid.UUID,
    schedule_update: ReportScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a report schedule"""

    query = select(ReportSchedule).where(ReportSchedule.id == schedule_id)
    result = await db.execute(query)
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report schedule not found"
        )

    # Only creator can update
    if schedule.created_by_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the schedule creator can update it"
        )

    # Update fields
    update_data = schedule_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(schedule, field, value)

    schedule.updated_at = datetime.utcnow()

    # Recalculate next run time if schedule parameters changed
    if any(field in update_data for field in ["frequency", "day_of_week", "day_of_month", "time_of_day"]):
        schedule.next_run_at = await ReportService.calculate_next_run_time(schedule)

    await db.commit()
    await db.refresh(schedule)

    return schedule


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report_schedule(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a report schedule"""

    query = select(ReportSchedule).where(ReportSchedule.id == schedule_id)
    result = await db.execute(query)
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report schedule not found"
        )

    # Only creator can delete
    if schedule.created_by_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the schedule creator can delete it"
        )

    await db.delete(schedule)
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================================
# Statistics Endpoints
# ============================================================================

@router.get("/statistics", response_model=ReportStatistics)
async def get_report_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get report statistics for current user"""

    # Count templates
    templates_query = select(func.count()).select_from(ReportTemplate).where(
        ReportTemplate.created_by_id == current_user.id
    )
    templates_result = await db.execute(templates_query)
    total_templates = templates_result.scalar() or 0

    # Count reports
    reports_query = select(func.count()).select_from(Report).where(
        Report.generated_by_id == current_user.id
    )
    reports_result = await db.execute(reports_query)
    total_reports = reports_result.scalar() or 0

    # Count schedules
    schedules_query = select(func.count()).select_from(ReportSchedule).where(
        ReportSchedule.created_by_id == current_user.id
    )
    schedules_result = await db.execute(schedules_query)
    total_schedules = schedules_result.scalar() or 0

    # Count active schedules
    active_schedules_query = select(func.count()).select_from(ReportSchedule).where(
        and_(
            ReportSchedule.created_by_id == current_user.id,
            ReportSchedule.is_active == True
        )
    )
    active_schedules_result = await db.execute(active_schedules_query)
    active_schedules = active_schedules_result.scalar() or 0

    # Reports by type
    reports_by_type = {}
    for report_type in ReportTypeEnum:
        type_query = select(func.count()).select_from(Report).where(
            and_(
                Report.generated_by_id == current_user.id,
                Report.report_type == report_type
            )
        )
        type_result = await db.execute(type_query)
        count = type_result.scalar() or 0
        if count > 0:
            reports_by_type[report_type.value] = count

    # Reports by status
    reports_by_status = {}
    for status_value in ReportStatusEnum:
        status_query = select(func.count()).select_from(Report).where(
            and_(
                Report.generated_by_id == current_user.id,
                Report.status == status_value
            )
        )
        status_result = await db.execute(status_query)
        count = status_result.scalar() or 0
        if count > 0:
            reports_by_status[status_value.value] = count

    # Total downloads
    downloads_query = select(func.sum(Report.download_count)).select_from(Report).where(
        Report.generated_by_id == current_user.id
    )
    downloads_result = await db.execute(downloads_query)
    total_downloads = downloads_result.scalar() or 0

    # Recent reports
    recent_query = select(Report).where(
        Report.generated_by_id == current_user.id
    ).order_by(desc(Report.created_at)).limit(5)
    recent_result = await db.execute(recent_query)
    recent_reports = recent_result.scalars().all()

    return ReportStatistics(
        total_templates=total_templates,
        total_reports=total_reports,
        total_schedules=total_schedules,
        reports_by_type=reports_by_type,
        reports_by_status=reports_by_status,
        active_schedules=active_schedules,
        total_downloads=total_downloads,
        recent_reports=[ReportSummary.model_validate(r) for r in recent_reports]
    )
