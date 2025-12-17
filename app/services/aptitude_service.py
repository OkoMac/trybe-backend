"""Aptitude Test Service - Test creation, taking, and scoring"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
import uuid

from app.models.hackathon import AptitudeTest, TestResult


logger = logging.getLogger(__name__)


class AptitudeTestService:
    """Service for managing aptitude tests"""

    @staticmethod
    def validate_questions(questions: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
        """
        Validate test questions format

        Args:
            questions: List of question dictionaries

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not questions:
            return False, "At least one question is required"

        for i, question in enumerate(questions):
            # Check required fields
            if "question" not in question:
                return False, f"Question {i+1}: Missing 'question' field"

            if "options" not in question or not isinstance(question["options"], list):
                return False, f"Question {i+1}: Missing or invalid 'options' field"

            if len(question["options"]) < 2:
                return False, f"Question {i+1}: Must have at least 2 options"

            if "correct" not in question:
                return False, f"Question {i+1}: Missing 'correct' field (correct answer index)"

            correct_index = question["correct"]
            if not isinstance(correct_index, int) or correct_index < 0 or correct_index >= len(question["options"]):
                return False, f"Question {i+1}: Invalid 'correct' index"

            if "points" not in question:
                return False, f"Question {i+1}: Missing 'points' field"

            if not isinstance(question["points"], (int, float)) or question["points"] <= 0:
                return False, f"Question {i+1}: Invalid 'points' value"

        return True, None

    @staticmethod
    def calculate_total_points(questions: List[Dict[str, Any]]) -> int:
        """Calculate total possible points for a test"""
        return sum(q.get("points", 0) for q in questions)

    @staticmethod
    async def create_test(
        db: AsyncSession,
        hackathon_id: uuid.UUID,
        title: str,
        description: Optional[str],
        questions: List[Dict[str, Any]],
        duration_minutes: int = 60,
        passing_score: int = 70
    ) -> AptitudeTest:
        """
        Create a new aptitude test

        Args:
            db: Database session
            hackathon_id: Associated hackathon ID
            title: Test title
            description: Test description
            questions: List of question dictionaries
            duration_minutes: Test duration
            passing_score: Passing score percentage

        Returns:
            Created AptitudeTest instance
        """
        # Validate questions
        is_valid, error = AptitudeTestService.validate_questions(questions)
        if not is_valid:
            raise ValueError(error)

        # Calculate total points
        total_points = AptitudeTestService.calculate_total_points(questions)

        test = AptitudeTest(
            hackathon_id=hackathon_id,
            title=title,
            description=description,
            duration_minutes=duration_minutes,
            passing_score=passing_score,
            total_questions=len(questions),
            questions=questions,
            total_points=total_points
        )

        db.add(test)
        await db.commit()
        await db.refresh(test)

        logger.info(f"Created aptitude test: {test.id} with {len(questions)} questions")

        return test

    @staticmethod
    async def get_test_for_user(
        db: AsyncSession,
        test_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get test details for a user (without correct answers)

        Args:
            db: Database session
            test_id: Test ID
            user_id: User ID

        Returns:
            Test dictionary without correct answers, or None if not found
        """
        result = await db.execute(
            select(AptitudeTest).where(AptitudeTest.id == test_id)
        )
        test = result.scalar_one_or_none()

        if not test or not test.is_active:
            return None

        # Check if user already took the test
        result_check = await db.execute(
            select(TestResult).where(
                and_(
                    TestResult.test_id == test_id,
                    TestResult.user_id == user_id
                )
            )
        )
        previous_result = result_check.scalar_one_or_none()

        # Remove correct answers from questions
        questions_for_user = []
        for q in test.questions:
            question_copy = {
                "question": q["question"],
                "options": q["options"],
                "points": q["points"]
            }
            # Don't include correct answer
            questions_for_user.append(question_copy)

        return {
            "id": str(test.id),
            "title": test.title,
            "description": test.description,
            "duration_minutes": test.duration_minutes,
            "total_questions": test.total_questions,
            "total_points": test.total_points,
            "passing_score": test.passing_score,
            "questions": questions_for_user,
            "already_attempted": previous_result is not None,
            "previous_score": previous_result.percentage if previous_result else None,
            "previous_passed": previous_result.passed if previous_result else None
        }

    @staticmethod
    async def submit_test(
        db: AsyncSession,
        test_id: uuid.UUID,
        user_id: uuid.UUID,
        answers: List[int],
        started_at: datetime
    ) -> TestResult:
        """
        Submit and score a test

        Args:
            db: Database session
            test_id: Test ID
            user_id: User ID
            answers: List of answer indices (same order as questions)
            started_at: When the user started the test

        Returns:
            TestResult instance with score
        """
        # Get test
        result = await db.execute(
            select(AptitudeTest).where(AptitudeTest.id == test_id)
        )
        test = result.scalar_one_or_none()

        if not test:
            raise ValueError("Test not found")

        if not test.is_active:
            raise ValueError("Test is not active")

        # Check if already submitted
        existing_result = await db.execute(
            select(TestResult).where(
                and_(
                    TestResult.test_id == test_id,
                    TestResult.user_id == user_id
                )
            )
        )
        if existing_result.scalar_one_or_none():
            raise ValueError("Test already submitted")

        # Validate answers
        if len(answers) != test.total_questions:
            raise ValueError(f"Expected {test.total_questions} answers, got {len(answers)}")

        # Calculate score
        score = 0
        for i, question in enumerate(test.questions):
            if i < len(answers) and answers[i] == question["correct"]:
                score += question["points"]

        # Calculate percentage
        percentage = (score / test.total_points * 100) if test.total_points > 0 else 0
        passed = percentage >= test.passing_score

        # Calculate time taken
        completed_at = datetime.utcnow()
        time_taken = (completed_at - started_at).total_seconds() / 60  # minutes

        # Create result
        test_result = TestResult(
            test_id=test_id,
            user_id=user_id,
            score=score,
            total_points=test.total_points,
            percentage=round(percentage, 2),
            passed=passed,
            answers=answers,
            started_at=started_at,
            completed_at=completed_at,
            time_taken_minutes=int(time_taken)
        )

        db.add(test_result)
        await db.commit()
        await db.refresh(test_result)

        logger.info(f"Test {test_id} submitted by user {user_id}: {percentage}% (passed: {passed})")

        return test_result

    @staticmethod
    async def get_test_result(
        db: AsyncSession,
        result_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed test result

        Args:
            db: Database session
            result_id: Result ID
            user_id: User ID (for authorization)

        Returns:
            Detailed result dictionary, or None if not found
        """
        result = await db.execute(
            select(TestResult).where(TestResult.id == result_id)
        )
        test_result = result.scalar_one_or_none()

        if not test_result or test_result.user_id != user_id:
            return None

        # Get test details
        test_query = await db.execute(
            select(AptitudeTest).where(AptitudeTest.id == test_result.test_id)
        )
        test = test_query.scalar_one_or_none()

        if not test:
            return None

        # Build answer review
        answer_review = []
        for i, (user_answer, question) in enumerate(zip(test_result.answers, test.questions)):
            is_correct = user_answer == question["correct"]
            answer_review.append({
                "question_number": i + 1,
                "question": question["question"],
                "options": question["options"],
                "user_answer": user_answer,
                "correct_answer": question["correct"],
                "is_correct": is_correct,
                "points_earned": question["points"] if is_correct else 0,
                "points_possible": question["points"]
            })

        return {
            "id": str(test_result.id),
            "test_id": str(test_result.test_id),
            "test_title": test.title,
            "score": test_result.score,
            "total_points": test_result.total_points,
            "percentage": float(test_result.percentage),
            "passed": test_result.passed,
            "passing_score": test.passing_score,
            "time_taken_minutes": test_result.time_taken_minutes,
            "started_at": test_result.started_at.isoformat(),
            "completed_at": test_result.completed_at.isoformat(),
            "answer_review": answer_review
        }

    @staticmethod
    async def get_test_statistics(
        db: AsyncSession,
        test_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get statistics for a test

        Args:
            db: Database session
            test_id: Test ID

        Returns:
            Dictionary with test statistics
        """
        # Count total attempts
        total_attempts = await db.execute(
            select(func.count()).select_from(TestResult).where(
                TestResult.test_id == test_id
            )
        )
        total = total_attempts.scalar()

        if total == 0:
            return {
                "total_attempts": 0,
                "average_score": 0,
                "pass_rate": 0,
                "average_time_minutes": 0
            }

        # Get all results
        results = await db.execute(
            select(TestResult).where(TestResult.test_id == test_id)
        )
        all_results = results.scalars().all()

        # Calculate statistics
        total_score = sum(r.percentage for r in all_results)
        total_time = sum(r.time_taken_minutes for r in all_results)
        passed_count = sum(1 for r in all_results if r.passed)

        return {
            "total_attempts": total,
            "average_score": round(total_score / total, 2),
            "pass_rate": round(passed_count / total * 100, 2),
            "average_time_minutes": round(total_time / total, 2),
            "highest_score": max(r.percentage for r in all_results),
            "lowest_score": min(r.percentage for r in all_results)
        }
