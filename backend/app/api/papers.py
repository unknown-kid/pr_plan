from typing import List, Optional
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Query,
    Form,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.paper import Paper as PaperModel
from app.schemas.paper import Paper, PaperCreate, PaperUpdate, Tag, TagCreate
from app.services.paper_service import (
    get_paper,
    get_papers,
    create_paper,
    update_paper,
    soft_delete_paper,
    restore_paper,
    add_tag as service_add_tag,
)
from app.tasks.paper_tasks import process_paper_upload_task
from app.config import settings
import shutil
import os
import uuid
from uuid import UUID

router = APIRouter()

UPLOAD_DIR = settings.UPLOAD_DIR
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)


def validate_file(file: UploadFile) -> None:
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {', '.join(settings.ALLOWED_EXTENSIONS)}",
        )


class PaginatedPapers(BaseModel):
    papers: List[Paper]
    total: int


class SearchResult(BaseModel):
    papers: List[Paper]
    folders: List[dict]
    total: int


@router.get("/search")
def search_papers(
    keyword: str,
    folder_id: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.folder import Folder as FolderModel

    if not keyword or len(keyword.strip()) == 0:
        return SearchResult(papers=[], folders=[], total=0)

    keyword_lower = keyword.strip().lower()

    def get_all_subfolder_ids(parent_id: Optional[UUID]) -> List[UUID]:
        ids = []
        if parent_id:
            ids.append(parent_id)
        children = (
            db.query(FolderModel)
            .filter(FolderModel.parent_id == parent_id, FolderModel.is_deleted == False)
            .all()
        )
        for child in children:
            ids.extend(get_all_subfolder_ids(child.id))
        return ids

    folder_ids = None
    if folder_id and folder_id != "null":
        try:
            root_folder_id = UUID(folder_id)
            folder_ids = get_all_subfolder_ids(root_folder_id)
        except ValueError:
            pass

    paper_query = db.query(PaperModel).filter(
        PaperModel.is_deleted == False, PaperModel.title.ilike(f"%{keyword_lower}%")
    )

    if folder_ids is not None:
        paper_query = paper_query.filter(PaperModel.folder_id.in_(folder_ids))

    papers = paper_query.order_by(PaperModel.created_at.desc()).limit(limit).all()

    folder_query = db.query(FolderModel).filter(
        FolderModel.is_deleted == False,
        FolderModel.name.ilike(f"%{keyword_lower}%"),
        FolderModel.user_id == current_user.id,
    )

    if folder_ids is not None:
        folder_query = folder_query.filter(FolderModel.id.in_(folder_ids))

    folders = folder_query.order_by(FolderModel.created_at.desc()).limit(limit).all()

    folder_results = [
        {
            "id": str(f.id),
            "name": f.name,
            "paper_count": f.paper_count,
            "parent_id": str(f.parent_id) if f.parent_id else None,
        }
        for f in folders
    ]

    return SearchResult(
        papers=papers, folders=folder_results, total=len(papers) + len(folders)
    )


@router.get("/", response_model=PaginatedPapers)
def list_papers(
    skip: int = 0,
    limit: int = 100,
    is_public: Optional[bool] = None,
    include_deleted: bool = False,
    folder_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    actual_folder_id = None
    if folder_id and folder_id != "null":
        try:
            actual_folder_id = UUID(folder_id)
        except ValueError:
            pass

    filter_null_folder = folder_id == "null"

    query = db.query(PaperModel)
    if not include_deleted:
        query = query.filter(PaperModel.is_deleted == False)
    if is_public is not None:
        query = query.filter(PaperModel.is_public == is_public)
    if filter_null_folder:
        query = query.filter(PaperModel.folder_id == None)
    elif actual_folder_id is not None:
        query = query.filter(PaperModel.folder_id == actual_folder_id)

    total = query.count()
    papers = (
        query.order_by(PaperModel.created_at.desc()).offset(skip).limit(limit).all()
    )

    return PaginatedPapers(papers=papers, total=total)


@router.post("/", response_model=Paper)
async def upload_paper(
    title: str = Form(...),
    file: UploadFile = File(...),
    embedding_model_id: Optional[UUID] = Form(None),
    folder_id: Optional[UUID] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    validate_file(file)

    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}.pdf")

    file_size = 0
    with open(file_path, "wb") as buffer:
        while chunk := await file.read(1024 * 1024):
            file_size += len(chunk)
            if file_size > settings.MAX_FILE_SIZE:
                buffer.close()
                os.remove(file_path)
                raise HTTPException(
                    status_code=400,
                    detail=f"File too large. Maximum size is {settings.MAX_FILE_SIZE // (1024 * 1024)}MB",
                )
            buffer.write(chunk)

    paper_in = PaperCreate(title=title, pdf_url=file_path)
    paper = create_paper(db, paper_in=paper_in, upload_user_id=current_user.id)
    paper.pdf_path = file_path
    paper.file_size = file_size
    if folder_id:
        paper.folder_id = folder_id
    db.commit()
    db.refresh(paper)

    process_paper_upload_task.delay(
        str(paper.id),
        str(current_user.id),
        str(embedding_model_id) if embedding_model_id else None,
    )

    return paper


class URLUploadRequest(BaseModel):
    url: str
    title: str
    folder_id: Optional[UUID] = None
    embedding_model_id: Optional[UUID] = None


@router.post("/url", response_model=Paper)
async def upload_paper_from_url(
    request: URLUploadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    import httpx

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(request.url)
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to download PDF")

            content_type = response.headers.get("content-type", "")
            if "pdf" not in content_type.lower() and not request.url.lower().endswith(
                ".pdf"
            ):
                raise HTTPException(
                    status_code=400, detail="URL does not point to a PDF file"
                )

            file_size = len(response.content)
            if file_size > settings.MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"File too large. Maximum size is {settings.MAX_FILE_SIZE // (1024 * 1024)}MB",
                )

            file_id = str(uuid.uuid4())
            file_path = os.path.join(UPLOAD_DIR, f"{file_id}.pdf")

            with open(file_path, "wb") as buffer:
                buffer.write(response.content)

            paper_in = PaperCreate(title=request.title, pdf_url=file_path)
            paper = create_paper(db, paper_in=paper_in, upload_user_id=current_user.id)
            paper.pdf_path = file_path
            paper.file_size = file_size
            if request.folder_id:
                paper.folder_id = request.folder_id
            db.commit()
            db.refresh(paper)

            process_paper_upload_task.delay(
                str(paper.id),
                str(current_user.id),
                str(request.embedding_model_id) if request.embedding_model_id else None,
            )

            return paper
    except httpx.RequestError as e:
        raise HTTPException(status_code=400, detail=f"Failed to download PDF: {str(e)}")


@router.get("/{paper_id}", response_model=Paper)
def get_paper_api(paper_id: UUID, db: Session = Depends(get_db)):
    paper = get_paper(db, paper_id=paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.put("/{paper_id}", response_model=Paper)
def update_paper_api(
    paper_id: UUID,
    paper_in: PaperUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_paper = get_paper(db, paper_id=paper_id)
    if not db_paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    if db_paper.upload_user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    return update_paper(db, db_paper=db_paper, paper_in=paper_in)


@router.delete("/{paper_id}")
def delete_paper_api(
    paper_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_paper = get_paper(db, paper_id=paper_id)
    if not db_paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    if db_paper.upload_user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    soft_delete_paper(db, db_paper=db_paper)
    return {"message": "Paper soft-deleted successfully"}


@router.post("/{paper_id}/restore")
def restore_paper_api(
    paper_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.paper import Paper as PaperModel

    db_paper = db.query(PaperModel).filter(PaperModel.id == paper_id).first()
    if not db_paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    if db_paper.upload_user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    restore_paper(db, db_paper=db_paper)
    return {"message": "Paper restored successfully"}


@router.delete("/{paper_id}/permanent")
def permanent_delete_paper_api(
    paper_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.paper import Paper as PaperModel
    from app.models.conversation import ConversationSession, ConversationMessage
    from app.models.paper_tag import PaperTag
    from app.models.user_note import UserNote
    from app.models.user_reading_progress import UserReadingProgress
    from app.models.reading_report import ReadingReport
    from app.models.user_favorite import UserFavorite
    import os

    db_paper = db.query(PaperModel).filter(PaperModel.id == paper_id).first()
    if not db_paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    if db_paper.upload_user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    db.query(ConversationMessage).filter(
        ConversationMessage.session_id.in_(
            db.query(ConversationSession.id).filter(
                ConversationSession.paper_id == paper_id
            )
        )
    ).delete(synchronize_session="fetch")

    db.query(ConversationSession).filter(
        ConversationSession.paper_id == paper_id
    ).delete()

    db.query(PaperTag).filter(PaperTag.paper_id == paper_id).delete()
    db.query(UserNote).filter(UserNote.paper_id == paper_id).delete()
    db.query(UserReadingProgress).filter(
        UserReadingProgress.paper_id == paper_id
    ).delete()
    db.query(ReadingReport).filter(ReadingReport.paper_id == paper_id).delete()
    db.query(UserFavorite).filter(UserFavorite.paper_id == paper_id).delete()

    if db_paper.pdf_path:
        try:
            pdf_path = str(db_paper.pdf_path)
            if pdf_path and os.path.exists(pdf_path):
                os.remove(pdf_path)
        except Exception:
            pass

    db.delete(db_paper)
    db.commit()
    return {"message": "Paper permanently deleted"}


@router.delete("/trash/empty")
def empty_trash_api(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.paper import Paper as PaperModel
    from app.models.folder import Folder as FolderModel
    from app.models.conversation import ConversationSession, ConversationMessage
    import os

    deleted_papers = (
        db.query(PaperModel)
        .filter(
            PaperModel.is_deleted == True, PaperModel.upload_user_id == current_user.id
        )
        .all()
    )

    papers_count = 0
    for paper in deleted_papers:
        sessions = (
            db.query(ConversationSession)
            .filter(ConversationSession.paper_id == paper.id)
            .all()
        )
        for session in sessions:
            db.query(ConversationMessage).filter(
                ConversationMessage.session_id == session.id
            ).delete()
            db.delete(session)

        if paper.pdf_path:
            try:
                pdf_path = str(paper.pdf_path)
                if pdf_path and os.path.exists(pdf_path):
                    os.remove(pdf_path)
            except Exception:
                pass

        db.delete(paper)
        papers_count += 1

    deleted_folders = (
        db.query(FolderModel)
        .filter(FolderModel.is_deleted == True, FolderModel.user_id == current_user.id)
        .all()
    )

    folders_count = 0
    for folder in deleted_folders:
        db.delete(folder)
        folders_count += 1

    db.commit()
    return {
        "message": f"Deleted {papers_count} papers and {folders_count} folders permanently"
    }
    return {"message": f"Deleted {count} papers permanently"}


@router.post("/trash/cleanup")
def cleanup_trash_api(
    days_old: int = Query(30, description="Delete items older than this many days"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.folder import Folder as FolderModel
    from app.models.conversation import ConversationSession, ConversationMessage
    from datetime import datetime, timedelta

    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can perform cleanup")

    cutoff_date = datetime.utcnow() - timedelta(days=days_old)

    papers_to_delete = (
        db.query(PaperModel)
        .filter(PaperModel.is_deleted == True, PaperModel.deleted_at <= cutoff_date)
        .all()
    )

    papers_count = 0
    for paper in papers_to_delete:
        sessions = (
            db.query(ConversationSession)
            .filter(ConversationSession.paper_id == paper.id)
            .all()
        )
        for session in sessions:
            db.query(ConversationMessage).filter(
                ConversationMessage.session_id == session.id
            ).delete()
            db.delete(session)

        if paper.pdf_path:
            try:
                pdf_path = str(paper.pdf_path)
                if pdf_path and os.path.exists(pdf_path):
                    os.remove(pdf_path)
            except Exception:
                pass

        db.delete(paper)
        papers_count += 1

    folders_to_delete = (
        db.query(FolderModel)
        .filter(FolderModel.is_deleted == True, FolderModel.deleted_at <= cutoff_date)
        .all()
    )

    folders_count = 0
    for folder in folders_to_delete:
        db.delete(folder)
        folders_count += 1

    db.commit()
    return {
        "message": f"Cleanup completed",
        "papers_deleted": papers_count,
        "folders_deleted": folders_count,
    }


@router.post("/{paper_id}/tags", response_model=Tag)
def add_tag_api(
    paper_id: UUID,
    tag_in: TagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service_add_tag(
        db, paper_id=paper_id, tag=tag_in.tag, user_id=current_user.id
    )


@router.get("/{paper_id}/view")
def view_paper_api(paper_id: UUID, db: Session = Depends(get_db)):
    paper = get_paper(db, paper_id=paper_id)
    if not paper or not paper.pdf_path:
        raise HTTPException(status_code=404, detail="Paper or PDF not found")
    return FileResponse(paper.pdf_path, media_type="application/pdf")


@router.post("/{paper_id}/export")
def export_citation_api(
    paper_id: UUID,
    format: str = Query("bibtex", enum=["bibtex", "ris", "gbt7714"]),
    db: Session = Depends(get_db),
):
    paper = get_paper(db, paper_id=paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    if format == "bibtex":
        authors_str = " and ".join(paper.authors or ["Unknown"])
        citation = f"@article{{{paper.id},\n  title={{{paper.title}}},\n  author={{{authors_str}}},\n  year={{{paper.publication_date.year if paper.publication_date else 'n.d.'}}}\n}}"
        return {"citation": citation, "format": "bibtex"}

    return {"message": f"Format {format} not implemented yet", "citation": ""}
