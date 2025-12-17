"""Payment endpoints - Payment proposals and Stripe integration"""

from datetime import datetime
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from math import ceil
import stripe

from app.core.database import get_db
from app.core.config import settings
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.payment import (
    PaymentProposal,
    Transaction,
    PaymentStatusEnum,
    TransactionStatusEnum
)
from app.schemas.payment import (
    PaymentProposalCreate,
    PaymentProposalUpdate,
    PaymentProposalCounter,
    PaymentProposalResponse,
    PaymentProposalListResponse,
    TransactionCreate,
    TransactionResponse,
    TransactionListResponse,
    StripePaymentIntentCreate,
    StripePaymentIntentResponse,
    RefundCreate
)

router = APIRouter()

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


@router.post("/proposals", response_model=PaymentProposalResponse, status_code=status.HTTP_201_CREATED)
async def create_payment_proposal(
    proposal_data: PaymentProposalCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Create a new payment proposal

    - **payment_type**: hourly, fixed, milestone, or commission
    - **amount**: Proposed payment amount
    - **recipient_id**: User who will receive the proposal
    """
    # Create new proposal
    new_proposal = PaymentProposal(
        proposer_id=current_user.id,
        **proposal_data.model_dump()
    )

    db.add(new_proposal)
    await db.commit()
    await db.refresh(new_proposal)

    return PaymentProposalResponse.model_validate(new_proposal)


@router.get("/proposals", response_model=PaymentProposalListResponse)
async def list_payment_proposals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str = Query("all", pattern="^(proposed|accepted|rejected|in_progress|completed|paid|all)$"),
    proposal_type: str = Query("all", pattern="^(sent|received|all)$"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    List payment proposals

    - **proposal_type**: sent (proposals I made), received (proposals I received), or all
    - **status_filter**: Filter by status
    """
    # Build query
    query = select(PaymentProposal)

    # Apply type filter
    if proposal_type == "sent":
        query = query.where(PaymentProposal.proposer_id == current_user.id)
    elif proposal_type == "received":
        query = query.where(PaymentProposal.recipient_id == current_user.id)
    else:  # all
        query = query.where(
            or_(
                PaymentProposal.proposer_id == current_user.id,
                PaymentProposal.recipient_id == current_user.id
            )
        )

    # Apply status filter
    if status_filter != "all":
        query = query.where(PaymentProposal.status == status_filter)

    # Order by created_at descending
    query = query.order_by(PaymentProposal.created_at.desc())

    # Get total count
    count_query = select(func.count()).select_from(PaymentProposal)
    if proposal_type == "sent":
        count_query = count_query.where(PaymentProposal.proposer_id == current_user.id)
    elif proposal_type == "received":
        count_query = count_query.where(PaymentProposal.recipient_id == current_user.id)
    else:
        count_query = count_query.where(
            or_(
                PaymentProposal.proposer_id == current_user.id,
                PaymentProposal.recipient_id == current_user.id
            )
        )
    if status_filter != "all":
        count_query = count_query.where(PaymentProposal.status == status_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    proposals = result.scalars().all()

    return PaymentProposalListResponse(
        items=[PaymentProposalResponse.model_validate(p) for p in proposals],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total > 0 else 0
    )


@router.get("/proposals/{proposal_id}", response_model=PaymentProposalResponse)
async def get_payment_proposal(
    proposal_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get a specific payment proposal
    """
    # Fetch proposal
    result = await db.execute(
        select(PaymentProposal).where(PaymentProposal.id == proposal_id)
    )
    proposal = result.scalar_one_or_none()

    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment proposal not found"
        )

    # Check authorization (proposer or recipient)
    if proposal.proposer_id != current_user.id and proposal.recipient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this proposal"
        )

    return PaymentProposalResponse.model_validate(proposal)


@router.post("/proposals/{proposal_id}/accept", response_model=PaymentProposalResponse)
async def accept_payment_proposal(
    proposal_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Accept a payment proposal
    """
    # Fetch proposal
    result = await db.execute(
        select(PaymentProposal).where(PaymentProposal.id == proposal_id)
    )
    proposal = result.scalar_one_or_none()

    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment proposal not found"
        )

    # Check authorization (must be recipient)
    if proposal.recipient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the recipient can accept the proposal"
        )

    # Check if already accepted or rejected
    if proposal.status in [PaymentStatusEnum.accepted, PaymentStatusEnum.rejected]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Proposal already {proposal.status}"
        )

    # Update proposal
    proposal.status = PaymentStatusEnum.accepted
    proposal.accepted_at = datetime.utcnow()

    await db.commit()
    await db.refresh(proposal)

    return PaymentProposalResponse.model_validate(proposal)


@router.post("/proposals/{proposal_id}/reject", response_model=PaymentProposalResponse)
async def reject_payment_proposal(
    proposal_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Reject a payment proposal
    """
    # Fetch proposal
    result = await db.execute(
        select(PaymentProposal).where(PaymentProposal.id == proposal_id)
    )
    proposal = result.scalar_one_or_none()

    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment proposal not found"
        )

    # Check authorization (must be recipient)
    if proposal.recipient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the recipient can reject the proposal"
        )

    # Update proposal
    proposal.status = PaymentStatusEnum.rejected
    proposal.rejected_at = datetime.utcnow()

    await db.commit()
    await db.refresh(proposal)

    return PaymentProposalResponse.model_validate(proposal)


@router.post("/proposals/{proposal_id}/counter", response_model=PaymentProposalResponse)
async def counter_payment_proposal(
    proposal_id: str,
    counter_data: PaymentProposalCounter,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Make a counter proposal
    """
    # Fetch original proposal
    result = await db.execute(
        select(PaymentProposal).where(PaymentProposal.id == proposal_id)
    )
    proposal = result.scalar_one_or_none()

    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment proposal not found"
        )

    # Check authorization (must be recipient)
    if proposal.recipient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the recipient can counter the proposal"
        )

    # Store original amount if first counter
    if proposal.counter_count == 0:
        proposal.original_amount = proposal.amount

    # Update proposal with counter
    proposal.amount = counter_data.amount
    if counter_data.description:
        proposal.description = counter_data.description
    if counter_data.terms:
        proposal.terms = counter_data.terms
    proposal.status = PaymentStatusEnum.counter_proposed
    proposal.counter_count += 1

    await db.commit()
    await db.refresh(proposal)

    return PaymentProposalResponse.model_validate(proposal)


@router.post("/transactions", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    transaction_data: TransactionCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Create a payment transaction via Stripe

    Requires an accepted payment proposal
    """
    # Fetch proposal
    result = await db.execute(
        select(PaymentProposal).where(PaymentProposal.id == transaction_data.proposal_id)
    )
    proposal = result.scalar_one_or_none()

    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment proposal not found"
        )

    # Check if proposal is accepted
    if proposal.status != PaymentStatusEnum.accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only create transaction for accepted proposals"
        )

    # Check authorization (payer must be proposer or recipient)
    if current_user.id not in [proposal.proposer_id, proposal.recipient_id]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for this transaction"
        )

    # Calculate platform fee (5% for now - should be configurable)
    platform_fee = float(proposal.amount) * 0.05
    net_amount = float(proposal.amount) - platform_fee

    # Determine payer and payee
    # Usually employer pays professional
    payer_id = proposal.proposer_id
    payee_id = proposal.recipient_id

    # Create transaction
    new_transaction = Transaction(
        proposal_id=proposal.id,
        payer_id=payer_id,
        payee_id=payee_id,
        amount=float(proposal.amount),
        currency=proposal.currency,
        platform_fee=platform_fee,
        net_amount=net_amount,
        status=TransactionStatusEnum.pending
    )

    try:
        # Create Stripe PaymentIntent
        payment_intent = stripe.PaymentIntent.create(
            amount=int(float(proposal.amount) * 100),  # Stripe uses cents
            currency=proposal.currency.lower(),
            payment_method=transaction_data.payment_method_id,
            confirm=True if transaction_data.payment_method_id else False,
            description=f"Payment for proposal {proposal.id}",
            metadata={
                "proposal_id": str(proposal.id),
                "payer_id": str(payer_id),
                "payee_id": str(payee_id)
            }
        )

        new_transaction.stripe_payment_intent_id = payment_intent.id
        new_transaction.status = TransactionStatusEnum.processing

    except stripe.error.StripeError as e:
        new_transaction.status = TransactionStatusEnum.failed
        new_transaction.error_message = str(e)

    db.add(new_transaction)

    # Update proposal status
    proposal.status = PaymentStatusEnum.in_progress

    await db.commit()
    await db.refresh(new_transaction)

    return TransactionResponse.model_validate(new_transaction)


@router.get("/transactions", response_model=TransactionListResponse)
async def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str = Query("all", pattern="^(pending|processing|succeeded|failed|refunded|all)$"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    List payment transactions
    """
    # Build query - user can see transactions they're involved in
    query = select(Transaction).where(
        or_(
            Transaction.payer_id == current_user.id,
            Transaction.payee_id == current_user.id
        )
    )

    # Apply status filter
    if status_filter != "all":
        query = query.where(Transaction.status == status_filter)

    # Order by created_at descending
    query = query.order_by(Transaction.created_at.desc())

    # Get total count
    count_query = select(func.count()).select_from(Transaction).where(
        or_(
            Transaction.payer_id == current_user.id,
            Transaction.payee_id == current_user.id
        )
    )
    if status_filter != "all":
        count_query = count_query.where(Transaction.status == status_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    transactions = result.scalars().all()

    return TransactionListResponse(
        items=[TransactionResponse.model_validate(t) for t in transactions],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total > 0 else 0
    )


@router.post("/stripe/payment-intent", response_model=StripePaymentIntentResponse)
async def create_payment_intent(
    intent_data: StripePaymentIntentCreate,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Create a Stripe payment intent for frontend

    Returns client_secret for frontend Stripe.js confirmation
    """
    try:
        payment_intent = stripe.PaymentIntent.create(
            amount=int(intent_data.amount * 100),  # Convert to cents
            currency=intent_data.currency.lower(),
            payment_method=intent_data.payment_method_id,
            description=intent_data.description,
            metadata={"user_id": str(current_user.id)}
        )

        return StripePaymentIntentResponse(
            client_secret=payment_intent.client_secret,
            payment_intent_id=payment_intent.id,
            status=payment_intent.status,
            amount=intent_data.amount,
            currency=intent_data.currency
        )

    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
