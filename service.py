import os
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from dotenv import load_dotenv
from models import CVData, WorkExperience, Education
import json
import typing

load_dotenv()

# Configure Vertex AI
# We expect the user to have authenticated via `gcloud auth application-default login`
# or set GOOGLE_APPLICATION_CREDENTIALS.
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

# Pre-prompt for Smart Search customization
SMART_SEARCH_PRE_PROMPT = """
You are an expert HR and recruitment AI. Your task is to analyze the candidates.
Basically, the question is about a technical role, like a Software Engineer, a Data Scientist, a Machine Learning Engineer, etc.
Morevoer, it is possible that the question is about the level of the role, like a Junior, Mid-level, Senior, etc.
In any case, act reading all the cv's and try to guess which one is the best fit for the question. 
For the position, guess using mostly the tags and the current or past role.
For the seniority, guess using the years of experience in that role.
"""

if PROJECT_ID:
    vertexai.init(project=PROJECT_ID, location=LOCATION)
else:
    print("Warning: GOOGLE_CLOUD_PROJECT not found. Attempting to match gcloud defaults.")
    vertexai.init()

from models import CVData, WorkExperience, Education

def analyze_document_content(file_path: str, mime_type: str) -> dict:
    """
    Analyzes a document using Gemini on Vertex AI to extract CV features.
    
    Args:
        file_path: The path to the file to be analyzed.
        mime_type: The mime type of the file.
        
    Returns:
        dict: A dictionary containing is_cv, rejection_reason, and cv_data.
    """
    
    # Use a Vertex AI model
    model = GenerativeModel("gemini-2.5-flash-lite")

    # Define the prompt
    prompt_text = """
    You are an expert HR and recruitment AI. Your task is to analyze the uploaded document.
    
    First, determine if the document is a Curriculum Vitae (CV) or Resume.
    
    If it is NOT a CV (e.g., a recipe, invoice, generic article, or empty file), set "is_cv" to false and provide a "rejection_reason".
    
    If it IS a CV, set "is_cv" to true and extract the following information strictly adhering to the JSON schema below:
    
    - first_name: Candidate's first name.
    - last_name: Candidate's last name.
    - email: Email address (if available).
    - phone: Phone number (if available).
    - summary: A brief professional summary of the candidate's skills and experience (max 3 sentences).
    - skills: A list of technical skills, technologies, and relevant soft skills.
    - work_experience: A list of previous jobs, including:
        - company: Name of the company.
        - dates: Employment period (e.g., "Jan 2020 - Present").
        - role: Job title.
        - description: Brief description of responsibilities and achievements.
    - education: A list of educational background, including:
        - school: Name of the institution.
        - dates: Attendance period.
        - degree: Degree or certification obtained.

    Output strictly valid JSON matching this schema:
    {
        "is_cv": boolean,
        "rejection_reason": stringOrNull,
        "cv_data": {
            "first_name": "string",
            "last_name": "string",
            "email": "string",
            "phone": "string",
            "summary": "string",
            "skills": ["string"],
            "work_experience": [
                {
                    "company": "string",
                    "dates": "string",
                    "role": "string",
                    "description": "string"
                }
            ],
            "education": [
                {
                    "school": "string",
                    "dates": "string",
                    "degree": "string"
                }
            ]
        }
    }
    """

    # Prepare logic for content
    content_parts = [prompt_text]

    if mime_type.startswith("text/") or mime_type == "application/json":
         try:
             with open(file_path, "r", encoding="utf-8") as f:
                text_content = f.read()
                content_parts.append(text_content)
         except UnicodeDecodeError:
             with open(file_path, "rb") as f:
                 data = f.read()
                 document_part = Part.from_data(data=data, mime_type=mime_type)
                 content_parts.append(document_part)
    else:
        # Binary content
        with open(file_path, "rb") as f:
            data = f.read()
            document_part = Part.from_data(data=data, mime_type=mime_type)
            content_parts.append(document_part)

    # Generate content
    response = model.generate_content(content_parts)
    
    # Parse the response
    try:
        # Simple cleaning of code blocks if Gemini returns them
        text_response = response.text.strip()
        if text_response.startswith("```json"):
            text_response = text_response[7:-3].strip()
        elif text_response.startswith("```"):
            text_response = text_response[3:-3].strip()
            
        data = json.loads(text_response)
        
        # Validation logic
        if not data.get("is_cv"):
             return {
                 "is_cv": False,
                 "rejection_reason": data.get("rejection_reason", "Document is not recognized as a CV."),
                 "cv_data": None
             }
        
        # Construct CVData object to validate structure
        cv_data_dict = data.get("cv_data", {})
        cv_data = CVData(**cv_data_dict)
        
        return {
            "is_cv": True,
            "rejection_reason": None,
            "cv_data": cv_data
        }

    except Exception as e:
        print(f"Error parsing Gemini response: {e}")
        try:
            print(f"Raw response: {response.text}")
        except:
             pass
        # Fallback error
        raise ValueError("Failed to extract CV data from the document.")

def smart_search_cvs(query: str, cv_list: list) -> dict:
    """
    Uses Gemini to search for the best candidates based on a natural language query.
    """
    model = GenerativeModel("gemini-2.5-flash-lite")
    
    # Prepare the context with all CVs (minified to save tokens if needed, but for now full data)
    # Ideally, we should only send relevant fields or summaries.
    # Let's send a simplified version of the list.
    
    simplified_cvs = []
    for cv in cv_list:
        simplified_cvs.append({
            "id": cv.get("id"), # Ensure ID is preserved for linking
            "filename": cv.get("filename"),
            "name": f"{cv.get('first_name')} {cv.get('last_name')}",
            "summary": cv.get("summary"),
            "skills": cv.get("skills"),
            "experience": [f"{exp.get('role')} at {exp.get('company')}" for exp in cv.get("work_experience", [])],
             # Education might be relevant too
            "education": [f"{edu.get('degree')} in {edu.get('school')}" for edu in cv.get("education", [])]
        })
        
    prompt = f"""
    You are an expert technical recruiter helper.
    
    System Instructions: {SMART_SEARCH_PRE_PROMPT}
    
    User Query: "{query}"
    
    Below is a list of Candidate CVs in JSON format:
    {json.dumps(simplified_cvs, indent=2)}
    
    Evaluation Task:
    1. Analyze the User Query to understand the requirements (skills, experience level, domain, etc.).
    2. Review each candidate against these requirements.
    3. Select ONLY the candidates that are a GOOD match (ignore irrelevant ones).
    4. For each selected candidate, provide a "match_score" (1-100) and a "match_reason" explaining why they fit.
    
    Output JSON format:
    {{
        "results": [
            {{
                "cv_id": "id_from_list",
                "match_reason": "Explanation...",
                "match_score": 85
            }}
        ]
    }}
    
    If no candidates match, return "results": [].
    """
    
    try:
        response = model.generate_content(prompt)
        text_response = response.text.strip()
        if text_response.startswith("```json"):
            text_response = text_response[7:-3].strip()
        elif text_response.startswith("```"):
            text_response = text_response[3:-3].strip()
            
        result_data = json.loads(text_response)
        
        # Now we need to merge back with full CV data for the response
        # The frontend needs full CV data to render the card or at least enough info.
        # Our SmartSearchResult model expects: cv (CVData), match_reason, match_score, filename
        
        final_results = []
        cv_map = {cv['id']: cv for cv in cv_list}
        
        for item in result_data.get("results", []):
            cv_id = item.get("cv_id")
            original_cv = cv_map.get(cv_id)
            if original_cv:
                # Convert dict back to CVData object for the response model
                # Note: original_cv is a dict from DuckDB/Storage, so we need to be careful with fields matching CVData
                # storage.list_cvs returns dicts.
                
                # We need to reconstruct CVData. 
                # Issues: storage.list_cvs might return incomplete data depending on the scan!
                # We should update storage.list_cvs to return full data or fetch full data here.
                # For efficiency, let's assume we passed full data or enough to reconstruct.
                
                # Check models.CVData fields vs storage dict keys.
                # storage: first_name, last_name, email, phone, summary, skills, work_experience, education
                
                # We might need to handle the conversion of nested lists (work_exp, edu) properly if they are simplified in storage list
                # actually list_cvs in storage.py (our current impl) returns what we defined in schema.
                
                from models import CVData # Import local to avoid circular issues if any
                
                # Prepare CVData dict
                cv_obj_data = {
                     "first_name": original_cv.get("first_name"),
                     "last_name": original_cv.get("last_name"),
                     "email": original_cv.get("email"),
                     "phone": original_cv.get("phone"),
                     "summary": original_cv.get("summary"),
                     "skills": original_cv.get("skills", []),
                     "work_experience": original_cv.get("work_experience", []),
                     "education": original_cv.get("education", [])
                }
                
                # Pydantic validation might complain if fields are missing or None vs Optional.
                # models.CVData: email, phone are optional. lists are required but can be empty.
                
                # Ensure lists are lists
                if cv_obj_data["skills"] is None: cv_obj_data["skills"] = []
                if cv_obj_data["work_experience"] is None: cv_obj_data["work_experience"] = []
                if cv_obj_data["education"] is None: cv_obj_data["education"] = []

                final_results.append({
                    "id": cv_id,
                    "cv": cv_obj_data,
                    "match_reason": item.get("match_reason"),
                    "match_score": item.get("match_score"),
                    "filename": original_cv.get("filename")
                })
                
        # Sort by score desc
        final_results.sort(key=lambda x: x["match_score"], reverse=True)
        
        return {"results": final_results}
        
    except Exception as e:
        print(f"Error in smart search: {e}")
        return {"results": []}
