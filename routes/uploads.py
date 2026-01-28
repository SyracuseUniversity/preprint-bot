from fastapi.responses import StreamingResponse
from .progress_tracker import progress_tracker
import json
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from typing import List
import shutil
from database import get_db_pool
from config import USER_PDF_DIR
import asyncio
from fastapi import Body

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
    
    # Count PDFs
    pdf_count = len(list(user_pdf_dir.glob("*.pdf")))
    
    # Initialize progress tracking
    task_id = f"{user_id}_{profile_id}"
    progress_tracker.start_task(
        task_id, 
        total_steps=pdf_count,
        description=f"Processing {pdf_count} papers"
    )
    
    # Add background task to process papers
    background_tasks.add_task(process_user_papers_task, user_id, profile_id)
    
    return {
        "message": "Processing started",
        "user_id": user_id,
        "profile_id": profile_id,
        "task_id": task_id,
        "total_papers": pdf_count
    }


async def process_user_papers_task(user_id: int, profile_id: int):
    """Background task to process user papers with progress tracking"""
    task_id = f"{user_id}_{profile_id}"
    
    print(f"Starting processing for user {user_id}, profile {profile_id}")
    
    try:
        from pathlib import Path
        import sys
        
        # Get the correct paths
        project_root = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(project_root / "src"))
        
        from preprint_bot.extract_grobid import extract_grobid_sections
        from preprint_bot.api_client import APIClient
        from preprint_bot.config import USER_PDF_DIR, USER_PROCESSED_DIR, DEFAULT_MODEL_NAME
        from preprint_bot.embed_papers import load_model
        
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
            progress_tracker.fail_task(task_id, "User or profile not found")
            print(f"User or profile not found")
            return
        
        profile_pdf_dir = USER_PDF_DIR / str(user_id) / str(profile_id)
        profile_processed_dir = USER_PROCESSED_DIR / str(user_id) / str(profile_id)
        profile_processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Get or create corpus
        corpus_name = f"user_{user_id}_profile_{profile_id}"
        corpus = await api_client.get_or_create_corpus(
            user_id=user_id,
            name=corpus_name,
            description=f"Papers for user {user_id} profile {profile_id}"
        )
        
        # Get list of PDFs
        pdf_files = list(profile_pdf_dir.glob("*.pdf"))
        total_pdfs = len(pdf_files)
        
        print(f"Processing {total_pdfs} papers from: {profile_pdf_dir}")
        
        # Load embedding model once
        model = load_model(DEFAULT_MODEL_NAME)
        
        # Process each PDF
        for i, pdf_file in enumerate(pdf_files):
            try:
                arxiv_id = pdf_file.stem
                
                # Update progress - Starting
                progress_tracker.update_progress(task_id, i, f"Starting: {pdf_file.name}")
                print(f"Processing {i+1}/{total_pdfs}: {pdf_file.name}")
                
                # Extract with GROBID
                progress_tracker.update_progress(task_id, i, f"Extracting text: {pdf_file.name}")
                info = extract_grobid_sections(pdf_file)
                
                # Save processed text
                progress_tracker.update_progress(task_id, i, f"Saving text: {pdf_file.name}")
                processed_file = profile_processed_dir / f"{arxiv_id}_output.txt"
                with open(processed_file, "w", encoding="utf-8") as fh:
                    fh.write(f"{info['title']}\n\n")
                    fh.write(f"{info['abstract']}\n\n")
                    for sec in info["sections"]:
                        fh.write(f"### {sec['header']}\n")
                        fh.write(f"{sec['text']}\n\n")
                
                # Check if paper already exists
                existing = await api_client.get_paper_by_arxiv_id(arxiv_id)
                if existing:
                    print(f"  Paper {arxiv_id} already exists, skipping")
                    progress_tracker.update_progress(task_id, i+1, f"Skipped (exists): {pdf_file.name}")
                    continue
                
                # Create paper in database
                progress_tracker.update_progress(task_id, i, f"Storing in database: {pdf_file.name}")
                paper = await api_client.create_paper(
                    corpus_id=corpus['id'],
                    arxiv_id=arxiv_id,
                    title=info['title'],
                    abstract=info['abstract'],
                    metadata={"user_id": user_id, "profile_id": profile_id},
                    pdf_path=str(pdf_file),
                    source="user"
                )
                
                # Update processed text path
                await api_client.update_paper_processed_path(paper['id'], str(processed_file))
                
                # Store sections
                for sec in info["sections"]:
                    await api_client.create_section(
                        paper_id=paper['id'],
                        header=sec['header'],
                        text=sec['text']
                    )
                
                # Generate embeddings
                progress_tracker.update_progress(task_id, i, f"Generating embeddings: {pdf_file.name}")
                
                # Abstract embedding
                abstract_text = f"{info['title']}. {info['abstract']}"
                abstract_emb = model.encode([abstract_text], normalize_embeddings=True)[0]
                await api_client.create_embedding(
                    paper_id=paper['id'],
                    embedding=abstract_emb.tolist(),
                    type="abstract",
                    model_name=DEFAULT_MODEL_NAME
                )
                
                # Section embeddings
                sections = await api_client.get_sections_by_paper(paper['id'])
                for section in sections:
                    if len(section['text'].split()) > 20:  # Only substantial sections
                        section_emb = model.encode([section['text']], normalize_embeddings=True)[0]
                        await api_client.create_embedding(
                            paper_id=paper['id'],
                            section_id=section['id'],
                            embedding=section_emb.tolist(),
                            type="section",
                            model_name=DEFAULT_MODEL_NAME
                        )
                
                progress_tracker.update_progress(task_id, i+1, f"Completed: {pdf_file.name}")
                print(f"  Completed {pdf_file.name}")
                
            except requests.exceptions.RequestException as e:
                # GROBID connection errors - can continue with other papers
                logger.error(f"GROBID processing failed for {pdf_file.name}: {e}")
                progress_tracker.update_progress(task_id, i+1, f"Failed (GROBID): {pdf_file.name}")
                continue
                
            except IOError as e:
                # File read/write errors - can continue with other papers
                logger.error(f"File I/O error for {pdf_file.name}: {e}")
                progress_tracker.update_progress(task_id, i+1, f"Failed (I/O): {pdf_file.name}")
                continue
                
            except KeyError as e:
                # Missing expected data in parsed content - can continue
                logger.error(f"Missing data in {pdf_file.name}: {e}")
                progress_tracker.update_progress(task_id, i+1, f"Failed (parsing): {pdf_file.name}")
                continue
                
            except Exception as e:
                # Unexpected errors - log and continue with next paper
                logger.exception(f"Unexpected error processing {pdf_file.name}: {e}")
                progress_tracker.update_progress(task_id, i+1, f"Failed (error): {pdf_file.name}")
                continue
        
        # Mark as complete
        progress_tracker.complete_task(task_id)
        print(f"Processing complete for user {user_id}, profile {profile_id}")
        
    except Exception as e:
        progress_tracker.fail_task(task_id, str(e))
        print(f"Error processing papers: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            await api_client.close()
        except:
            pass

@router.get("/progress/{user_id}/{profile_id}")
async def get_processing_progress(user_id: int, profile_id: int):
    """Get current processing progress"""
    task_id = f"{user_id}_{profile_id}"
    status = progress_tracker.get_task_status(task_id)
    
    if not status:
        return {
            "status": "not_started",
            "message": "No processing task found"
        }
    
    return status

@router.get("/progress-stream/{user_id}/{profile_id}")
async def stream_processing_progress(user_id: int, profile_id: int):
    """Stream processing progress updates using SSE"""
    
    async def event_generator():
        task_id = f"{user_id}_{profile_id}"
        
        while True:
            status = progress_tracker.get_task_status(task_id)
            
            if not status:
                # Task hasn't started yet
                yield f"data: {json.dumps({'status': 'waiting'})}\n\n"
                await asyncio.sleep(1)
                continue
            
            # Send current status
            yield f"data: {json.dumps(status)}\n\n"
            
            # Stop streaming if task is done
            if status["status"] in ["completed", "failed"]:
                break
            
            await asyncio.sleep(0.5)  # Update every 500ms
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/arxiv/{user_id}/{profile_id}")
async def add_paper_from_arxiv(
    user_id: int,
    profile_id: int,
    background_tasks: BackgroundTasks,
    arxiv_id: str = Body(..., embed=True)
):
    """Add a paper from arXiv by downloading it"""
    import requests
    from pathlib import Path
    
    try:
        # Download PDF from arXiv
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        
        print(f"Downloading paper {arxiv_id} from arXiv...")
        response = requests.get(pdf_url, timeout=30)
        response.raise_for_status()
        
        # Check if it's actually a PDF
        content_type = response.headers.get('Content-Type', '')
        if 'application/pdf' not in content_type.lower():
            raise HTTPException(status_code=400, detail=f"Failed to download PDF for {arxiv_id}. arXiv may have returned an error page.")
        
        # Save to user's directory
        user_pdf_dir = USER_PDF_DIR / str(user_id) / str(profile_id)
        user_pdf_dir.mkdir(parents=True, exist_ok=True)
        
        pdf_path = user_pdf_dir / f"{arxiv_id}.pdf"
        
        with open(pdf_path, 'wb') as f:
            f.write(response.content)
        
        print(f"Saved PDF to {pdf_path}")
        
        return {
            "message": "Paper added successfully from arXiv",
            "arxiv_id": arxiv_id,
            "filename": f"{arxiv_id}.pdf",
            "path": str(pdf_path),
            "user_id": user_id,
            "profile_id": profile_id,
            "size_mb": round(len(response.content) / (1024 * 1024), 2)
        }
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Paper {arxiv_id} not found on arXiv")
        raise HTTPException(status_code=400, detail=f"Failed to download paper: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding paper from arXiv: {str(e)}")