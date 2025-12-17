"""Report models for custom report generation and data exports"""

import uuid
import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Boolean, Integer, Float, DateTime, ForeignKey, Index, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ReportTypeEnum(str, enum.Enum):
    """Types of reports that can be generated"""
    users = "users"
    opportunities = "opportunities"
    matches = "matches"
    payments = "payments"
    transactions = "transactions"
    messages = "messages"
    learning = "learning"
    analytics = "analytics"
    custom = "custom"


class ExportFormatEnum(str, enum.Enum):
    """Supported export formats"""
    csv = "csv"
    excel = "excel"
    pdf = "pdf"
    json = "json"


class ReportStatusEnum(str, enum.Enum):
    """Report generation status"""
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class ScheduleFrequencyEnum(str, enum.Enum):
    """Frequency for scheduled reports"""
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    quarterly = "quarterly"
    yearly = "yearly"


class ReportTemplate(Base):
    """Predefined report configurations and templates"""
    __tablename__ = "report_templates"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Template details
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    report_type: Mapped[ReportTypeEnum] = mapped_column(String(50), nullable=False, index=True)

    # Creator
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Configuration
    fields: Mapped[list] = mapped_column(ARRAY(String), nullable=False)  # Fields to include
    filters: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # Filter criteria
    sort_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sort_order: Mapped[str] = mapped_column(String(4), default="asc")  # asc or desc

    # Aggregations and grouping
    group_by: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)
    aggregations: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # sum, avg, count, etc.

    # Display options
    chart_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # bar, line, pie, etc.
    chart_config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Access control
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    shared_with_user_ids: Mapped[Optional[list]] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=True)

    # Metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    created_by: Mapped["User"] = relationship("User", back_populates="report_templates")
    reports: Mapped[list["Report"]] = relationship("Report", back_populates="template")
    schedules: Mapped[list["ReportSchedule"]] = relationship("ReportSchedule", back_populates="template")

    # Indexes
    __table_args__ = (
        Index("ix_report_templates_created_by_id", "created_by_id"),
        Index("ix_report_templates_report_type", "report_type"),
        Index("ix_report_templates_is_active", "is_active"),
    )


class Report(Base):
    """Generated report instances"""
    __tablename__ = "reports"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Report details
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    report_type: Mapped[ReportTypeEnum] = mapped_column(String(50), nullable=False, index=True)

    # Template reference (optional - reports can be ad-hoc)
    template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("report_templates.id", ondelete="SET NULL"),
        nullable=True
    )

    # Generator
    generated_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Generation parameters
    parameters: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # Filters, date ranges, etc.
    export_format: Mapped[ExportFormatEnum] = mapped_column(String(20), nullable=False)

    # Status and progress
    status: Mapped[ReportStatusEnum] = mapped_column(String(20), default=ReportStatusEnum.pending, index=True)
    progress_percentage: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Results
    total_records: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    download_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Metadata
    data_snapshot: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # Summary statistics
    generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    downloaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    download_count: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    template: Mapped[Optional["ReportTemplate"]] = relationship("ReportTemplate", back_populates="reports")
    generated_by: Mapped["User"] = relationship("User", back_populates="reports")

    # Indexes
    __table_args__ = (
        Index("ix_reports_generated_by_id", "generated_by_id"),
        Index("ix_reports_template_id", "template_id"),
        Index("ix_reports_status", "status"),
        Index("ix_reports_created_at", "created_at"),
    )


class ReportSchedule(Base):
    """Scheduled report generation"""
    __tablename__ = "report_schedules"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Template reference
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("report_templates.id", ondelete="CASCADE"),
        nullable=False
    )

    # Schedule owner
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Schedule configuration
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    frequency: Mapped[ScheduleFrequencyEnum] = mapped_column(String(20), nullable=False)
    export_format: Mapped[ExportFormatEnum] = mapped_column(String(20), nullable=False)

    # Timing
    day_of_week: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0=Monday, 6=Sunday
    day_of_month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-31
    time_of_day: Mapped[str] = mapped_column(String(5), default="00:00")  # HH:MM format
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")

    # Recipients
    recipient_user_ids: Mapped[list] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False)
    recipient_emails: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    next_run_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    run_count: Mapped[int] = mapped_column(Integer, default=0)

    # Error tracking
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    template: Mapped["ReportTemplate"] = relationship("ReportTemplate", back_populates="schedules")
    created_by: Mapped["User"] = relationship("User", back_populates="report_schedules")

    # Indexes
    __table_args__ = (
        Index("ix_report_schedules_template_id", "template_id"),
        Index("ix_report_schedules_created_by_id", "created_by_id"),
        Index("ix_report_schedules_is_active", "is_active"),
        Index("ix_report_schedules_next_run_at", "next_run_at"),
    )
