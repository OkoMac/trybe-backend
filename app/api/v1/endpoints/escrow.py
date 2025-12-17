"""
Payment Escrow API Endpoints
Provides secure escrow services for opportunity-based work
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.services.escrow_service import escrow_service, EscrowStatus, DisputeStatus

router = APIRouter()


# ==================== Schemas ====================

class MilestoneCreate(BaseModel):
    """Schema for milestone creation"""
    title: str = Field(..., description="Milestone title")
    description: str = Field("", description="Milestone description")
    amount: Decimal = Field(..., gt=0, description="Milestone payment amount")
    due_date: Optional[datetime] = Field(None, description="Milestone due date")


class CreateEscrowRequest(BaseModel):
    """Request schema for creating escrow"""
    worker_id: str = Field(..., description="Worker/freelancer user ID")
    opportunity_id: str = Field(..., description="Related opportunity ID")
    amount: Decimal = Field(..., gt=0, description="Total amount to hold in escrow")
    currency: str = Field("USD", description="Currency code")
    description: str = Field(..., min_length=10, description="Work description")
    milestones: Optional[List[MilestoneCreate]] = Field(None, description="Optional milestone payments")
    auto_release_enabled: bool = Field(True, description="Enable auto-release after completion period")


class FundEscrowRequest(BaseModel):
    """Request schema for funding escrow"""
    payment_method_id: str = Field(..., description="Stripe payment method ID")


class ApproveWorkRequest(BaseModel):
    """Request schema for approving work"""
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating (1-5 stars)")
    review: Optional[str] = Field(None, description="Review text")


class RefundEscrowRequest(BaseModel):
    """Request schema for refund"""
    reason: str = Field(..., min_length=10, description="Refund reason")
    partial_amount: Optional[Decimal] = Field(None, gt=0, description="Partial refund amount")


class RaiseDisputeRequest(BaseModel):
    """Request schema for raising dispute"""
    reason: str = Field(..., description="Dispute reason category")
    description: str = Field(..., min_length=20, description="Detailed description")
    evidence: Optional[List[str]] = Field(None, description="Evidence URLs")


class ResolveDisputeRequest(BaseModel):
    """Request schema for resolving dispute (admin only)"""
    resolution: str = Field(..., description="Resolution type: worker, payer, split")
    resolution_notes: str = Field(..., min_length=10, description="Resolution explanation")
    payer_refund_percentage: Decimal = Field(Decimal("0"), ge=0, le=100)
    worker_payout_percentage: Decimal = Field(Decimal("100"), ge=0, le=100)


class CompleteMilestoneRequest(BaseModel):
    """Request schema for completing milestone"""
    milestone_index: int = Field(..., ge=0, description="Milestone index")


class EscrowResponse(BaseModel):
    """Response schema for escrow details"""
    id: str
    payer_id: str
    worker_id: str
    opportunity_id: str
    amount: float
    currency: str
    platform_fee: float
    worker_amount: float
    status: str
    description: str
    auto_release_enabled: bool
    created_at: str
    updated_at: str
    funded_at: Optional[str] = None
    completed_at: Optional[str] = None
    approved_at: Optional[str] = None
    released_at: Optional[str] = None
    auto_release_at: Optional[str] = None


# ==================== Escrow Management Endpoints ====================

@router.post("/", response_model=EscrowResponse, status_code=status.HTTP_201_CREATED)
async def create_escrow(
    request: CreateEscrowRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create an escrow transaction

    Creates a new escrow to hold payment securely until work is completed.

    Flow:
    1. Payer (employer/client) creates escrow
    2. Payer funds escrow with payment method
    3. Worker completes work
    4. Payer approves work
    5. Payment released to worker

    Features:
    - Platform fee calculated automatically (default 10%)
    - Optional milestone-based payments
    - Auto-release after completion period
    - Dispute resolution system

    Example:
    ```json
    {
      "worker_id": "user_456",
      "opportunity_id": "opp_789",
      "amount": 1000.00,
      "currency": "USD",
      "description": "Build a responsive landing page with React",
      "auto_release_enabled": true
    }
    ```

    Milestones example:
    ```json
    {
      "worker_id": "user_456",
      "opportunity_id": "opp_789",
      "amount": 1000.00,
      "description": "Full-stack web application",
      "milestones": [
        {
          "title": "Frontend Design",
          "amount": 300.00,
          "due_date": "2024-01-20T00:00:00Z"
        },
        {
          "title": "Backend API",
          "amount": 400.00,
          "due_date": "2024-01-27T00:00:00Z"
        },
        {
          "title": "Deployment",
          "amount": 300.00,
          "due_date": "2024-02-03T00:00:00Z"
        }
      ]
    }
    ```
    """
    try:
        # Convert milestones if provided
        milestones_data = None
        if request.milestones:
            milestones_data = [
                {
                    "title": m.title,
                    "description": m.description,
                    "amount": float(m.amount),
                    "due_date": m.due_date.isoformat() if m.due_date else None,
                    "status": "pending"
                }
                for m in request.milestones
            ]

        escrow = await escrow_service.create_escrow(
            db=db,
            payer_id=str(current_user.id),
            worker_id=request.worker_id,
            opportunity_id=request.opportunity_id,
            amount=request.amount,
            currency=request.currency,
            description=request.description,
            milestones=milestones_data,
            auto_release_enabled=request.auto_release_enabled
        )

        return EscrowResponse(**escrow)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create escrow: {str(e)}"
        )


@router.post("/{escrow_id}/fund", response_model=EscrowResponse)
async def fund_escrow(
    escrow_id: str,
    request: FundEscrowRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Fund an escrow transaction

    Transfers funds from payer to escrow account (held securely).

    Payment method can be obtained from Stripe Elements on the frontend.

    Example:
    ```json
    {
      "payment_method_id": "pm_1234567890abcdef"
    }
    ```

    Frontend integration (React):
    ```javascript
    // Create payment method using Stripe Elements
    const { paymentMethod } = await stripe.createPaymentMethod({
      type: 'card',
      card: cardElement,
    });

    // Fund escrow
    await axios.post(`/api/v1/escrow/${escrowId}/fund`, {
      payment_method_id: paymentMethod.id
    });
    ```
    """
    try:
        escrow = await escrow_service.fund_escrow(
            db=db,
            escrow_id=escrow_id,
            payment_method_id=request.payment_method_id,
            payer_email=current_user.email
        )

        return EscrowResponse(**escrow)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fund escrow: {str(e)}"
        )


@router.post("/{escrow_id}/start", response_model=EscrowResponse)
async def start_work(
    escrow_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Start work on an escrow (worker action)

    Marks the escrow as work in progress.
    Only the assigned worker can start work.

    Status transition: FUNDED → IN_PROGRESS
    """
    try:
        escrow = await escrow_service.start_work(
            db=db,
            escrow_id=escrow_id,
            worker_id=str(current_user.id)
        )

        return EscrowResponse(**escrow)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start work: {str(e)}"
        )


@router.post("/{escrow_id}/complete", response_model=EscrowResponse)
async def mark_completed(
    escrow_id: str,
    completion_notes: Optional[str] = None,
    deliverables: Optional[List[str]] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark work as completed (worker action)

    Worker submits completed work for payer review.
    Only the assigned worker can mark work as completed.

    Optional parameters:
    - completion_notes: Notes about the completion
    - deliverables: List of URLs to deliverables (GitHub repos, deployed sites, etc.)

    Status transition: IN_PROGRESS → COMPLETED

    After completion:
    - Payer has time to review and approve
    - Auto-release timer starts (if enabled)
    - Payer can approve or raise dispute
    """
    try:
        escrow = await escrow_service.mark_completed(
            db=db,
            escrow_id=escrow_id,
            worker_id=str(current_user.id),
            completion_notes=completion_notes,
            deliverables=deliverables
        )

        return EscrowResponse(**escrow)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark work as completed: {str(e)}"
        )


@router.post("/{escrow_id}/approve", response_model=EscrowResponse)
async def approve_work(
    escrow_id: str,
    request: ApproveWorkRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Approve completed work (payer action)

    Payer approves the work and triggers payment release.
    Only the payer can approve work.

    Optional:
    - rating: Rate the worker (1-5 stars)
    - review: Leave a review

    Status transition: COMPLETED → APPROVED → RELEASED

    Actions triggered:
    1. Work marked as approved
    2. Payment automatically released to worker
    3. Rating and review recorded
    4. Worker notified
    """
    try:
        escrow = await escrow_service.approve_work(
            db=db,
            escrow_id=escrow_id,
            payer_id=str(current_user.id),
            rating=request.rating,
            review=request.review
        )

        return EscrowResponse(**escrow)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve work: {str(e)}"
        )


@router.post("/{escrow_id}/release", response_model=EscrowResponse)
async def release_payment(
    escrow_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Release payment to worker

    Can be triggered by:
    - Payer after approving work
    - System after auto-release timeout
    - Admin for dispute resolution

    Actions:
    1. Capture Stripe payment
    2. Transfer funds to worker's account
    3. Record platform fee
    4. Update escrow status to RELEASED
    5. Send notifications
    """
    try:
        escrow = await escrow_service.release_payment(
            db=db,
            escrow_id=escrow_id,
            requester_id=str(current_user.id),
            is_admin=current_user.user_type == "admin"
        )

        return EscrowResponse(**escrow)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to release payment: {str(e)}"
        )


@router.post("/{escrow_id}/refund", response_model=EscrowResponse)
async def refund_escrow(
    escrow_id: str,
    request: RefundEscrowRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Refund escrow to payer

    Can be used when:
    - Work hasn't started (full refund)
    - Dispute resolved in payer's favor
    - Mutual agreement to cancel
    - Partial refund for incomplete work

    Only payer or admin can request refund.

    Example:
    ```json
    {
      "reason": "Project requirements changed and work no longer needed",
      "partial_amount": 500.00
    }
    ```
    """
    try:
        escrow = await escrow_service.refund_escrow(
            db=db,
            escrow_id=escrow_id,
            requester_id=str(current_user.id),
            reason=request.reason,
            is_admin=current_user.user_type == "admin",
            partial_amount=request.partial_amount
        )

        return EscrowResponse(**escrow)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refund escrow: {str(e)}"
        )


# ==================== Dispute Management ====================

@router.post("/{escrow_id}/dispute", status_code=status.HTTP_201_CREATED)
async def raise_dispute(
    escrow_id: str,
    request: RaiseDisputeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Raise a dispute on an escrow transaction

    Either payer or worker can raise a dispute if:
    - Work quality doesn't meet expectations
    - Scope creep or requirements changed
    - Communication breakdown
    - Payment concerns

    Common dispute reasons:
    - "incomplete_work" - Work not fully completed
    - "poor_quality" - Quality doesn't meet standards
    - "scope_change" - Requirements changed mid-project
    - "communication_issues" - Unable to reach other party
    - "payment_delay" - Payment not released when due
    - "other" - Other reason (provide details)

    Evidence can include:
    - Screenshots
    - Communication logs
    - Deliverable URLs
    - Documentation

    Example:
    ```json
    {
      "reason": "incomplete_work",
      "description": "Only 60% of the agreed features were implemented. Missing user authentication and payment integration.",
      "evidence": [
        "https://example.com/screenshots/missing-features.png",
        "https://github.com/user/repo/issues/123"
      ]
    }
    ```

    After raising dispute:
    - Escrow status changes to DISPUTED
    - Funds remain held
    - Admin reviews evidence
    - Both parties can add evidence
    - Admin makes final decision
    """
    try:
        dispute = await escrow_service.raise_dispute(
            db=db,
            escrow_id=escrow_id,
            raised_by_id=str(current_user.id),
            reason=request.reason,
            description=request.description,
            evidence=request.evidence
        )

        return dispute

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to raise dispute: {str(e)}"
        )


@router.post("/disputes/{dispute_id}/resolve", status_code=status.HTTP_200_OK)
async def resolve_dispute(
    dispute_id: str,
    request: ResolveDisputeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Resolve a dispute (Admin only)

    Admin reviews evidence and makes a decision:

    1. **Worker favor (100% to worker)**
       ```json
       {
         "resolution": "worker",
         "resolution_notes": "Work was completed as agreed. Releasing full payment.",
         "payer_refund_percentage": 0,
         "worker_payout_percentage": 100
       }
       ```

    2. **Payer favor (100% refund to payer)**
       ```json
       {
         "resolution": "payer",
         "resolution_notes": "Work was not completed. Issuing full refund.",
         "payer_refund_percentage": 100,
         "worker_payout_percentage": 0
       }
       ```

    3. **Split decision (partial to both)**
       ```json
       {
         "resolution": "split",
         "resolution_notes": "Work was 70% complete. Split payment accordingly.",
         "payer_refund_percentage": 30,
         "worker_payout_percentage": 70
       }
       ```

    Note: Percentages must add up to 100
    """
    # Check admin permissions
    if current_user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can resolve disputes"
        )

    try:
        # Validate percentages
        total = request.payer_refund_percentage + request.worker_payout_percentage
        if total != Decimal("100"):
            raise ValueError(f"Percentages must add up to 100. Current total: {total}")

        result = await escrow_service.resolve_dispute(
            db=db,
            dispute_id=dispute_id,
            admin_id=str(current_user.id),
            resolution=request.resolution,
            resolution_notes=request.resolution_notes,
            payer_refund_percentage=request.payer_refund_percentage,
            worker_payout_percentage=request.worker_payout_percentage
        )

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve dispute: {str(e)}"
        )


# ==================== Milestone Management ====================

@router.post("/{escrow_id}/milestones/complete", status_code=status.HTTP_200_OK)
async def complete_milestone(
    escrow_id: str,
    request: CompleteMilestoneRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark a milestone as completed (worker action)

    For escrows with milestone-based payments.

    Example:
    ```json
    {
      "milestone_index": 0
    }
    ```

    Flow:
    1. Worker completes milestone
    2. Payer reviews milestone
    3. Payer approves milestone
    4. Milestone payment released
    5. Work continues to next milestone
    """
    try:
        milestone = await escrow_service.complete_milestone(
            db=db,
            escrow_id=escrow_id,
            milestone_index=request.milestone_index,
            worker_id=str(current_user.id)
        )

        return milestone

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete milestone: {str(e)}"
        )


# ==================== Query Endpoints ====================

@router.get("/{escrow_id}", response_model=EscrowResponse)
async def get_escrow(
    escrow_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get escrow details

    Returns full escrow information including:
    - Transaction details
    - Current status
    - Milestone progress
    - Payment information
    - Timestamps
    """
    try:
        # TODO: Get from database and check authorization
        escrow = await escrow_service._get_escrow(db, escrow_id)
        return EscrowResponse(**escrow)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get escrow: {str(e)}"
        )


@router.get("/", response_model=List[EscrowResponse])
async def list_escrows(
    status_filter: Optional[str] = Query(None, alias="status"),
    role: str = Query("all", description="Filter by role: payer, worker, all"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List escrow transactions

    Filters:
    - **status**: pending, funded, in_progress, completed, approved, released, disputed, cancelled, refunded
    - **role**: payer (as employer), worker (as freelancer), all
    - **limit**: Max results (1-100)
    - **offset**: Pagination offset

    Examples:
    - Get all my escrows as worker: `?role=worker`
    - Get all funded escrows as payer: `?role=payer&status=funded`
    - Get disputed escrows: `?status=disputed`
    """
    try:
        # TODO: Implement actual database query with filters
        # For now, return empty list
        return []

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list escrows: {str(e)}"
        )


@router.get("/stats/me")
async def get_my_escrow_stats(
    role: str = Query("all", description="Stats for role: payer, worker, all"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get escrow statistics for current user

    Returns:
    - Total escrows
    - Total amount
    - Status breakdown
    - Success rate
    - Average amount
    - Dispute rate

    Example response:
    ```json
    {
      "total_escrows": 25,
      "total_amount": 45000.00,
      "pending": 2,
      "in_progress": 5,
      "completed": 3,
      "released": 14,
      "disputed": 1,
      "success_rate": 0.92,
      "average_amount": 1800.00,
      "dispute_rate": 0.04
    }
    ```
    """
    try:
        stats = await escrow_service.get_escrow_stats(
            db=db,
            user_id=str(current_user.id),
            role=role
        )

        return stats

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}"
        )


@router.get("/health")
async def escrow_health_check():
    """
    Check escrow service health

    Returns service status and configuration
    """
    return {
        "status": "healthy",
        "service": "Payment Escrow",
        "platform_fee_percentage": float(escrow_service.platform_fee_percentage),
        "auto_release_days": escrow_service.auto_release_days,
        "dispute_resolution_days": escrow_service.dispute_resolution_days
    }
