"""Payment models - Payment proposals and transactions"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, Enum, Integer, Numeric, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
import uuid
import enum

from app.core.database import Base


class PaymentStatusEnum(str, enum.Enum):
    """Payment status enumeration"""
    proposed = "proposed"
    counter_proposed = "counter_proposed"
    system_suggested = "system_suggested"
    accepted = "accepted"
    rejected = "rejected"
    in_progress = "in_progress"
    completed = "completed"
    paid = "paid"


class PaymentTypeEnum(str, enum.Enum):
    """Payment type enumeration"""
    hourly = "hourly"
    fixed = "fixed"
    milestone = "milestone"
    commission = "commission"


class TransactionStatusEnum(str, enum.Enum):
    """Transaction status enumeration"""
    pending = "pending"
    processing = "processing"
    succeeded = "succeeded"
    failed = "failed"
    refunded = "refunded"
    disputed = "disputed"


class PaymentProposal(Base):
    """Payment Proposal model - negotiable payment between parties"""

    __tablename__ = "payment_proposals"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    # Related Entities
    opportunity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Related opportunity (if applicable)"
    )
    match_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matches.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Related match (if applicable)"
    )

    # Parties
    proposer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who made the proposal"
    )
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who receives the proposal"
    )

    # Payment Details
    payment_type: Mapped[PaymentTypeEnum] = mapped_column(
        Enum(PaymentTypeEnum, name="payment_type_enum"),
        nullable=False
    )
    amount: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Proposed amount"
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        default="USD",
        nullable=False
    )
    hourly_rate: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="For hourly payments"
    )
    estimated_hours: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Estimated hours for hourly payments"
    )

    # Status and History
    status: Mapped[PaymentStatusEnum] = mapped_column(
        Enum(PaymentStatusEnum, name="payment_status_enum", create_constraint=False),
        nullable=False,
        default=PaymentStatusEnum.proposed,
        index=True
    )

    # Counter Proposal Tracking
    original_amount: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Original proposed amount before counter"
    )
    counter_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of counter proposals"
    )

    # AI Suggestions
    is_ai_suggested: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True if suggested by AI"
    )
    ai_confidence_score: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="AI confidence score 0-100"
    )

    # Terms and Conditions
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Description of work/services"
    )
    terms: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Payment terms and conditions"
    )
    milestones: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Array of milestone objects for milestone payments"
    )

    # Dates
    deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Deadline for work completion"
    )
    accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    rejected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Proposal expiration time"
    )

    # Metadata
    proposal_metadata: Mapped[Optional[dict]] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        default=dict,
        comment="Additional proposal metadata"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<PaymentProposal {self.id} - {self.amount} {self.currency} ({self.status})>"


class Transaction(Base):
    """Transaction model - actual payment transactions via Stripe"""

    __tablename__ = "transactions"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    # Related Proposal
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payment_proposals.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Parties
    payer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    payee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Transaction Details
    amount: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        default="USD",
        nullable=False
    )
    platform_fee: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=0.0,
        comment="Trybe platform fee"
    )
    net_amount: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Amount after platform fee"
    )

    # Status
    status: Mapped[TransactionStatusEnum] = mapped_column(
        Enum(TransactionStatusEnum, name="transaction_status_enum"),
        nullable=False,
        default=TransactionStatusEnum.pending,
        index=True
    )

    # Stripe Integration
    stripe_payment_intent_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
        comment="Stripe PaymentIntent ID"
    )
    stripe_charge_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Stripe Charge ID"
    )
    stripe_transfer_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Stripe Transfer ID to payee"
    )

    # Payment Method
    payment_method_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="e.g., card, bank_transfer"
    )
    last_4_digits: Mapped[Optional[str]] = mapped_column(
        String(4),
        nullable=True,
        comment="Last 4 digits of card/account"
    )

    # Error Handling
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if transaction failed"
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    # Refund Information
    refunded_amount: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=0.0
    )
    refund_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Metadata
    transaction_metadata: Mapped[Optional[dict]] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        default=dict,
        comment="Additional transaction metadata"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    def __repr__(self) -> str:
        return f"<Transaction {self.id} - {self.amount} {self.currency} ({self.status})>"
