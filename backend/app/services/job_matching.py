"""
Job matching and filtering service.
Scores jobs based on user profile, resume, and preferences.
"""
import re
from typing import List, Tuple, Optional
from app.models.job_posting import JobPosting
from app.models.user import User
from app.services.resume_extraction import ResumeExtractor, ResumeData


class ResumeParser:
    """Extract skills and experience from resume text."""
    
    # Common technical skills
    TECHNICAL_SKILLS = {
        # Languages
        "python", "java", "javascript", "typescript", "go", "rust", "c++", "c#",
        "ruby", "php", "swift", "kotlin", "scala", "haskell", "clojure", "elixir",
        "sql", "r", "matlab", "lua", "groovy", "dart", "erlang",
        
        # Frontend
        "react", "vue", "angular", "svelte", "nextjs", "next.js", "gatsby",
        "html", "css", "sass", "tailwind", "bootstrap", "material ui", "web components",
        "webpack", "vite", "rollup", "parcel",
        
        # Backend
        "nodejs", "node.js", "express", "fastapi", "django", "flask", "spring",
        "spring boot", "rails", "gin", "echo", "fiber", "actix", "tokio",
        "async", "concurrency",
        
        # Databases
        "postgresql", "postgres", "mysql", "mongodb", "redis", "elasticsearch",
        "dynamodb", "cassandra", "neo4j", "firebase", "supabase", "sqlite",
        "sql", "nosql", "graphql",
        
        # Cloud & DevOps
        "aws", "gcp", "google cloud", "azure", "kubernetes", "docker",
        "terraform", "ansible", "jenkins", "ci/cd", "github actions", "gitlab ci",
        "cloudflare", "vercel", "netlify", "heroku",
        
        # Data & AI
        "machine learning", "deep learning", "nlp", "computer vision", "pytorch",
        "tensorflow", "keras", "scikit-learn", "pandas", "numpy", "dask",
        "airflow", "spark", "hadoop", "kafka", "data engineering",
        
        # DevOps/Infrastructure
        "linux", "unix", "bash", "shell scripting", "git", "svn",
        "monitoring", "logging", "observability", "prometheus", "grafana",
        
        # Other
        "rest api", "grpc", "websockets", "authentication", "oauth", "jwt",
        "microservices", "distributed systems", "event-driven", "messaging",
        "testing", "pytest", "jest", "rspec", "unit testing", "integration testing",
        "agile", "scrum", "kanban",
    }
    
    SENIORITY_INDICATORS = {
        "junior": ("junior", "entry", "early", "0-2", "1-2", "graduate", "intern"),
        "mid": ("mid", "intermediate", "3-5", "senior developer", "lead developer"),
        "senior": ("senior", "staff", "principal", "architect", "expert", "5+", "8+", "10+"),
    }
    
    # Job types to accept (engineering/technical roles)
    ACCEPTED_JOB_TYPES = {
        # Core engineering
        "software", "engineer", "developer", "dev", "swe",
        "backend", "frontend", "fullstack", "full-stack", "full stack",
        "frontend engineer", "backend engineer", "frontend developer",
        "devops", "sre", "infrastructure", "platform engineer",
        "ml", "machine learning", "data scientist", "ai engineer", "ai/ml",
        "security", "infosec", "cybersecurity", "appsec",
        "qa", "testing", "quality assurance", "test engineer",
        "embedded", "systems engineer", "firmware",
        "robotics", "cv", "computer vision",
        "crypto", "blockchain",
    }
    
    # Job types to reject (non-technical roles)
    REJECTED_JOB_TYPES = {
        "hr", "human resources", "recruiter", "recruiting",
        "sales", "account executive", "business development",
        "finance", "accounting", "accountant", "financial",
        "legal", "lawyer", "counsel",
        "marketing", "brand", "communications", "pr",
        "operations", "ops", "product manager", "pm",
        "administrative", "admin", "assistant",
        "customer success", "customer support", "support",
        "project manager", "project management",
    }
    
    @staticmethod
    def extract_skills(resume_text: str) -> List[str]:
        """Extract technical skills from resume text."""
        if not resume_text:
            return []
        
        resume_lower = resume_text.lower()
        found_skills = []
        
        for skill in ResumeParser.TECHNICAL_SKILLS:
            # Use word boundary matching to avoid partial matches
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, resume_lower):
                found_skills.append(skill)
        
        return list(set(found_skills))  # Deduplicate
    
    @staticmethod
    def infer_seniority(resume_text: str) -> Optional[str]:
        """Infer seniority level from resume text.
        
        Priority:
        1. Explicit seniority keywords in job titles (Senior, Staff, Principal, Junior)
        2. Years of experience extracted from resume
        3. Default to mid-level if ambiguous
        """
        if not resume_text:
            return None
        
        text_lower = resume_text.lower()
        
        # Check for explicit seniority indicators (check senior/principal first to avoid matching "junior" in other contexts)
        if any(keyword in text_lower for keyword in ["staff", "principal", "architect"]):
            return "senior"
        
        if any(keyword in text_lower for keyword in ["senior", "lead", "tech lead", "sr."]):
            return "senior"
        
        if any(keyword in text_lower for keyword in ["junior", "entry", "graduate", "intern"]):
            return "junior"
        
        # Fall back to years of experience
        years = ResumeParser.extract_experience_years(resume_text)
        if years:
            if years < 2:
                return "junior"
            elif years < 5:
                return "mid"
            else:
                return "senior"
        
        # Default to mid-level if no clear indicators
        return "mid"
    
    @staticmethod
    def extract_experience_years(resume_text: str) -> Optional[int]:
        """Extract total years of experience from resume text."""
        if not resume_text:
            return None
        
        # Look for patterns like "5+ years", "5 years", "experience: 5 years"
        patterns = [
            r'(\d+)\+?\s*years?\s*(?:of\s*)?(?:experience|work)',
            r'experience:\s*(\d+)\+?\s*years?',
            r'(\d+)\+?\s*years?\s*(?:in\s*)?(?:software|web|full-?stack)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, resume_text.lower())
            if match:
                return int(match.group(1))
        
        return None


def check_job_type_match(
    job_title: str,
    job_desc: str,
    preferred_job_types: Optional[List[str]] = None
) -> Tuple[bool, Optional[str]]:
    """
    Check if job matches user's preferred job types (hard filter).
    
    Returns:
        Tuple of (is_valid, reason_if_invalid)
    """
    job_title_lower = (job_title or "").lower()
    job_desc_lower = (job_desc or "").lower()
    
    # Check for rejected job types first
    for rejected in ResumeParser.REJECTED_JOB_TYPES:
        if rejected in job_title_lower or rejected in job_desc_lower:
            return False, f"Rejected job type: {rejected}"
    
    # If no preferred types specified, accept all technical roles
    if not preferred_job_types:
        for accepted in ResumeParser.ACCEPTED_JOB_TYPES:
            if accepted in job_title_lower or accepted in job_desc_lower:
                return True, None
        return False, "Not a technical/engineering role"
    
    # Check for preferred job types
    for preferred in preferred_job_types:
        if preferred.lower() in job_title_lower or preferred.lower() in job_desc_lower:
            return True, None
    
    # If no preferred type found, reject
    return False, f"Job type not in preferred list: {', '.join(preferred_job_types)}"


def check_seniority_match(
    resume_seniority: Optional[str],
    job_title: str,
    job_desc: str
) -> Tuple[bool, Optional[str]]:
    """
    Check if job seniority matches user seniority (hard filter).
    
    Returns:
        Tuple of (is_valid, reason_if_invalid)
    """
    if not resume_seniority:
        # If we don't know user seniority, accept all jobs
        return True, None
    
    job_title_lower = (job_title or "").lower()
    job_desc_lower = (job_desc or "").lower()
    
    # Junior users should get internship/entry-level/junior roles
    if resume_seniority == "junior":
        junior_keywords = ("internship", "entry", "junior", "graduate", "co-op", "early")
        is_junior_job = any(kw in job_title_lower or kw in job_desc_lower for kw in junior_keywords)
        if not is_junior_job:
            return False, "Job is not junior/entry-level but user is junior"
        return True, None
    
    # Mid-level users should get mid/senior roles (avoid internships)
    if resume_seniority == "mid":
        is_internship = "internship" in job_title_lower or "intern" in job_desc_lower
        if is_internship:
            return False, "Job is internship but user is mid-level"
        return True, None
    
    # Senior users get everything
    if resume_seniority == "senior":
        return True, None
    
    return True, None


def calculate_job_match_score(
    job: JobPosting,
    user_skills: List[str],
    user_location: Optional[str],
    prefer_remote: bool = True,
) -> Tuple[int, List[str]]:
    """
    Calculate match score (0-100) for a job based on user profile.
    Only called if job passed hard filters (job type + seniority).
    
    Returns:
        Tuple of (score, mismatch_reasons)
    
    Scoring logic:
    - Base: 50 points
    - Skill match: +30 if job skills overlap with user skills (max +5 per skill)
    - Work mode: +15 if remote and user prefers remote, +5 if hybrid, 0 if onsite
    - Location: +10 if remote, +5 if matches user location, 0 otherwise
    - Description quality: +10 if has description
    """
    score = 50
    mismatches = []
    
    # Parse job details
    job_desc = (job.description_raw or "").lower()
    job_location = (job.location_text or "").lower()
    job_work_mode = (job.work_mode or "").lower()
    
    # 1. Skill matching (most important)
    if user_skills and job_desc:
        matching_skills = []
        for skill in user_skills:
            if skill.lower() in job_desc:
                matching_skills.append(skill)
        
        if matching_skills:
            # +5 points per matched skill, max +30
            skill_bonus = min(len(matching_skills) * 5, 30)
            score += skill_bonus
        else:
            mismatches.append("No skill match found in job description")
    
    # 2. Work mode matching
    if prefer_remote:
        if "remote" in job_work_mode:
            score += 15
        elif "hybrid" in job_work_mode:
            score += 5
        else:
            mismatches.append("Not remote or hybrid")
    
    # 3. Location matching
    if "remote" in job_location or "remote" in job_work_mode:
        score += 10
    elif user_location and user_location.lower() in job_location:
        score += 5
    else:
        if user_location and "remote" not in job_location:
            mismatches.append(f"Location mismatch: job is {job_location}, user is {user_location}")
    
    # 4. Description quality bonus
    if job_desc and len(job_desc) > 200:
        score += 10
    
    # Clamp to 0-100
    return max(0, min(100, score)), mismatches


def get_applicable_jobs(
    jobs: List[JobPosting],
    user: User,
    resume_text: Optional[str] = None,
    min_score: int = 50,
) -> List[Tuple[JobPosting, int, List[str]]]:
    """
    Filter and score jobs for a user based on profile and resume.
    
    Hard filters (jobs rejected if they fail):
    1. Must match user's preferred job types
    2. Seniority must match user's experience level
    3. Must be internship if user is junior
    
    Scoring (for ranking remaining jobs):
    - Skill match: +30 points
    - Work mode: +15 for remote, +5 for hybrid
    - Location: +10 for remote, +5 for location match
    - Description quality: +10 points
    
    Returns:
        List of (job, score, mismatch_reasons) sorted by score (highest first)
    """
    # Extract user info from resume and profile
    user_skills = []
    user_seniority = None
    user_experience_years = None
    
    if resume_text:
        user_skills = ResumeParser.extract_skills(resume_text)
        user_seniority = ResumeParser.infer_seniority(resume_text)
        user_experience_years = ResumeParser.extract_experience_years(resume_text)
    
    # Get user preferences
    preferred_job_types = user.preferred_job_types or []
    
    # Score all jobs
    scored_jobs = []
    for job in jobs:
        job_title = job.job_title or ""
        job_desc = job.description_raw or ""
        
        # HARD FILTER 1: Job type must match preferred types
        is_valid_type, type_reason = check_job_type_match(
            job_title, job_desc, preferred_job_types
        )
        if not is_valid_type:
            continue
        
        # HARD FILTER 2: Seniority must match
        is_valid_seniority, seniority_reason = check_seniority_match(
            user_seniority, job_title, job_desc
        )
        if not is_valid_seniority:
            continue
        
        # If job passes hard filters, calculate score
        score, mismatches = calculate_job_match_score(
            job,
            user_skills=user_skills,
            user_location=user.address_city,
            prefer_remote=True,
        )
        
        if score >= min_score:
            scored_jobs.append((job, score, mismatches))
    
    # Sort by score (highest first), then by recency
    scored_jobs.sort(
        key=lambda x: (-x[1], -(x[0].first_seen_at.timestamp() if x[0].first_seen_at else 0))
    )
    
    return scored_jobs
