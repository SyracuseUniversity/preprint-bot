from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from typing import List
from pathlib import Path
import shutil
from database import get_db_pool
from config import USER_PDF_DIR, USER_PROCESSED_DIR
import asyncio

router = APIRouter(prefix="/uploads", tags=["uploads"])

@router.post("/paper/{user_id}/{profile_id}")
async def upload_paper(
    user_id: int,
    profile_id: int,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """Upload a PDF paper for a user profile"""
    
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Create directories
    user_pdf_dir = USER_PDF_DIR / str(user_id) / str(profile_id)
    user_pdf_dir.mkdir(parents=True, exist_ok=True)
    
    # Save file
    file_path = user_pdf_dir / file.filename
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    return {
        "message": "File uploaded successfully",
        "filename": file.filename,
        "path": str(file_path),
        "user_id": user_id,
        "profile_id": profile_id
    }

@router.post("/batch/{user_id}/{profile_id}")
async def upload_multiple_papers(
    user_id: int,
    profile_id: int,
    files: List[UploadFile] = File(...)
):
    """Upload multiple PDF papers at once"""
    
    results = []
    errors = []
    
    for file in files:
        if not file.filename.endswith('.pdf'):
            errors.append(f"{file.filename}: Not a PDF file")
            continue
        
        user_pdf_dir = USER_PDF_DIR / str(user_id) / str(profile_id)
        user_pdf_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = user_pdf_dir / file.filename
        
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            results.append({
                "filename": file.filename,
                "path": str(file_path),
                "status": "success"
            })
        except Exception as e:
            errors.append(f"{file.filename}: {str(e)}")
    
    return {
        "uploaded": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors
    }

@router.get("/papers/{user_id}/{profile_id}")
async def list_uploaded_papers(user_id: int, profile_id: int):
    """List all uploaded papers for a user profile"""
    
    user_pdf_dir = USER_PDF_DIR / str(user_id) / str(profile_id)
    
    if not user_pdf_dir.exists():
        return {"papers": []}
    
    papers = []
    for pdf_file in user_pdf_dir.glob("*.pdf"):
        papers.append({
            "filename": pdf_file.name,
            "path": str(pdf_file),
            "size_mb": round(pdf_file.stat().st_size / (1024 * 1024), 2)
        })
    
    return {"papers": papers}

@router.delete("/paper/{user_id}/{profile_id}/{filename}")
async def delete_uploaded_paper(user_id: int, profile_id: int, filename: str):
    """Delete an uploaded paper"""
    
    file_path = USER_PDF_DIR / str(user_id) / str(profile_id) / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        file_path.unlink()
        return {"message": "File deleted successfully", "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")

@router.post("/process/{user_id}/{profile_id}")
async def trigger_processing(
    user_id: int,
    profile_id: int,
    background_tasks: BackgroundTasks
):
    """Trigger processing of uploaded papers"""
    
    user_pdf_dir = USER_PDF_DIR / str(user_id) / str(profile_id)
    
    if not user_pdf_dir.exists() or not list(user_pdf_dir.glob("*.pdf")):
        raise HTTPException(status_code=400, detail="No papers to process")
    
    # Add background task to process papers
    background_tasks.add_task(process_user_papers_task, user_id, profile_id)
    
    return {
        "message": "Processing started",
        "user_id": user_id,
        "profile_id": profile_id
    }

async def process_user_papers_task(user_id: int, profile_id: int):
    """Background task to process user papers"""
    print(f"Starting processing for user {user_id}, profile {profile_id}")
    
    try:
        from pathlib import Path
        import sys
        
        # Get the correct paths
        project_root = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(project_root / "src"))
        
        from preprint_bot.user_mode_processor import process_profile_directory
        from preprint_bot.api_client import APIClient
        from preprint_bot.config import USER_PDF_DIR, USER_PROCESSED_DIR
        
        api_client = APIClient()
        
        # Get user from database
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            user_row = await conn.fetchrow(
                "SELECT id, email, name FROM users WHERE id = $1", 
                user_id
            )
            profile_row = await conn.fetchrow(
                "SELECT id, name FROM profiles WHERE id = $1", 
                profile_id
            )
        
        if not user_row or not profile_row:
            print(f"User or profile not found")
            return
        
        user_dict = {
            'id': user_row['id'],
            'email': user_row['email'],
            'name': user_row['name']
        }
        
        profile_pdf_dir = USER_PDF_DIR / str(user_id) / str(profile_id)
        profile_processed_dir = USER_PROCESSED_DIR / str(user_id) / str(profile_id)
        
        print(f"Processing papers from: {profile_pdf_dir}")
        
        # Process the papers
        result = await process_profile_directory(
            api_client,
            user_dict,
            user_id,
            profile_id,
            profile_pdf_dir,
            profile_processed_dir,
            skip_parse=False,
            skip_embed=False
        )
        
        print(f"Processing complete for user {user_id}, profile {profile_id}")
        print(f"Result: {result}")
        
    except Exception as e:
        print(f"Error processing papers: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            await api_client.close()
        except:
            pass