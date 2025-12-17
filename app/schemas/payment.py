"""Payment schemas - Pydantic models for API validation"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import uuid


class PaymentProposalBase(BaseModel):
    """Base payment proposal schema"""
    payment_type: str = Field(..., pattern="^(hourly|fixed|milestone|commission)$")
    amount: float = Field(..., ge=0, description="Proposed amount")
    currency: str = Field(default="USD", max_length=3)
    hourly_rate: Optional[float] = Field(None, ge=0)
    estimated_hours: Optional[int] = Field(None, ge=0)
    description: str = Field(..., min_length=10)
    terms: Optional[str] = None
    milestones: Optional[List[dict]] = None
    deadline: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class PaymentProposalCreate(PaymentProposalBase):
    """Schema for creating a payment proposal"""
    opportunity_id: Optional[uuid.UUID] = None
    match_id: Optional[uuid.UUID] = None
    recipient_id: uuid.UUID

    @field_validator("milestones")
    @classmethod
    def validate_milestones(cls, v: Optional[List[dict]]) -> Optional[List[dict]]:
        """Validate milestone structure"""
        if v:
            for milestone in v:
                if "description" not in milestone or "amount" not in milestone:
                    raise ValueError("Each milestone must have description and amount")
        return v


class PaymentProposalUpdate(BaseModel):
    """Schema for updating a payment proposal"""
    amount: Optional[float] = Field(None, ge=0)
    description: Optional[str] = Field(None, min_length=10)
    terms: Optional[str] = None
    milestones: Optional[List[dict]] = None
    deadline: Optional[datetime] = None


class PaymentProposalCounter(BaseModel):
    """Schema for counter proposal"""
    amount: float = Field(..., ge=0)
    description: Optional[str] = None
    terms: Optional[str] = None


class PaymentProposalResponse(PaymentProposalBase):
    """Schema for payment proposal response"""
    id: uuid.UUID
    opportunity_id: Optional[uuid.UUID]
    match_id: Optional[uuid.UUID]
    proposer_id: uuid.UUID
    recipient_id: uuid.UUID
    status: str
    original_amount: Optional[float]
    counter_count: int
    is_ai_suggested: bool
    ai_confidence_score: Optional[float]
    accepted_at: Optional[datetime]
    rejected_at: Optional[datetime]
    proposal_metadata: Optional[dict]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaymentProposalListResponse(BaseModel):
    """Schema for paginated payment proposal list"""
    items: List[PaymentProposalResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class TransactionCreate(BaseModel):
    """Schema for creating a transaction"""
    proposal_id: uuid.UUID
    payment_method_id: Optional[str] = Field(None, description="Stripe payment method ID")


class TransactionResponse(BaseModel):
    """Schema for transaction response"""
    id: uuid.UUID
    proposal_id: uuid.UUID
    payer_id: uuid.UUID
    payee_id: uuid.UUID
    amount: float
    currency: str
    platform_fee: float
    net_amount: float
    status: str
    stripe_payment_intent_id: Optional[str]
    stripe_charge_id: Optional[str]
    stripe_transfer_id: Optional[str]
    payment_method_type: Optional[str]
    last_4_digits: Optional[str]
    error_message: Optional[str]
    retry_count: int
    refunded_amount: float
    refund_reason: Optional[str]
    transaction_metadata: Optional[dict]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class TransactionListResponse(BaseModel):
    """Schema for paginated transaction list"""
    items: List[TransactionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class StripePaymentIntentCreate(BaseModel):
    """Schema for creating Stripe payment intent"""
    amount: float = Field(..., ge=0)
    currency: str = Field(default="USD", max_length=3)
    payment_method_id: Optional[str] = None
    description: Optional[str] = None


class StripePaymentIntentResponse(BaseModel):
    """Schema for Stripe payment intent response"""
    client_secret: str
    payment_intent_id: str
    status: str
    amount: float
    currency: str


class RefundCreate(BaseModel):
    """Schema for creating a refund"""
    transaction_id: uuid.UUID
    amount: Optional[float] = Field(None, ge=0, description="Partial refund amount (None for full)")
    reason: Optional[str] = None


class AIPaymentSuggestion(BaseModel):
    """Schema for AI-suggested payment"""
    opportunity_id: Optional[uuid.UUID] = None
    match_id: Optional[uuid.UUID] = None
    suggested_amount: float
    confidence_score: float
    reasoning: str
    market_data: Optional[dict] = None
