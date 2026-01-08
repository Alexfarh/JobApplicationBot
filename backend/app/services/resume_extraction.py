"""
Comprehensive resume extraction service using Hugging Face models and NER.
Extracts: skills, experience, education, projects, contact info, employment history.
"""
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class Experience:
    """Work experience entry."""
    company: str
    title: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration_years: Optional[float] = None
    description: List[str] = None
    
    def __post_init__(self):
        if self.description is None:
            self.description = []


@dataclass
class Education:
    """Education entry."""
    institution: str
    degree: str
    field: Optional[str] = None
    graduation_year: Optional[str] = None
    gpa: Optional[str] = None


@dataclass
class ResumeData:
    """Structured resume data."""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    
    # Professional info
    summary: Optional[str] = None
    skills: List[str] = None
    experience: List[Experience] = None
    education: List[Education] = None
    projects: List[Dict] = None
    certifications: List[str] = None
    
    # Computed fields
    total_experience_years: Optional[float] = None
    seniority_level: Optional[str] = None
    
    def __post_init__(self):
        if self.skills is None:
            self.skills = []
        if self.experience is None:
            self.experience = []
        if self.education is None:
            self.education = []
        if self.projects is None:
            self.projects = []
        if self.certifications is None:
            self.certifications = []
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['experience'] = [asdict(e) for e in self.experience]
        data['education'] = [asdict(e) for e in self.education]
        return data


class ResumeExtractor:
    """Extract structured data from resume text using regex and pattern matching."""
    
    # Technical skills database
    TECHNICAL_SKILLS = {
        # Languages
        "python", "java", "javascript", "typescript", "go", "rust", "c++", "c#",
        "ruby", "php", "swift", "kotlin", "scala", "haskell", "clojure", "elixir",
        "sql", "r", "matlab", "lua", "groovy", "dart", "erlang", "perl", "vb.net",
        
        # Frontend
        "react", "vue", "angular", "svelte", "nextjs", "next.js", "gatsby",
        "html", "css", "sass", "tailwind", "bootstrap", "material ui", "web components",
        "webpack", "vite", "rollup", "parcel", "jquery", "ember", "backbone",
        
        # Backend
        "nodejs", "node.js", "node", "express", "fastapi", "django", "flask", "spring",
        "spring boot", "rails", "gin", "echo", "fiber", "actix", "tokio", "asp.net",
        "asp.net core", "laravel", "symfony", "nestjs",
        
        # Databases
        "postgresql", "postgres", "mysql", "mongodb", "redis", "elasticsearch",
        "dynamodb", "cassandra", "neo4j", "firebase", "supabase", "sqlite",
        "sql", "nosql", "graphql", "memcached", "oracle", "sql server",
        
        # Cloud & DevOps
        "aws", "gcp", "google cloud", "azure", "kubernetes", "docker",
        "terraform", "ansible", "jenkins", "ci/cd", "github actions", "gitlab ci",
        "cloudflare", "vercel", "netlify", "heroku", "circleci", "travis ci",
        "prometheus", "grafana", "datadog", "newrelic", "splunk",
        
        # Data & AI/ML
        "machine learning", "deep learning", "nlp", "computer vision", "pytorch",
        "tensorflow", "keras", "scikit-learn", "pandas", "numpy", "dask",
        "airflow", "spark", "hadoop", "kafka", "ray", "hugging face",
        "sql", "data engineering", "etl", "elt", "analytics",
        
        # DevOps/Infrastructure
        "linux", "unix", "bash", "shell scripting", "git", "svn",
        "monitoring", "logging", "observability", "observability",
        
        # Other
        "rest api", "grpc", "websockets", "authentication", "oauth", "jwt", "saml",
        "microservices", "distributed systems", "event-driven", "messaging",
        "testing", "pytest", "jest", "rspec", "unit testing", "integration testing",
        "agile", "scrum", "kanban", "jira", "confluence",
        "mobile", "ios", "android", "flutter", "react native",
        "blockchain", "web3", "solidity", "ethereum", "crypto",
    }
    
    # Common technical certifications
    CERTIFICATIONS = {
        "aws", "azure", "gcp", "kubernetes", "ccna", "cissp", "oscp",
        "certified kubernetes administrator", "cka", "docker certified associate",
        "terraform associate", "aws solutions architect", "aws developer",
    }
    
    @staticmethod
    def extract_contact_info(text: str) -> Dict[str, Optional[str]]:
        """Extract contact information: email, phone, location, links."""
        contact = {
            "email": None,
            "phone": None,
            "location": None,
            "linkedin": None,
            "github": None,
            "portfolio": None,
        }
        
        # Email
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        if email_match:
            contact["email"] = email_match.group()
        
        # Phone (multiple formats)
        phone_patterns = [
            r'\+?1?\s*\(?(\d{3})\)?[\s.-]?(\d{3})[\s.-]?(\d{4})',
            r'\+\d{1,3}[\s.-]?\d{1,14}',
        ]
        for pattern in phone_patterns:
            match = re.search(pattern, text)
            if match:
                contact["phone"] = match.group().strip()
                break
        
        # LinkedIn
        linkedin_match = re.search(r'linkedin\.com/in/([a-zA-Z0-9_-]+)', text, re.IGNORECASE)
        if linkedin_match:
            contact["linkedin"] = f"linkedin.com/in/{linkedin_match.group(1)}"
        
        # GitHub
        github_match = re.search(r'github\.com/([a-zA-Z0-9_-]+)', text, re.IGNORECASE)
        if github_match:
            contact["github"] = f"github.com/{github_match.group(1)}"
        
        # Portfolio
        portfolio_match = re.search(r'(https?://[^\s]+|[a-zA-Z0-9.-]+\.(com|io|dev|co))(?![a-zA-Z0-9])', text)
        if portfolio_match and 'linkedin' not in portfolio_match.group().lower() and 'github' not in portfolio_match.group().lower():
            contact["portfolio"] = portfolio_match.group()
        
        return contact
    
    @staticmethod
    def extract_skills(text: str) -> List[str]:
        """Extract technical skills from resume text."""
        text_lower = text.lower()
        found_skills = []
        
        for skill in ResumeExtractor.TECHNICAL_SKILLS:
            # Use word boundary matching
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, text_lower):
                found_skills.append(skill)
        
        return list(set(found_skills))  # Deduplicate
    
    @staticmethod
    def extract_experience(text: str) -> List[Experience]:
        """Extract work experience entries from resume text."""
        experiences = []
        
        # Find experience section
        experience_match = re.search(
            r'(?:PROFESSIONAL\s+EXPERIENCE|Professional Experience|EXPERIENCE|Experience)(.*?)(?:EDUCATION|Education|PROJECTS|Projects|SKILLS|Skills|ACHIEVEMENTS|Achievements|$)',
            text,
            re.IGNORECASE | re.DOTALL
        )
        
        if not experience_match:
            return experiences
        
        exp_section = experience_match.group(1)
        
        # Split by company lines (usually in all caps or title case)
        # Pattern: Company name on one line, followed by date range and job title
        lines = exp_section.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines
            if not line:
                i += 1
                continue
            
            # Check if this looks like a company line (has a date range)
            if any(month in line for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec']) and re.search(r'\d{4}\s*(?:–|-)', line):
                # Parse company line: "Sun Life Sept 2025 – Dec 2025"
                company_match = re.match(r'([A-Za-z\s&]+?)\s+([A-Za-z]+)\s+(\d{4})\s*(?:–|-)\s*([A-Za-z]*)\s*(\d{4})', line)
                if company_match:
                    company = company_match.group(1).strip()
                    start_month = company_match.group(2).strip()
                    start_year = company_match.group(3).strip()
                    end_month = company_match.group(4).strip()
                    end_year = company_match.group(5).strip()
                    
                    # Next line should be job title
                    i += 1
                    title_line = lines[i].strip() if i < len(lines) else ""
                    title = title_line
                    
                    # Extract bullet points
                    descriptions = []
                    i += 1
                    while i < len(lines):
                        bullet_line = lines[i].strip()
                        if not bullet_line:
                            i += 1
                            continue
                        if bullet_line.startswith('•'):
                            descriptions.append(bullet_line[1:].strip())
                            i += 1
                        elif any(month in bullet_line for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec']) and re.search(r'\d{4}\s*(?:–|-)', bullet_line):
                            # Hit next job
                            break
                        else:
                            i += 1
                            break
                    
                    # Calculate duration with month precision
                    try:
                        start_y = int(start_year)
                        end_y = int(end_year)
                        
                        # Get month numbers for more accurate duration
                        months = {
                            'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                            'Jul': 7, 'Aug': 8, 'Sept': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
                        }
                        
                        start_m = months.get(start_month, 1)
                        end_m = months.get(end_month, 1) if end_month else 1
                        
                        # Calculate months difference
                        total_months = (end_y - start_y) * 12 + (end_m - start_m)
                        duration = round(total_months / 12, 2)  # Convert to years
                    except:
                        duration = None
                    
                    # Convert description list to string
                    description_text = '\n'.join(descriptions) if descriptions else ""
                    
                    experience = Experience(
                        company=company,
                        title=title,
                        start_date=f"{start_month} {start_year}",
                        end_date=f"{end_month} {end_year}" if end_month else end_year,
                        duration_years=float(duration) if duration else None,
                        description=description_text
                    )
                    experiences.append(experience)
                    continue
            
            i += 1
        
        return experiences
    
    @staticmethod
    def extract_education(text: str) -> List[Education]:
        """Extract education entries."""
        educations = []
        
        # Find education section
        education_match = re.search(
            r'(?:EDUCATION|Education)(.*?)(?:PROJECTS|Projects|TECHNICAL|Technical|SKILLS|Skills|ACHIEVEMENTS|Achievements|ADDITIONAL|Additional|$)',
            text,
            re.IGNORECASE | re.DOTALL
        )
        
        if not education_match:
            return educations
        
        edu_section = education_match.group(1)
        lines = edu_section.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines
            if not line:
                i += 1
                continue
            
            # Look for date pattern or "University" keyword
            if 'University' in line or 'College' in line or 'Institute' in line:
                # Parse institution line: "University of Toronto Sept 2023 – April 2027 (Expected)"
                institution_match = re.match(r'(.*?(?:University|College|Institute|School).*?)\s+([A-Za-z]+)\s+(\d{4})\s*(?:–|-)\s*([A-Za-z]+)\s+(\d{4})', line)
                
                if institution_match:
                    institution = institution_match.group(1).strip()
                    start_month = institution_match.group(2).strip()
                    start_year = institution_match.group(3).strip()
                    end_month = institution_match.group(4).strip()
                    end_year = institution_match.group(5).strip()
                    
                    # Next line(s) should be degree/specialization
                    i += 1
                    degree_lines = []
                    while i < len(lines):
                        degree_line = lines[i].strip()
                        if not degree_line:
                            i += 1
                            break
                        if degree_line.startswith('•'):
                            degree_lines.append(degree_line[1:].strip())
                            i += 1
                        else:
                            # Hit next section
                            break
                    
                    degree = " ".join(degree_lines) if degree_lines else "Degree"
                    
                    education = Education(
                        institution=institution,
                        degree=degree,
                        field=None,
                        graduation_year=end_year
                    )
                    educations.append(education)
                    continue
            
            i += 1
        
        return educations
    
    @staticmethod
    def extract_projects(text: str) -> List[str]:
        """Extract projects as simple strings."""
        projects = []
        
        # Find projects section
        projects_section = re.search(
            r'(?:projects?|portfolio)(.*?)(?:education|skills|experience|$)',
            text,
            re.IGNORECASE | re.DOTALL
        )
        
        if not projects_section:
            return projects
        
        proj_text = projects_section.group(1)
        
        # Extract project entries (lines starting with bullet points or dashes)
        project_entries = re.findall(r'[-•]\s*([^\n]+)', proj_text)
        
        for entry in project_entries:
            entry = entry.strip()
            if entry and len(entry) > 10:  # Filter short entries
                projects.append(entry)
        
        return projects
    
    @staticmethod
    def _parse_date_range(date_str: str) -> Tuple[Optional[str], Optional[str], Optional[float]]:
        """Parse date range string like 'Jan 2020 - Dec 2023' or '2020-2023'."""
        if not date_str:
            return None, None, None
        
        # Pattern: Month Year - Month Year or Year - Year
        date_pattern = r'([A-Za-z]+ )?(\d{4})\s*[-–]\s*([A-Za-z]+ )?(\d{4})|(?:Present|Current)'
        match = re.search(date_pattern, date_str)
        
        if match:
            try:
                start_year = int(match.group(2))
                end_year = int(match.group(4)) if match.group(4) else datetime.now().year
                duration = end_year - start_year
                start_date = match.group(1) + str(start_year) if match.group(1) else str(start_year)
                end_date = match.group(3) + str(end_year) if match.group(3) else str(end_year)
                return start_date, end_date, float(duration)
            except:
                return None, None, None
        
        return None, None, None
    
    @staticmethod
    def extract_summary(text: str) -> Optional[str]:
        """Extract professional summary."""
        # Find summary section (usually near the top)
        summary_section = re.search(
            r'(?:professional summary|summary|objective)(.*?)(?:experience|skills|education|$)',
            text,
            re.IGNORECASE | re.DOTALL
        )
        
        if summary_section:
            summary = summary_section.group(1).strip()
            # Get first 2-3 sentences
            sentences = re.split(r'[.!?]', summary)
            return (sentences[0] + sentences[1] + ".").strip() if len(sentences) > 1 else sentences[0].strip()
        
        return None
    
    @staticmethod
    def infer_seniority(experience_list: List[Experience], years: Optional[float]) -> Optional[str]:
        """Infer seniority level from experience."""
        if not years:
            return None
        
        if years < 2:
            return "junior"
        elif years < 5:
            return "mid"
        else:
            return "senior"
    
    @staticmethod
    def calculate_total_experience(experience_list: List[Experience]) -> Optional[float]:
        """Calculate total years of experience."""
        if not experience_list:
            return None
        
        total_years = 0
        for exp in experience_list:
            if exp.duration_years:
                total_years += exp.duration_years
        
        return total_years if total_years > 0 else None
    
    @staticmethod
    def parse(resume_text: str) -> ResumeData:
        """Parse complete resume and extract all structured data."""
        if not resume_text:
            return ResumeData()
        
        # Extract all components
        contact = ResumeExtractor.extract_contact_info(resume_text)
        skills = ResumeExtractor.extract_skills(resume_text)
        experience = ResumeExtractor.extract_experience(resume_text)
        education = ResumeExtractor.extract_education(resume_text)
        projects = ResumeExtractor.extract_projects(resume_text)
        summary = ResumeExtractor.extract_summary(resume_text)
        
        # Calculate totals
        total_experience_years = ResumeExtractor.calculate_total_experience(experience)
        seniority_level = ResumeExtractor.infer_seniority(experience, total_experience_years)
        
        # Extract name (usually first line or near top)
        name_match = re.match(r'^([A-Z][a-z]+ [A-Z][a-z]+)', resume_text)
        name = name_match.group(1) if name_match else None
        
        return ResumeData(
            name=name,
            email=contact.get("email"),
            phone=contact.get("phone"),
            linkedin=contact.get("linkedin"),
            github=contact.get("github"),
            portfolio=contact.get("portfolio"),
            summary=summary,
            skills=skills,
            experience=experience,
            education=education,
            projects=projects,
            total_experience_years=total_experience_years,
            seniority_level=seniority_level,
        )
