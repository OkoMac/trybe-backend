"""AI Career Assistant Service using OpenAI and Anthropic Claude"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("OpenAI SDK not installed. OpenAI features disabled.")

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logging.warning("Anthropic SDK not installed. Claude features disabled.")

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
import uuid

from app.core.config import settings
from app.models.opportunity import Opportunity
from app.models.user import User
from app.models.learning import Course


logger = logging.getLogger(__name__)


class CareerAssistantService:
    """
    AI-Powered Career Assistant Service

    Features:
    - Resume analysis and optimization
    - Job/opportunity recommendations
    - Skill gap analysis
    - Career roadmap generation
    - Interview preparation
    - Salary insights
    - Chat-based career counseling
    """

    def __init__(self):
        self.openai_client = None
        self.anthropic_client = None
        self._initialize_clients()

    def _initialize_clients(self):
        """Initialize AI API clients"""
        if OPENAI_AVAILABLE and settings.OPENAI_API_KEY:
            self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("OpenAI client initialized")

        if ANTHROPIC_AVAILABLE and settings.ANTHROPIC_API_KEY:
            self.anthropic_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            logger.info("Anthropic Claude client initialized")

    async def analyze_resume(
        self,
        resume_text: str,
        target_role: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze a resume and provide detailed feedback

        Args:
            resume_text: Full text of the resume
            target_role: Optional target job role for tailored feedback

        Returns:
            Dictionary with analysis results
        """
        if not self.openai_client and not self.anthropic_client:
            return {
                "error": "AI services not configured",
                "recommendations": []
            }

        try:
            prompt = f"""Analyze the following resume and provide detailed feedback.

Resume:
{resume_text}

{f"Target Role: {target_role}" if target_role else ""}

Please provide:
1. Overall assessment (strengths and weaknesses)
2. Extracted skills (technical and soft skills)
3. Experience level assessment
4. Specific improvement recommendations
5. ATS (Applicant Tracking System) optimization tips
6. Missing important sections or information
7. Overall score (1-100)

Format your response as JSON with the following structure:
{{
    "overall_score": 85,
    "strengths": ["list", "of", "strengths"],
    "weaknesses": ["list", "of", "weaknesses"],
    "technical_skills": ["skill1", "skill2"],
    "soft_skills": ["skill1", "skill2"],
    "experience_level": "mid-level",
    "recommendations": [
        {{"priority": "high", "category": "format", "suggestion": "specific suggestion"}},
    ],
    "ats_score": 75,
    "ats_tips": ["tip1", "tip2"],
    "missing_sections": ["section1", "section2"],
    "summary": "Overall assessment summary"
}}"""

            # Use Claude if available (better for detailed analysis), otherwise OpenAI
            if self.anthropic_client:
                response = self.anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}]
                )
                result_text = response.content[0].text
            else:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7
                )
                result_text = response.choices[0].message.content

            # Parse JSON response
            result = json.loads(result_text)
            result["analyzed_at"] = datetime.utcnow().isoformat()
            return result

        except Exception as e:
            logger.error(f"Failed to analyze resume: {e}")
            return {
                "error": str(e),
                "recommendations": []
            }

    async def recommend_opportunities(
        self,
        db: AsyncSession,
        user_skills: List[str],
        experience_level: str,
        preferences: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Recommend opportunities based on user profile using AI

        Args:
            db: Database session
            user_skills: User's skills
            experience_level: User's experience level
            preferences: Additional preferences (location, remote, salary, etc.)
            limit: Maximum number of recommendations

        Returns:
            List of recommended opportunities with match scores
        """
        # Get active opportunities
        result = await db.execute(
            select(Opportunity)
            .where(Opportunity.status == "open")
            .order_by(desc(Opportunity.created_at))
            .limit(100)
        )
        opportunities = result.scalars().all()

        if not opportunities:
            return []

        # Use AI to score and rank opportunities
        if not self.openai_client and not self.anthropic_client:
            # Fallback to simple keyword matching
            return self._simple_opportunity_matching(
                opportunities, user_skills, limit
            )

        try:
            recommendations = []

            for opp in opportunities:
                # Generate match score using AI
                score, reason = await self._calculate_opportunity_match(
                    opportunity=opp,
                    user_skills=user_skills,
                    experience_level=experience_level,
                    preferences=preferences
                )

                if score > 50:  # Threshold
                    recommendations.append({
                        "opportunity_id": str(opp.id),
                        "title": opp.title,
                        "company": opp.provider_company,
                        "match_score": score,
                        "match_reason": reason,
                        "estimated_salary": opp.budget,
                        "location": opp.location,
                        "opportunity_type": opp.opportunity_type,
                        "required_skills": opp.required_skills,
                        "missing_skills": list(set(opp.required_skills or []) - set(user_skills))
                    })

            # Sort by match score
            recommendations.sort(key=lambda x: x["match_score"], reverse=True)

            return recommendations[:limit]

        except Exception as e:
            logger.error(f"Failed to recommend opportunities: {e}")
            return self._simple_opportunity_matching(opportunities, user_skills, limit)

    def _simple_opportunity_matching(
        self,
        opportunities: List[Opportunity],
        user_skills: List[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Simple keyword-based matching (fallback)"""
        user_skills_set = set(s.lower() for s in user_skills)
        recommendations = []

        for opp in opportunities:
            if not opp.required_skills:
                continue

            opp_skills_set = set(s.lower() for s in opp.required_skills)
            matching_skills = user_skills_set & opp_skills_set

            if matching_skills:
                score = (len(matching_skills) / len(opp_skills_set)) * 100

                recommendations.append({
                    "opportunity_id": str(opp.id),
                    "title": opp.title,
                    "company": opp.provider_company,
                    "match_score": round(score, 2),
                    "match_reason": f"Matches {len(matching_skills)} of {len(opp_skills_set)} required skills",
                    "estimated_salary": opp.budget,
                    "location": opp.location,
                    "opportunity_type": opp.opportunity_type,
                    "required_skills": opp.required_skills,
                    "missing_skills": list(opp_skills_set - user_skills_set)
                })

        recommendations.sort(key=lambda x: x["match_score"], reverse=True)
        return recommendations[:limit]

    async def _calculate_opportunity_match(
        self,
        opportunity: Opportunity,
        user_skills: List[str],
        experience_level: str,
        preferences: Optional[Dict[str, Any]]
    ) -> tuple[float, str]:
        """Calculate match score for an opportunity using AI"""
        # Simple scoring for now (in production, use AI for better matching)
        score = 0.0
        reasons = []

        # Skills match (50 points)
        if opportunity.required_skills:
            user_skills_set = set(s.lower() for s in user_skills)
            opp_skills_set = set(s.lower() for s in opportunity.required_skills)
            matching_skills = user_skills_set & opp_skills_set

            if matching_skills:
                skill_score = (len(matching_skills) / len(opp_skills_set)) * 50
                score += skill_score
                reasons.append(f"{len(matching_skills)}/{len(opp_skills_set)} required skills match")

        # Experience level match (20 points)
        if opportunity.experience_level:
            if opportunity.experience_level.lower() == experience_level.lower():
                score += 20
                reasons.append("Experience level matches")
            else:
                score += 10  # Partial credit

        # Location/remote preference (15 points)
        if preferences and preferences.get("is_remote"):
            if opportunity.is_remote:
                score += 15
                reasons.append("Remote opportunity")
        elif opportunity.location:
            score += 10

        # Budget match (15 points)
        if preferences and preferences.get("min_salary"):
            min_salary = preferences["min_salary"]
            if opportunity.budget and opportunity.budget >= min_salary:
                score += 15
                reasons.append("Meets salary requirements")

        reason = "; ".join(reasons) if reasons else "General match"
        return round(score, 2), reason

    async def analyze_skill_gaps(
        self,
        user_skills: List[str],
        target_role: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Analyze skill gaps for a target role

        Args:
            user_skills: User's current skills
            target_role: Target job role
            db: Database session

        Returns:
            Dictionary with skill gap analysis and learning recommendations
        """
        if not self.anthropic_client and not self.openai_client:
            return {"error": "AI services not configured"}

        try:
            prompt = f"""Analyze skill gaps for someone wanting to become a {target_role}.

Current Skills: {', '.join(user_skills)}
Target Role: {target_role}

Please provide:
1. List of essential skills required for {target_role}
2. Skills the user already has that are relevant
3. Critical skills the user is missing (prioritized)
4. Nice-to-have skills that would be beneficial
5. Estimated time to acquire missing skills
6. Learning path recommendations (specific courses, certifications, projects)

Format as JSON:
{{
    "target_role": "{target_role}",
    "essential_skills": ["skill1", "skill2"],
    "user_has": ["skill1", "skill2"],
    "critical_gaps": [
        {{"skill": "skill_name", "priority": "high", "estimated_learning_time_weeks": 4}}
    ],
    "nice_to_have": ["skill1", "skill2"],
    "overall_readiness_percentage": 60,
    "learning_path": [
        {{"step": 1, "skill": "skill_name", "resources": ["course1", "project idea"]}}
    ],
    "estimated_total_weeks": 12
}}"""

            if self.anthropic_client:
                response = self.anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}]
                )
                result_text = response.content[0].text
            else:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7
                )
                result_text = response.choices[0].message.content

            result = json.loads(result_text)

            # Enrich with course recommendations from database
            critical_skills = [gap["skill"] for gap in result.get("critical_gaps", [])]
            recommended_courses = await self._find_courses_for_skills(db, critical_skills)
            result["recommended_courses"] = recommended_courses

            return result

        except Exception as e:
            logger.error(f"Failed to analyze skill gaps: {e}")
            return {"error": str(e)}

    async def _find_courses_for_skills(
        self,
        db: AsyncSession,
        skills: List[str]
    ) -> List[Dict[str, Any]]:
        """Find courses that teach specific skills"""
        if not skills:
            return []

        # Search for courses that teach these skills
        result = await db.execute(
            select(Course)
            .where(Course.status == "published")
            .limit(50)
        )
        courses = result.scalars().all()

        matching_courses = []
        for course in courses:
            if not course.skills_gained:
                continue

            course_skills_set = set(s.lower() for s in course.skills_gained)
            target_skills_set = set(s.lower() for s in skills)
            matching_skills = course_skills_set & target_skills_set

            if matching_skills:
                matching_courses.append({
                    "course_id": str(course.id),
                    "title": course.title,
                    "skills_taught": list(matching_skills),
                    "duration_hours": course.estimated_duration_minutes // 60,
                    "difficulty": course.difficulty,
                    "is_free": course.is_free,
                    "price": course.price
                })

        return matching_courses[:5]

    async def generate_career_roadmap(
        self,
        current_role: str,
        target_role: str,
        user_skills: List[str],
        timeline_months: int = 12
    ) -> Dict[str, Any]:
        """
        Generate a detailed career roadmap

        Args:
            current_role: User's current role
            target_role: Target role
            user_skills: User's current skills
            timeline_months: Timeline for transition in months

        Returns:
            Detailed career roadmap with milestones
        """
        if not self.anthropic_client and not self.openai_client:
            return {"error": "AI services not configured"}

        try:
            prompt = f"""Create a detailed career roadmap for transitioning from {current_role} to {target_role}.

Current Role: {current_role}
Current Skills: {', '.join(user_skills)}
Target Role: {target_role}
Timeline: {timeline_months} months

Provide a structured roadmap with:
1. Quarterly milestones
2. Skills to develop each quarter
3. Projects to complete
4. Networking/community activities
5. Certifications to pursue
6. Expected challenges and how to overcome them

Format as JSON:
{{
    "summary": "Brief overview of the transition plan",
    "is_realistic": true,
    "difficulty_level": "moderate",
    "quarters": [
        {{
            "quarter": 1,
            "focus": "Foundation Building",
            "skills_to_develop": ["skill1", "skill2"],
            "projects": ["project1", "project2"],
            "certifications": ["cert1"],
            "networking": ["activity1"],
            "success_metrics": ["metric1"]
        }}
    ],
    "key_challenges": [
        {{"challenge": "challenge description", "solution": "how to overcome"}}
    ],
    "success_probability": 75,
    "alternative_paths": ["alternative1", "alternative2"]
}}"""

            if self.anthropic_client:
                response = self.anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=3000,
                    messages=[{"role": "user", "content": prompt}]
                )
                result_text = response.content[0].text
            else:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7
                )
                result_text = response.choices[0].message.content

            return json.loads(result_text)

        except Exception as e:
            logger.error(f"Failed to generate career roadmap: {e}")
            return {"error": str(e)}

    async def chat_with_assistant(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Chat with AI career assistant

        Args:
            user_message: User's message
            conversation_history: Previous conversation messages
            user_context: User profile context (skills, experience, goals)

        Returns:
            Assistant's response with suggestions
        """
        if not self.anthropic_client and not self.openai_client:
            return {"error": "AI services not configured"}

        try:
            # Build context
            context_prompt = ""
            if user_context:
                context_prompt = f"""User Profile:
- Current Skills: {', '.join(user_context.get('skills', []))}
- Experience Level: {user_context.get('experience_level', 'unknown')}
- Career Goal: {user_context.get('career_goal', 'not specified')}
"""

            system_message = f"""You are an expert career counselor and mentor. Help the user with their career questions and provide actionable advice.

{context_prompt}

Guidelines:
- Be encouraging and supportive
- Provide specific, actionable advice
- Reference relevant resources when helpful
- Ask clarifying questions when needed
- Focus on practical steps the user can take"""

            # Build message history
            messages = []
            if conversation_history:
                for msg in conversation_history[-10:]:  # Last 10 messages
                    messages.append(msg)

            messages.append({"role": "user", "content": user_message})

            if self.anthropic_client:
                response = self.anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    system=system_message,
                    messages=messages
                )
                assistant_message = response.content[0].text
            else:
                chat_messages = [{"role": "system", "content": system_message}] + messages
                response = self.openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=chat_messages,
                    temperature=0.8
                )
                assistant_message = response.choices[0].message.content

            return {
                "message": assistant_message,
                "timestamp": datetime.utcnow().isoformat(),
                "suggestions": self._extract_action_items(assistant_message)
            }

        except Exception as e:
            logger.error(f"Failed to chat with assistant: {e}")
            return {"error": str(e)}

    def _extract_action_items(self, message: str) -> List[str]:
        """Extract actionable items from assistant message"""
        # Simple extraction of bullet points and numbered lists
        action_items = []
        lines = message.split('\n')

        for line in lines:
            line = line.strip()
            # Check for bullet points or numbers
            if line.startswith(('-', '•', '*')) or (len(line) > 2 and line[0].isdigit() and line[1] in '.):'):
                # Remove bullet/number prefix
                item = line.lstrip('-•*0123456789.): ').strip()
                if item:
                    action_items.append(item)

        return action_items[:5]  # Return top 5 action items


# Global instance
career_assistant_service = CareerAssistantService()
