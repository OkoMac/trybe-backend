"""AI Learning Path Service - Personalized course recommendations"""

import logging
from typing import List, Optional, Dict, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
import uuid

from app.models.learning import Course, Enrollment
from app.models.user import User

logger = logging.getLogger(__name__)


class LearningPathService:
    """Service for AI-powered learning path recommendations"""

    @staticmethod
    async def recommend_courses(
        db: AsyncSession,
        user_id: uuid.UUID,
        user_skills: Optional[List[str]] = None,
        target_skills: Optional[List[str]] = None,
        difficulty_preference: Optional[str] = None,
        time_available_hours_per_week: Optional[int] = None,
        career_goal: Optional[str] = None,
        limit: int = 10
    ) -> Tuple[List[Dict], Dict]:
        """
        Generate personalized learning path recommendations

        Args:
            db: Database session
            user_id: User requesting recommendations
            user_skills: User's current skills
            target_skills: Skills user wants to acquire
            difficulty_preference: Preferred difficulty level
            time_available_hours_per_week: Weekly time commitment
            career_goal: Career objective description
            limit: Maximum number of courses to recommend

        Returns:
            Tuple of (recommended_courses, path_metadata)
        """
        # Get user's current enrollments
        enrolled_course_ids = await LearningPathService._get_user_enrolled_courses(db, user_id)

        # Get all published courses
        result = await db.execute(
            select(Course).where(Course.status == "published")
        )
        all_courses = result.scalars().all()

        # Score and rank courses
        scored_courses = []
        for course in all_courses:
            if course.id in enrolled_course_ids:
                continue  # Skip already enrolled courses

            score, reason = LearningPathService._calculate_course_match_score(
                course=course,
                user_skills=user_skills or [],
                target_skills=target_skills or [],
                difficulty_preference=difficulty_preference,
                career_goal=career_goal
            )

            if score > 0:
                # Calculate estimated completion time
                estimated_weeks = LearningPathService._estimate_completion_weeks(
                    course_duration_minutes=course.estimated_duration_minutes,
                    hours_per_week=time_available_hours_per_week or 5
                )

                scored_courses.append({
                    "course": course,
                    "match_score": score,
                    "recommendation_reason": reason,
                    "estimated_completion_weeks": estimated_weeks
                })

        # Sort by match score
        scored_courses.sort(key=lambda x: x["match_score"], reverse=True)

        # Take top N recommendations
        recommendations = scored_courses[:limit]

        # Calculate path metadata
        total_hours = sum(
            rec["course"].estimated_duration_minutes / 60
            for rec in recommendations
        )
        total_weeks = sum(rec["estimated_completion_weeks"] for rec in recommendations)

        # Identify skill gaps
        all_recommended_skills = set()
        for rec in recommendations:
            if rec["course"].skills_gained:
                all_recommended_skills.update(rec["course"].skills_gained)

        target_skill_set = set(target_skills or [])
        skill_gaps = list(target_skill_set - all_recommended_skills)

        # Generate path description
        path_description = LearningPathService._generate_path_description(
            recommendations=recommendations,
            career_goal=career_goal,
            skill_gaps=skill_gaps
        )

        path_metadata = {
            "total_estimated_hours": int(total_hours),
            "total_estimated_weeks": total_weeks,
            "skill_gaps": skill_gaps,
            "path_description": path_description
        }

        return recommendations, path_metadata

    @staticmethod
    async def _get_user_enrolled_courses(
        db: AsyncSession,
        user_id: uuid.UUID
    ) -> set:
        """Get set of course IDs user is already enrolled in"""
        result = await db.execute(
            select(Enrollment.course_id).where(
                and_(
                    Enrollment.user_id == user_id,
                    Enrollment.status.in_(["active", "completed"])
                )
            )
        )
        return set(row[0] for row in result)

    @staticmethod
    def _calculate_course_match_score(
        course: Course,
        user_skills: List[str],
        target_skills: List[str],
        difficulty_preference: Optional[str],
        career_goal: Optional[str]
    ) -> Tuple[float, str]:
        """
        Calculate match score for a course (0-100)

        Scoring factors:
        - Skills match: 40 points
        - Difficulty match: 20 points
        - Career goal alignment: 20 points
        - Popularity/rating: 10 points
        - Prerequisites met: 10 points
        """
        score = 0.0
        reasons = []

        # Skills match (40 points)
        if course.skills_gained:
            skills_gained_set = set(course.skills_gained)
            target_skills_set = set(target_skills)

            # Skills that user wants to learn
            relevant_skills = skills_gained_set & target_skills_set
            if relevant_skills:
                skill_match_percentage = len(relevant_skills) / len(target_skills) if target_skills else 0
                skill_points = skill_match_percentage * 40
                score += skill_points
                reasons.append(f"Teaches {len(relevant_skills)} of your target skills")

        # Difficulty match (20 points)
        if difficulty_preference and course.difficulty == difficulty_preference:
            score += 20
            reasons.append(f"Matches your {difficulty_preference} level")
        elif not difficulty_preference:
            # Award partial points based on logical progression
            user_skill_level = len(user_skills)
            if user_skill_level == 0 and course.difficulty == "beginner":
                score += 20
            elif user_skill_level < 5 and course.difficulty in ["beginner", "intermediate"]:
                score += 15
            elif user_skill_level < 10 and course.difficulty in ["intermediate", "advanced"]:
                score += 15
            else:
                score += 10

        # Career goal alignment (20 points)
        if career_goal and course.category:
            # Simple keyword matching (in production, use NLP/embeddings)
            career_keywords = career_goal.lower().split()
            if any(keyword in course.category.lower() or
                   keyword in course.title.lower() or
                   keyword in course.description.lower()
                   for keyword in career_keywords):
                score += 20
                reasons.append("Aligns with your career goal")

        # Popularity and rating (10 points)
        if course.average_rating:
            rating_score = (course.average_rating / 5.0) * 5  # 0-5 points
            score += rating_score

        if course.enrollment_count > 100:
            score += 3
            reasons.append("Popular course")
        elif course.enrollment_count > 50:
            score += 2

        # Prerequisites met (10 points)
        if course.required_skills:
            user_skills_set = set(user_skills)
            required_skills_set = set(course.required_skills)

            if required_skills_set.issubset(user_skills_set):
                score += 10
                reasons.append("You meet all prerequisites")
            else:
                missing_count = len(required_skills_set - user_skills_set)
                if missing_count <= 2:
                    score += 5
                    reasons.append(f"Missing only {missing_count} prerequisite skills")
        else:
            # No prerequisites required
            score += 10

        # Generate recommendation reason
        if not reasons:
            reasons.append("Recommended based on platform popularity")

        reason = "; ".join(reasons)

        return round(score, 2), reason

    @staticmethod
    def _estimate_completion_weeks(
        course_duration_minutes: int,
        hours_per_week: int
    ) -> int:
        """Estimate weeks to complete course"""
        total_hours = course_duration_minutes / 60
        weeks = max(1, int((total_hours / hours_per_week) + 0.5))  # Round up
        return weeks

    @staticmethod
    def _generate_path_description(
        recommendations: List[Dict],
        career_goal: Optional[str],
        skill_gaps: List[str]
    ) -> str:
        """Generate human-readable path description"""
        if not recommendations:
            return "No courses match your criteria at this time."

        num_courses = len(recommendations)
        top_course = recommendations[0]["course"].title if recommendations else ""

        description_parts = []

        if career_goal:
            description_parts.append(
                f"To achieve your goal of {career_goal}, we recommend starting with "
                f"'{top_course}' and completing {num_courses} courses in total."
            )
        else:
            description_parts.append(
                f"Based on your profile, we recommend {num_courses} courses "
                f"starting with '{top_course}'."
            )

        # Add skill gap information
        if skill_gaps:
            if len(skill_gaps) <= 3:
                gap_list = ", ".join(skill_gaps)
                description_parts.append(
                    f"Note: You may want to look for additional courses in: {gap_list}."
                )
            else:
                description_parts.append(
                    f"Note: There are {len(skill_gaps)} additional skills not covered by these courses."
                )

        return " ".join(description_parts)

    @staticmethod
    async def update_ai_recommendations_for_user(
        db: AsyncSession,
        user_id: uuid.UUID
    ) -> int:
        """
        Update AI recommendation flags for all courses for a user
        (This would be run periodically or when user profile changes)

        Returns:
            Number of courses updated with recommendations
        """
        # Get user profile
        user_result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            return 0

        # Get user skills from metadata (simplified)
        user_skills = user.user_metadata.get("skills", []) if user.user_metadata else []

        # Get all published courses
        courses_result = await db.execute(
            select(Course).where(Course.status == "published")
        )
        courses = courses_result.scalars().all()

        updated_count = 0
        for course in courses:
            score, _ = LearningPathService._calculate_course_match_score(
                course=course,
                user_skills=user_skills,
                target_skills=[],  # Could get from user profile
                difficulty_preference=None,
                career_goal=None
            )

            if score > 60:  # Threshold for recommendation
                course.is_ai_recommended = True
                course.ai_match_score = score
                updated_count += 1
            else:
                course.is_ai_recommended = False
                course.ai_match_score = None

        await db.commit()
        return updated_count
