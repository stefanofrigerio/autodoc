from pydantic import BaseModel
from typing import List, Optional

class WorkExperience(BaseModel):
    company: str
    dates: str
    role: str
    description: str

class Education(BaseModel):
    school: str
    dates: str
    degree: str

class CVData(BaseModel):
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    summary: str
    skills: List[str]
    work_experience: List[WorkExperience]
    education: List[Education]

class AnalysisResponse(BaseModel):
    """
    The response model for the analysis endpoint.
    """
    filename: str
    is_cv: bool
    rejection_reason: Optional[str] = None
    cv_data: Optional[CVData] = None

class SmartSearchRequest(BaseModel):
    query: str

class SmartSearchResult(BaseModel):
    id: str
    cv: CVData
    match_reason: str
    match_score: int # 1-100
    filename: str

class SmartSearchResponse(BaseModel):
    results: List[SmartSearchResult]
