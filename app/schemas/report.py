"""Report schemas for API validation"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator

from app.models.report import (
    ReportTypeEnum,
    ExportFormatEnum,
    ReportStatusEnum,
    ScheduleFrequencyEnum
)


# ============================================================================
# Report Template Schemas
# ============================================================================

class ReportTemplateBase(BaseModel):
    """Base schema for report templates"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    report_type: ReportTypeEnum
    fields: List[str] = Field(..., min_items=1)
    filters: Optional[Dict[str, Any]] = None
    sort_by: Optional[str] = None
    sort_order: str = Field(default="asc", pattern="^(asc|desc)$")
    group_by: Optional[List[str]] = None
    aggregations: Optional[Dict[str, Any]] = None
    chart_type: Optional[str] = None
    chart_config: Optional[Dict[str, Any]] = None
    is_public: bool = False
    shared_with_user_ids: Optional[List[uuid.UUID]] = None


class ReportTemplateCreate(ReportTemplateBase):
    """Schema for creating a report template"""
    pass


class ReportTemplateUpdate(BaseModel):
    """Schema for updating a report template"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    fields: Optional[List[str]] = Field(None, min_items=1)
    filters: Optional[Dict[str, Any]] = None
    sort_by: Optional[str] = None
    sort_order: Optional[str] = Field(None, pattern="^(asc|desc)$")
    group_by: Optional[List[str]] = None
    aggregations: Optional[Dict[str, Any]] = None
    chart_type: Optional[str] = None
    chart_config: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = None
    shared_with_user_ids: Optional[List[uuid.UUID]] = None
    is_active: Optional[bool] = None


class ReportTemplateResponse(ReportTemplateBase):
    """Schema for report template response"""
    id: uuid.UUID
    created_by_id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReportTemplateListResponse(BaseModel):
    """Schema for paginated template list"""
    templates: List[ReportTemplateResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# Report Schemas
# ============================================================================

class ReportBase(BaseModel):
    """Base schema for reports"""
    name: str = Field(..., min_length=1, max_length=255)
    report_type: ReportTypeEnum
    export_format: ExportFormatEnum
    parameters: Optional[Dict[str, Any]] = None


class ReportCreate(ReportBase):
    """Schema for creating a report (ad-hoc)"""
    template_id: Optional[uuid.UUID] = None


class ReportFromTemplate(BaseModel):
    """Schema for generating report from template"""
    template_id: uuid.UUID
    export_format: ExportFormatEnum
    parameters: Optional[Dict[str, Any]] = None  # Override template filters


class ReportResponse(ReportBase):
    """Schema for report response"""
    id: uuid.UUID
    template_id: Optional[uuid.UUID]
    generated_by_id: uuid.UUID
    status: ReportStatusEnum
    progress_percentage: int
    error_message: Optional[str]
    total_records: Optional[int]
    file_path: Optional[str]
    file_size_bytes: Optional[int]
    download_url: Optional[str]
    expires_at: Optional[datetime]
    data_snapshot: Optional[Dict[str, Any]]
    generated_at: Optional[datetime]
    downloaded_at: Optional[datetime]
    download_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReportListResponse(BaseModel):
    """Schema for paginated report list"""
    reports: List[ReportResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ReportSummary(BaseModel):
    """Lightweight report summary for lists"""
    id: uuid.UUID
    name: str
    report_type: ReportTypeEnum
    status: ReportStatusEnum
    export_format: ExportFormatEnum
    total_records: Optional[int]
    file_size_bytes: Optional[int]
    generated_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Report Schedule Schemas
# ============================================================================

class ReportScheduleBase(BaseModel):
    """Base schema for report schedules"""
    name: str = Field(..., min_length=1, max_length=255)
    frequency: ScheduleFrequencyEnum
    export_format: ExportFormatEnum
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    day_of_month: Optional[int] = Field(None, ge=1, le=31)
    time_of_day: str = Field(default="00:00", pattern="^([01]?[0-9]|2[0-3]):[0-5][0-9]$")
    timezone: str = Field(default="UTC")
    recipient_user_ids: List[uuid.UUID] = Field(..., min_items=1)
    recipient_emails: Optional[List[str]] = None

    @validator("recipient_emails")
    def validate_emails(cls, v):
        """Validate email format"""
        if v:
            import re
            email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
            for email in v:
                if not email_pattern.match(email):
                    raise ValueError(f"Invalid email format: {email}")
        return v


class ReportScheduleCreate(ReportScheduleBase):
    """Schema for creating a report schedule"""
    template_id: uuid.UUID


class ReportScheduleUpdate(BaseModel):
    """Schema for updating a report schedule"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    frequency: Optional[ScheduleFrequencyEnum] = None
    export_format: Optional[ExportFormatEnum] = None
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    day_of_month: Optional[int] = Field(None, ge=1, le=31)
    time_of_day: Optional[str] = Field(None, pattern="^([01]?[0-9]|2[0-3]):[0-5][0-9]$")
    timezone: Optional[str] = None
    recipient_user_ids: Optional[List[uuid.UUID]] = Field(None, min_items=1)
    recipient_emails: Optional[List[str]] = None
    is_active: Optional[bool] = None


class ReportScheduleResponse(ReportScheduleBase):
    """Schema for report schedule response"""
    id: uuid.UUID
    template_id: uuid.UUID
    created_by_id: uuid.UUID
    is_active: bool
    last_run_at: Optional[datetime]
    next_run_at: datetime
    run_count: int
    last_error: Optional[str]
    consecutive_failures: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReportScheduleListResponse(BaseModel):
    """Schema for paginated schedule list"""
    schedules: List[ReportScheduleResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# Export Schemas
# ============================================================================

class ExportRequest(BaseModel):
    """Schema for custom export requests"""
    report_type: ReportTypeEnum
    export_format: ExportFormatEnum
    fields: List[str] = Field(..., min_items=1)
    filters: Optional[Dict[str, Any]] = None
    sort_by: Optional[str] = None
    sort_order: str = Field(default="asc", pattern="^(asc|desc)$")
    limit: Optional[int] = Field(None, gt=0, le=100000)


class ExportResponse(BaseModel):
    """Schema for export response"""
    report_id: uuid.UUID
    status: ReportStatusEnum
    message: str
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None


# ============================================================================
# Statistics Schemas
# ============================================================================

class ReportStatistics(BaseModel):
    """Schema for report statistics"""
    total_templates: int
    total_reports: int
    total_schedules: int
    reports_by_type: Dict[str, int]
    reports_by_status: Dict[str, int]
    active_schedules: int
    total_downloads: int
    recent_reports: List[ReportSummary]


class TemplateUsageStats(BaseModel):
    """Schema for template usage statistics"""
    template_id: uuid.UUID
    template_name: str
    total_reports: int
    successful_reports: int
    failed_reports: int
    total_downloads: int
    last_used_at: Optional[datetime]
    average_generation_time_seconds: Optional[float]
