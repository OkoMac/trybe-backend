"""
Payment Escrow Service for Trybe Platform
Provides secure payment escrow for opportunity-based work
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import logging
import os
from enum import Enum

from app.models.user import User
from app.services.payment_service import payment_service

logger = logging.getLogger(__name__)


class EscrowStatus(str, Enum):
    """Escrow transaction states"""
    PENDING = "pending"  # Created but not funded
    FUNDED = "funded"  # Payment held in escrow
    IN_PROGRESS = "in_progress"  # Work in progress
    COMPLETED = "completed"  # Work completed, awaiting approval
    APPROVED = "approved"  # Approved, ready for release
    RELEASED = "released"  # Payment released to worker
    DISPUTED = "disputed"  # Dispute raised
    CANCELLED = "cancelled"  # Cancelled before funding
    REFUNDED = "refunded"  # Refunded to payer


class DisputeStatus(str, Enum):
    """Dispute states"""
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED_WORKER = "resolved_worker"  # Resolved in favor of worker
    RESOLVED_PAYER = "resolved_payer"  # Resolved in favor of payer
    RESOLVED_SPLIT = "resolved_split"  # Split payment


class EscrowService:
    """Service for managing escrow transactions"""

    def __init__(self):
        """Initialize escrow service"""
        self.platform_fee_percentage = Decimal(os.getenv("PLATFORM_FEE_PERCENTAGE", "10.0"))
        self.dispute_resolution_days = int(os.getenv("DISPUTE_RESOLUTION_DAYS", "7"))
        self.auto_release_days = int(os.getenv("AUTO_RELEASE_DAYS", "14"))

    # ==================== Escrow Transaction Management ====================

    async def create_escrow(
        self,
        db: AsyncSession,
        payer_id: str,
        worker_id: str,
        opportunity_id: str,
        amount: Decimal,
        currency: str = "USD",
        description: str = "",
        milestones: Optional[List[Dict[str, Any]]] = None,
        auto_release_enabled: bool = True
    ) -> Dict[str, Any]:
        """
        Create an escrow transaction

        Args:
            db: Database session
            payer_id: User ID of payer (employer/client)
            worker_id: User ID of worker (freelancer/contractor)
            opportunity_id: Related opportunity ID
            amount: Total amount to hold in escrow
            currency: Currency code (USD, EUR, etc.)
            description: Description of work
            milestones: Optional list of milestone payments
            auto_release_enabled: Auto-release after completion period

        Returns:
            Escrow transaction details
        """
        try:
            # Calculate platform fee
            platform_fee = amount * (self.platform_fee_percentage / Decimal(100))
            worker_amount = amount - platform_fee

            # Create escrow record
            escrow = {
                "id": self._generate_escrow_id(),
                "payer_id": payer_id,
                "worker_id": worker_id,
                "opportunity_id": opportunity_id,
                "amount": float(amount),
                "currency": currency,
                "platform_fee": float(platform_fee),
                "worker_amount": float(worker_amount),
                "status": EscrowStatus.PENDING,
                "description": description,
                "auto_release_enabled": auto_release_enabled,
                "milestones": milestones or [],
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "payment_intent_id": None,
                "stripe_charge_id": None,
                "funded_at": None,
                "completed_at": None,
                "approved_at": None,
                "released_at": None,
                "auto_release_at": None
            }

            # TODO: Save to database
            # For now, store in a dict (in production, use proper DB model)
            logger.info(f"Created escrow transaction: {escrow['id']}")

            return escrow

        except Exception as e:
            logger.error(f"Failed to create escrow: {str(e)}")
            raise

    async def fund_escrow(
        self,
        db: AsyncSession,
        escrow_id: str,
        payment_method_id: str,
        payer_email: str
    ) -> Dict[str, Any]:
        """
        Fund an escrow transaction

        Creates a Stripe payment intent to hold funds in escrow

        Args:
            db: Database session
            escrow_id: Escrow transaction ID
            payment_method_id: Stripe payment method ID
            payer_email: Payer's email

        Returns:
            Updated escrow with payment details
        """
        try:
            # TODO: Get escrow from database
            escrow = await self._get_escrow(db, escrow_id)

            if escrow["status"] != EscrowStatus.PENDING:
                raise ValueError(f"Escrow must be in PENDING status to fund. Current: {escrow['status']}")

            # Create Stripe payment intent
            # We'll capture it later when releasing funds
            amount_cents = int(Decimal(str(escrow["amount"])) * 100)

            payment_intent = await payment_service.create_payment_intent(
                amount=amount_cents,
                currency=escrow["currency"],
                payment_method_id=payment_method_id,
                customer_email=payer_email,
                description=f"Escrow for {escrow['description']}",
                capture_method="manual",  # Don't capture immediately
                metadata={
                    "escrow_id": escrow_id,
                    "opportunity_id": escrow["opportunity_id"],
                    "type": "escrow"
                }
            )

            # Update escrow
            escrow["payment_intent_id"] = payment_intent.get("id")
            escrow["status"] = EscrowStatus.FUNDED
            escrow["funded_at"] = datetime.utcnow().isoformat()
            escrow["updated_at"] = datetime.utcnow().isoformat()

            # TODO: Update in database

            logger.info(f"Funded escrow {escrow_id}: {escrow['amount']} {escrow['currency']}")

            return escrow

        except Exception as e:
            logger.error(f"Failed to fund escrow {escrow_id}: {str(e)}")
            raise

    async def start_work(
        self,
        db: AsyncSession,
        escrow_id: str,
        worker_id: str
    ) -> Dict[str, Any]:
        """
        Mark escrow as work in progress

        Args:
            db: Database session
            escrow_id: Escrow transaction ID
            worker_id: Worker ID (for authorization)

        Returns:
            Updated escrow
        """
        try:
            escrow = await self._get_escrow(db, escrow_id)

            # Verify authorization
            if escrow["worker_id"] != worker_id:
                raise ValueError("Only the assigned worker can start work")

            if escrow["status"] != EscrowStatus.FUNDED:
                raise ValueError(f"Escrow must be FUNDED to start work. Current: {escrow['status']}")

            # Update status
            escrow["status"] = EscrowStatus.IN_PROGRESS
            escrow["started_at"] = datetime.utcnow().isoformat()
            escrow["updated_at"] = datetime.utcnow().isoformat()

            # TODO: Update in database

            logger.info(f"Started work on escrow {escrow_id}")

            return escrow

        except Exception as e:
            logger.error(f"Failed to start work on escrow {escrow_id}: {str(e)}")
            raise

    async def mark_completed(
        self,
        db: AsyncSession,
        escrow_id: str,
        worker_id: str,
        completion_notes: Optional[str] = None,
        deliverables: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Mark work as completed by worker

        Args:
            db: Database session
            escrow_id: Escrow transaction ID
            worker_id: Worker ID (for authorization)
            completion_notes: Notes about completion
            deliverables: List of deliverable URLs/IDs

        Returns:
            Updated escrow
        """
        try:
            escrow = await self._get_escrow(db, escrow_id)

            # Verify authorization
            if escrow["worker_id"] != worker_id:
                raise ValueError("Only the assigned worker can mark work as completed")

            if escrow["status"] != EscrowStatus.IN_PROGRESS:
                raise ValueError(f"Escrow must be IN_PROGRESS. Current: {escrow['status']}")

            # Update status
            escrow["status"] = EscrowStatus.COMPLETED
            escrow["completed_at"] = datetime.utcnow().isoformat()
            escrow["completion_notes"] = completion_notes
            escrow["deliverables"] = deliverables or []
            escrow["updated_at"] = datetime.utcnow().isoformat()

            # Set auto-release date if enabled
            if escrow["auto_release_enabled"]:
                auto_release_date = datetime.utcnow() + timedelta(days=self.auto_release_days)
                escrow["auto_release_at"] = auto_release_date.isoformat()

            # TODO: Update in database
            # TODO: Send notification to payer for review

            logger.info(f"Marked escrow {escrow_id} as completed")

            return escrow

        except Exception as e:
            logger.error(f"Failed to mark escrow {escrow_id} as completed: {str(e)}")
            raise

    async def approve_work(
        self,
        db: AsyncSession,
        escrow_id: str,
        payer_id: str,
        rating: Optional[int] = None,
        review: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Approve completed work (by payer)

        Args:
            db: Database session
            escrow_id: Escrow transaction ID
            payer_id: Payer ID (for authorization)
            rating: Optional rating (1-5)
            review: Optional review text

        Returns:
            Updated escrow
        """
        try:
            escrow = await self._get_escrow(db, escrow_id)

            # Verify authorization
            if escrow["payer_id"] != payer_id:
                raise ValueError("Only the payer can approve work")

            if escrow["status"] != EscrowStatus.COMPLETED:
                raise ValueError(f"Escrow must be COMPLETED. Current: {escrow['status']}")

            # Update status
            escrow["status"] = EscrowStatus.APPROVED
            escrow["approved_at"] = datetime.utcnow().isoformat()
            escrow["rating"] = rating
            escrow["review"] = review
            escrow["updated_at"] = datetime.utcnow().isoformat()

            # TODO: Update in database
            # TODO: Trigger automatic release

            logger.info(f"Approved escrow {escrow_id}")

            # Auto-release immediately upon approval
            return await self.release_payment(db, escrow_id, payer_id)

        except Exception as e:
            logger.error(f"Failed to approve escrow {escrow_id}: {str(e)}")
            raise

    async def release_payment(
        self,
        db: AsyncSession,
        escrow_id: str,
        requester_id: str,
        is_admin: bool = False
    ) -> Dict[str, Any]:
        """
        Release payment to worker

        Can be triggered by:
        - Payer after approving work
        - Auto-release after timeout
        - Admin for dispute resolution

        Args:
            db: Database session
            escrow_id: Escrow transaction ID
            requester_id: ID of user requesting release
            is_admin: Whether requester is admin

        Returns:
            Updated escrow with payout details
        """
        try:
            escrow = await self._get_escrow(db, escrow_id)

            # Authorization check
            if not is_admin and escrow["payer_id"] != requester_id:
                raise ValueError("Only payer or admin can release payment")

            if escrow["status"] not in [EscrowStatus.APPROVED, EscrowStatus.COMPLETED]:
                raise ValueError(f"Cannot release payment. Status: {escrow['status']}")

            # Capture the payment intent
            if escrow["payment_intent_id"]:
                captured_payment = await payment_service.capture_payment_intent(
                    escrow["payment_intent_id"]
                )
                escrow["stripe_charge_id"] = captured_payment.get("id")

            # Transfer funds to worker
            # TODO: Implement Stripe Connect transfer to worker's account
            # For now, we'll mark as released
            worker_payout = await self._payout_to_worker(
                worker_id=escrow["worker_id"],
                amount=Decimal(str(escrow["worker_amount"])),
                currency=escrow["currency"],
                escrow_id=escrow_id
            )

            # Update escrow
            escrow["status"] = EscrowStatus.RELEASED
            escrow["released_at"] = datetime.utcnow().isoformat()
            escrow["payout_id"] = worker_payout.get("id")
            escrow["updated_at"] = datetime.utcnow().isoformat()

            # TODO: Update in database
            # TODO: Send notifications

            logger.info(f"Released payment for escrow {escrow_id}: {escrow['worker_amount']} {escrow['currency']}")

            return escrow

        except Exception as e:
            logger.error(f"Failed to release payment for escrow {escrow_id}: {str(e)}")
            raise

    async def refund_escrow(
        self,
        db: AsyncSession,
        escrow_id: str,
        requester_id: str,
        reason: str,
        is_admin: bool = False,
        partial_amount: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Refund escrow to payer

        Args:
            db: Database session
            escrow_id: Escrow transaction ID
            requester_id: ID of user requesting refund
            reason: Reason for refund
            is_admin: Whether requester is admin
            partial_amount: Optional partial refund amount

        Returns:
            Updated escrow with refund details
        """
        try:
            escrow = await self._get_escrow(db, escrow_id)

            # Authorization check
            if not is_admin:
                # Payer can request refund for FUNDED or DISPUTED status
                if escrow["payer_id"] != requester_id:
                    raise ValueError("Only payer or admin can request refund")

                if escrow["status"] not in [EscrowStatus.FUNDED, EscrowStatus.DISPUTED]:
                    raise ValueError(f"Cannot refund escrow. Status: {escrow['status']}")

            # Calculate refund amount
            refund_amount = partial_amount or Decimal(str(escrow["amount"]))

            # Process refund through Stripe
            if escrow["payment_intent_id"]:
                refund = await payment_service.refund_payment(
                    payment_intent_id=escrow["payment_intent_id"],
                    amount=int(refund_amount * 100),
                    reason=reason
                )
                refund_id = refund.get("id")
            else:
                refund_id = None

            # Update escrow
            escrow["status"] = EscrowStatus.REFUNDED
            escrow["refunded_at"] = datetime.utcnow().isoformat()
            escrow["refund_id"] = refund_id
            escrow["refund_amount"] = float(refund_amount)
            escrow["refund_reason"] = reason
            escrow["updated_at"] = datetime.utcnow().isoformat()

            # TODO: Update in database
            # TODO: Send notifications

            logger.info(f"Refunded escrow {escrow_id}: {refund_amount} {escrow['currency']}")

            return escrow

        except Exception as e:
            logger.error(f"Failed to refund escrow {escrow_id}: {str(e)}")
            raise

    # ==================== Dispute Management ====================

    async def raise_dispute(
        self,
        db: AsyncSession,
        escrow_id: str,
        raised_by_id: str,
        reason: str,
        description: str,
        evidence: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Raise a dispute on an escrow transaction

        Args:
            db: Database session
            escrow_id: Escrow transaction ID
            raised_by_id: User ID raising the dispute
            reason: Dispute reason category
            description: Detailed description
            evidence: List of evidence URLs

        Returns:
            Dispute details
        """
        try:
            escrow = await self._get_escrow(db, escrow_id)

            # Verify the user is involved in the transaction
            if raised_by_id not in [escrow["payer_id"], escrow["worker_id"]]:
                raise ValueError("Only payer or worker can raise a dispute")

            if escrow["status"] in [EscrowStatus.RELEASED, EscrowStatus.REFUNDED, EscrowStatus.CANCELLED]:
                raise ValueError(f"Cannot dispute escrow. Status: {escrow['status']}")

            # Create dispute
            dispute = {
                "id": self._generate_dispute_id(),
                "escrow_id": escrow_id,
                "raised_by_id": raised_by_id,
                "raised_by_role": "payer" if raised_by_id == escrow["payer_id"] else "worker",
                "reason": reason,
                "description": description,
                "evidence": evidence or [],
                "status": DisputeStatus.OPEN,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "resolution": None,
                "resolved_at": None,
                "resolved_by_id": None
            }

            # Update escrow status
            escrow["status"] = EscrowStatus.DISPUTED
            escrow["dispute_id"] = dispute["id"]
            escrow["updated_at"] = datetime.utcnow().isoformat()

            # TODO: Save dispute and update escrow in database
            # TODO: Send notifications to both parties and admins

            logger.info(f"Dispute raised on escrow {escrow_id} by {raised_by_id}")

            return dispute

        except Exception as e:
            logger.error(f"Failed to raise dispute on escrow {escrow_id}: {str(e)}")
            raise

    async def resolve_dispute(
        self,
        db: AsyncSession,
        dispute_id: str,
        admin_id: str,
        resolution: str,
        resolution_notes: str,
        payer_refund_percentage: Decimal = Decimal("0"),
        worker_payout_percentage: Decimal = Decimal("100")
    ) -> Dict[str, Any]:
        """
        Resolve a dispute (admin only)

        Args:
            db: Database session
            dispute_id: Dispute ID
            admin_id: Admin user ID
            resolution: Resolution type (worker, payer, split)
            resolution_notes: Explanation of resolution
            payer_refund_percentage: Percentage to refund to payer (0-100)
            worker_payout_percentage: Percentage to pay worker (0-100)

        Returns:
            Resolved dispute details
        """
        try:
            # TODO: Get dispute from database
            # TODO: Verify admin_id has admin permissions

            # Get associated escrow
            # escrow = await self._get_escrow(db, dispute["escrow_id"])

            # Calculate amounts
            # total_amount = Decimal(str(escrow["amount"]))
            # payer_refund = total_amount * (payer_refund_percentage / Decimal(100))
            # worker_payout = total_amount * (worker_payout_percentage / Decimal(100))

            # TODO: Process split payment/refund
            # TODO: Update dispute status
            # TODO: Update escrow status
            # TODO: Send notifications

            logger.info(f"Resolved dispute {dispute_id}: {resolution}")

            return {
                "dispute_id": dispute_id,
                "resolution": resolution,
                "message": "Dispute resolved successfully"
            }

        except Exception as e:
            logger.error(f"Failed to resolve dispute {dispute_id}: {str(e)}")
            raise

    # ==================== Milestone Management ====================

    async def complete_milestone(
        self,
        db: AsyncSession,
        escrow_id: str,
        milestone_index: int,
        worker_id: str
    ) -> Dict[str, Any]:
        """
        Mark a milestone as completed

        Args:
            db: Database session
            escrow_id: Escrow transaction ID
            milestone_index: Index of milestone (0-based)
            worker_id: Worker ID (for authorization)

        Returns:
            Updated milestone details
        """
        try:
            escrow = await self._get_escrow(db, escrow_id)

            if escrow["worker_id"] != worker_id:
                raise ValueError("Only the assigned worker can complete milestones")

            milestones = escrow.get("milestones", [])
            if milestone_index >= len(milestones):
                raise ValueError(f"Invalid milestone index: {milestone_index}")

            milestone = milestones[milestone_index]
            milestone["status"] = "completed"
            milestone["completed_at"] = datetime.utcnow().isoformat()

            escrow["milestones"] = milestones
            escrow["updated_at"] = datetime.utcnow().isoformat()

            # TODO: Update in database
            # TODO: Send notification to payer

            logger.info(f"Completed milestone {milestone_index} for escrow {escrow_id}")

            return milestone

        except Exception as e:
            logger.error(f"Failed to complete milestone: {str(e)}")
            raise

    # ==================== Helper Methods ====================

    async def _get_escrow(self, db: AsyncSession, escrow_id: str) -> Dict[str, Any]:
        """Get escrow from database"""
        # TODO: Implement actual database query
        # For now, return mock data
        return {
            "id": escrow_id,
            "payer_id": "user_123",
            "worker_id": "user_456",
            "opportunity_id": "opp_789",
            "amount": 1000.0,
            "currency": "USD",
            "platform_fee": 100.0,
            "worker_amount": 900.0,
            "status": EscrowStatus.FUNDED,
            "created_at": datetime.utcnow().isoformat()
        }

    async def _payout_to_worker(
        self,
        worker_id: str,
        amount: Decimal,
        currency: str,
        escrow_id: str
    ) -> Dict[str, Any]:
        """Process payout to worker's account"""
        # TODO: Implement Stripe Connect transfer
        # For now, return mock payout
        logger.info(f"Processing payout to worker {worker_id}: {amount} {currency}")
        return {
            "id": f"payout_{escrow_id}",
            "amount": float(amount),
            "currency": currency,
            "status": "paid"
        }

    def _generate_escrow_id(self) -> str:
        """Generate unique escrow ID"""
        import uuid
        return f"escrow_{uuid.uuid4().hex[:16]}"

    def _generate_dispute_id(self) -> str:
        """Generate unique dispute ID"""
        import uuid
        return f"dispute_{uuid.uuid4().hex[:16]}"

    async def get_escrow_stats(
        self,
        db: AsyncSession,
        user_id: str,
        role: str = "all"
    ) -> Dict[str, Any]:
        """
        Get escrow statistics for a user

        Args:
            db: Database session
            user_id: User ID
            role: Filter by role (payer, worker, all)

        Returns:
            Escrow statistics
        """
        # TODO: Implement actual stats query
        return {
            "total_escrows": 0,
            "total_amount": 0.0,
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "released": 0,
            "disputed": 0
        }


# Global service instance
escrow_service = EscrowService()
