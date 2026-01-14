from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import shutil
import os
import uuid
from models import AnalysisResponse, SmartSearchResponse, SmartSearchRequest
from service import analyze_document_content
from storage import ensure_table_exists, save_cv_data

app = FastAPI(title="Document Analysis Service", description="API to analyze documents using Gemini", version="1.0.0")

# Mount Static Files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
def on_startup():
    ensure_table_exists()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def read_root():
    return FileResponse('static/index.html')

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_document(file: UploadFile = File(...)):
    """
    Uploads a document and returns extracted features.
    """
    
    # Validate file type (basic validation)
    allowed_types = ["application/pdf", "text/plain", "application/octet-stream", "text/markdown"]
    # Note: mime type detection can be tricky, trusting the header for now
    
    # Create a temporary file path
    temp_filename = f"{uuid.uuid4()}_{file.filename}"
    temp_file_path = f"/tmp/{temp_filename}"
    
    try:
        # Save the uploaded file to disk
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Determine mime type to pass to Gemini
        mime_type = file.content_type or "text/plain" # fallback
        
        # Analyze the document
        result = analyze_document_content(temp_file_path, mime_type)
        
        # Save to Iceberg if it is a CV
        if result["is_cv"] and result["cv_data"]:
            try:
                save_cv_data(result["cv_data"], file.filename)
                print(f"Successfully saved data for {file.filename}")
            except Exception as e:
                print(f"Error saving to Iceberg: {e}")

        return AnalysisResponse(
            filename=file.filename,
            is_cv=result["is_cv"],
            rejection_reason=result["rejection_reason"],
            cv_data=result["cv_data"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up: remove the temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@app.get("/cvs")
def get_cvs(q: str = None):
    """
    Retrieves a list of CVs from the warehouse.
    """
    from storage import list_cvs
    return list_cvs(q)

@app.get("/cvs/{cv_id}")
def get_cv_detail(cv_id: str):
    """
    Retrieves a single CV by ID.
    """
    from storage import get_cv
    cv = get_cv(cv_id)
    if not cv:
        raise HTTPException(status_code=404, detail="CV not found")
    return cv

@app.delete("/cvs/{cv_id}")
def delete_cv_endpoint(cv_id: str):
    """
    Deletes a CV by ID.
    """
    from storage import delete_cv
    success = delete_cv(cv_id)
    if not success:
         raise HTTPException(status_code=500, detail="Failed to delete CV")
    return {"status": "success", "message": f"CV {cv_id} deleted"}

@app.post("/search/smart", response_model=SmartSearchResponse)
def smart_search_endpoint(request: SmartSearchRequest):
    """
    Performs a smart search on stored CVs using Gemini.
    """
    from service import smart_search_cvs
    from storage import list_cvs

    # Fetch all CVs (can be optimized later)
    # Note: list_cvs expects a string query for filtering, here we want all of them for LLM evaluation
    all_cvs = list_cvs() 
    
    if not all_cvs:
        return SmartSearchResponse(results=[])

    result = smart_search_cvs(request.query, all_cvs)
    
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
