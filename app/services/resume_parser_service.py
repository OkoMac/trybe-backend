"""Resume Parser Service - Extract structured data from resumes"""

import logging
import re
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
import io

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logging.warning("PyPDF2 not installed. PDF parsing disabled.")

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    logging.warning("python-docx not installed. DOCX parsing disabled.")

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from app.core.config import settings


logger = logging.getLogger(__name__)


class ResumeParserService:
    """
    Resume Parser Service

    Features:
    - Extract text from PDF and DOCX files
    - Parse contact information
    - Extract work experience
    - Identify skills
    - Parse education details
    - Detect certifications
    - AI-powered enhancement for better accuracy
    """

    def __init__(self):
        self.openai_client = None
        self.anthropic_client = None
        self._initialize_ai_clients()

    def _initialize_ai_clients(self):
        """Initialize AI clients for enhanced parsing"""
        if OPENAI_AVAILABLE and settings.OPENAI_API_KEY:
            self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

        if ANTHROPIC_AVAILABLE and settings.ANTHROPIC_API_KEY:
            self.anthropic_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def extract_text_from_pdf(self, file_content: bytes) -> str:
        """Extract text from PDF file"""
        if not PDF_AVAILABLE:
            raise ValueError("PDF parsing not available. Install PyPDF2.")

        try:
            pdf_file = io.BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"

            return text.strip()

        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise ValueError(f"Failed to extract text from PDF: {str(e)}")

    async def extract_text_from_docx(self, file_content: bytes) -> str:
        """Extract text from DOCX file"""
        if not DOCX_AVAILABLE:
            raise ValueError("DOCX parsing not available. Install python-docx.")

        try:
            docx_file = io.BytesIO(file_content)
            doc = Document(docx_file)

            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"

            return text.strip()

        except Exception as e:
            logger.error(f"Error extracting text from DOCX: {e}")
            raise ValueError(f"Failed to extract text from DOCX: {str(e)}")

    async def parse_resume(
        self,
        file_content: bytes,
        filename: str,
        use_ai: bool = True
    ) -> Dict[str, Any]:
        """
        Parse resume and extract structured data

        Args:
            file_content: File content as bytes
            filename: Original filename
            use_ai: Whether to use AI for enhanced parsing

        Returns:
            Dictionary with parsed resume data
        """
        # Extract text based on file type
        file_extension = Path(filename).suffix.lower()

        if file_extension == '.pdf':
            text = await self.extract_text_from_pdf(file_content)
        elif file_extension in ['.docx', '.doc']:
            text = await self.extract_text_from_docx(file_content)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")

        # Parse with rule-based extraction
        basic_data = self._rule_based_parse(text)

        # Enhance with AI if available and requested
        if use_ai and (self.openai_client or self.anthropic_client):
            enhanced_data = await self._ai_enhanced_parse(text, basic_data)
            return enhanced_data

        return basic_data

    def _rule_based_parse(self, text: str) -> Dict[str, Any]:
        """Rule-based parsing using regex patterns"""

        data = {
            "raw_text": text,
            "contact_info": self._extract_contact_info(text),
            "skills": self._extract_skills(text),
            "experience": self._extract_experience(text),
            "education": self._extract_education(text),
            "certifications": self._extract_certifications(text),
            "summary": self._extract_summary(text),
            "parsed_at": datetime.utcnow().isoformat()
        }

        return data

    def _extract_contact_info(self, text: str) -> Dict[str, Optional[str]]:
        """Extract contact information"""
        contact = {
            "name": None,
            "email": None,
            "phone": None,
            "location": None,
            "linkedin": None,
            "github": None,
            "website": None
        }

        # Extract email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, text)
        if email_match:
            contact["email"] = email_match.group()

        # Extract phone (various formats)
        phone_patterns = [
            r'\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            r'\+?\d{10,15}'
        ]
        for pattern in phone_patterns:
            phone_match = re.search(pattern, text)
            if phone_match:
                contact["phone"] = phone_match.group()
                break

        # Extract LinkedIn
        linkedin_pattern = r'linkedin\.com/in/[\w-]+'
        linkedin_match = re.search(linkedin_pattern, text, re.IGNORECASE)
        if linkedin_match:
            contact["linkedin"] = f"https://{linkedin_match.group()}"

        # Extract GitHub
        github_pattern = r'github\.com/[\w-]+'
        github_match = re.search(github_pattern, text, re.IGNORECASE)
        if github_match:
            contact["github"] = f"https://{github_match.group()}"

        # Extract name (first line often contains name)
        lines = text.split('\n')
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if line and len(line) < 50 and not re.search(email_pattern, line):
                # Likely a name if it's short and doesn't contain email
                if not any(keyword in line.lower() for keyword in ['resume', 'cv', 'curriculum']):
                    contact["name"] = line
                    break

        return contact

    def _extract_skills(self, text: str) -> List[str]:
        """Extract skills from resume"""
        # Common technical skills (expandable list)
        skill_keywords = [
            # Programming Languages
            'python', 'javascript', 'java', 'c++', 'c#', 'ruby', 'php', 'swift', 'kotlin',
            'typescript', 'go', 'rust', 'scala', 'r', 'matlab',

            # Web Technologies
            'react', 'angular', 'vue', 'node.js', 'express', 'django', 'flask', 'fastapi',
            'html', 'css', 'sass', 'bootstrap', 'tailwind',

            # Databases
            'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'cassandra',

            # Cloud & DevOps
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'gitlab', 'terraform',
            'ansible', 'circleci',

            # Data Science & AI
            'machine learning', 'deep learning', 'tensorflow', 'pytorch', 'scikit-learn',
            'pandas', 'numpy', 'data analysis', 'nlp', 'computer vision',

            # Tools & Others
            'git', 'github', 'jira', 'agile', 'scrum', 'rest api', 'graphql', 'microservices',
            'linux', 'bash', 'testing', 'ci/cd'
        ]

        found_skills = []
        text_lower = text.lower()

        for skill in skill_keywords:
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, text_lower):
                # Capitalize properly
                found_skills.append(skill.title() if skill.islower() else skill)

        # Remove duplicates while preserving order
        seen = set()
        unique_skills = []
        for skill in found_skills:
            skill_lower = skill.lower()
            if skill_lower not in seen:
                seen.add(skill_lower)
                unique_skills.append(skill)

        return unique_skills

    def _extract_experience(self, text: str) -> List[Dict[str, Any]]:
        """Extract work experience (simplified)"""
        experience = []

        # Look for experience section
        exp_patterns = [
            r'EXPERIENCE',
            r'WORK EXPERIENCE',
            r'EMPLOYMENT',
            r'PROFESSIONAL EXPERIENCE'
        ]

        # Find experience section
        exp_section_start = -1
        for pattern in exp_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                exp_section_start = match.start()
                break

        if exp_section_start == -1:
            return experience

        # Extract experience text
        exp_text = text[exp_section_start:]

        # Look for date patterns (2020-2023, Jan 2020 - Dec 2023, etc.)
        date_pattern = r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)?\s*\d{4}\s*[-–to]\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)?\s*(?:\d{4}|Present|Current)'

        # Split by common separators
        lines = exp_text.split('\n')
        current_entry = None

        for line in lines[:50]:  # Limit to avoid processing entire resume
            line = line.strip()
            if not line:
                continue

            # Check if line contains dates
            date_match = re.search(date_pattern, line, re.IGNORECASE)
            if date_match:
                if current_entry:
                    experience.append(current_entry)

                current_entry = {
                    "title": None,
                    "company": None,
                    "period": date_match.group().strip(),
                    "description": []
                }
            elif current_entry:
                # Add to description or set title/company
                if not current_entry["title"]:
                    current_entry["title"] = line
                elif not current_entry["company"]:
                    current_entry["company"] = line
                else:
                    current_entry["description"].append(line)

        if current_entry:
            experience.append(current_entry)

        return experience[:5]  # Return top 5 experiences

    def _extract_education(self, text: str) -> List[Dict[str, str]]:
        """Extract education details"""
        education = []

        # Look for education section
        edu_patterns = [
            r'EDUCATION',
            r'ACADEMIC',
            r'QUALIFICATIONS'
        ]

        edu_section_start = -1
        for pattern in edu_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                edu_section_start = match.start()
                break

        if edu_section_start == -1:
            return education

        edu_text = text[edu_section_start:edu_section_start + 1000]  # Limit section

        # Look for degree keywords
        degree_keywords = [
            'bachelor', 'master', 'phd', 'doctorate', 'associate', 'diploma',
            'b.s.', 'm.s.', 'b.a.', 'm.a.', 'mba', 'bsc', 'msc'
        ]

        lines = edu_text.split('\n')
        for line in lines[:20]:
            line_lower = line.lower()
            if any(degree in line_lower for degree in degree_keywords):
                education.append({
                    "degree": line.strip(),
                    "institution": None,
                    "year": None
                })

        return education

    def _extract_certifications(self, text: str) -> List[str]:
        """Extract certifications"""
        certifications = []

        # Look for certification section
        cert_patterns = [
            r'CERTIFICATION',
            r'LICENSE',
            r'CREDENTIALS'
        ]

        cert_section_start = -1
        for pattern in cert_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                cert_section_start = match.start()
                break

        if cert_section_start == -1:
            return certifications

        cert_text = text[cert_section_start:cert_section_start + 500]
        lines = cert_text.split('\n')

        for line in lines[1:10]:  # Skip header, take next 10 lines
            line = line.strip()
            if line and len(line) > 5:
                certifications.append(line)

        return certifications

    def _extract_summary(self, text: str) -> Optional[str]:
        """Extract professional summary"""
        summary_patterns = [
            r'SUMMARY',
            r'PROFILE',
            r'OBJECTIVE',
            r'ABOUT'
        ]

        for pattern in summary_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Get text after the heading
                start = match.end()
                summary_text = text[start:start + 500]

                # Get first paragraph
                lines = summary_text.split('\n')
                summary_lines = []
                for line in lines:
                    line = line.strip()
                    if line and not line.isupper():  # Skip section headers
                        summary_lines.append(line)
                        if len(' '.join(summary_lines)) > 200:
                            break

                if summary_lines:
                    return ' '.join(summary_lines)

        return None

    async def _ai_enhanced_parse(
        self,
        text: str,
        basic_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use AI to enhance parsing accuracy"""

        if not self.anthropic_client and not self.openai_client:
            return basic_data

        try:
            prompt = f"""Parse the following resume and extract structured information.

Resume Text:
{text[:4000]}  # Limit to avoid token limits

Please extract and return ONLY valid JSON with the following structure:
{{
    "contact_info": {{
        "name": "Full Name",
        "email": "email@example.com",
        "phone": "+1234567890",
        "location": "City, Country",
        "linkedin": "URL",
        "github": "URL"
    }},
    "summary": "Professional summary...",
    "skills": ["skill1", "skill2", ...],
    "experience": [
        {{
            "title": "Job Title",
            "company": "Company Name",
            "period": "Start Date - End Date",
            "description": ["achievement1", "achievement2"]
        }}
    ],
    "education": [
        {{
            "degree": "Degree Name",
            "institution": "University Name",
            "year": "Graduation Year"
        }}
    ],
    "certifications": ["cert1", "cert2"],
    "languages": ["English", "Spanish"],
    "total_years_experience": 5
}}

Return ONLY the JSON, no additional text."""

            # Use Claude if available (better for structured extraction)
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
                    temperature=0.3
                )
                result_text = response.choices[0].message.content

            # Parse JSON
            ai_data = json.loads(result_text)

            # Merge with basic data, preferring AI data
            merged = {**basic_data, **ai_data}
            merged["parsing_method"] = "ai_enhanced"
            merged["parsed_at"] = datetime.utcnow().isoformat()

            return merged

        except Exception as e:
            logger.error(f"AI enhanced parsing failed: {e}")
            # Fall back to basic parsing
            basic_data["parsing_method"] = "rule_based"
            return basic_data


# Global instance
resume_parser_service = ResumeParserService()
