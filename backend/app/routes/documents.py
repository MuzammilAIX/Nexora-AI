"""Document management API for the Knowledge Base.

Endpoints:
  POST   /documents/upload     — multipart upload, extracts text
  GET    /documents            — list all docs for tenant
  GET    /documents/{id}       — get one doc with extracted text
  DELETE /documents/{id}       — soft-delete (removes from list)

Supported formats (v1.0): txt, csv, pdf, docx
Full RAG (embeddings + semantic search) is deferred to v1.1.
"""
import io
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth_deps import get_current_user
from ..database import get_session
from ..database.auth_models import User
from ..database.document_models import Document

router = APIRouter(prefix="/documents", tags=["Documents"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_TYPES = {
    "txt": "text/plain",
    "csv": "text/csv",
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "md": "text/markdown",
}


def _detect_type(filename: str) -> Optional[str]:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext if ext in ALLOWED_TYPES else None


def _extract_text(content: bytes, file_type: str) -> str:
    """Extract plain text from uploaded bytes based on file type."""
    if file_type in ("txt", "md", "csv"):
        try:
            return content.decode("utf-8", errors="replace")
        except Exception:
            return content.decode("latin-1", errors="replace")

    if file_type == "pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content))
            parts = []
            for page in reader.pages:
                try:
                    parts.append(page.extract_text() or "")
                except Exception:
                    continue
            return "\n\n".join(parts).strip()
        except ImportError:
            return "[PDF text extraction requires pypdf — install with: pip install pypdf]"
        except Exception as e:
            return f"[PDF extraction failed: {e}]"

    if file_type == "docx":
        try:
            import docx
            document = docx.Document(io.BytesIO(content))
            parts = [p.text for p in document.paragraphs if p.text.strip()]
            return "\n\n".join(parts).strip()
        except ImportError:
            return "[DOCX text extraction requires python-docx — install with: pip install python-docx]"
        except Exception as e:
            return f"[DOCX extraction failed: {e}]"

    return ""


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form("uncategorized"),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Upload a document, extract text, store in the knowledge base."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")

    file_type = _detect_type(file.filename)
    if not file_type:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_TYPES.keys())}",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {MAX_FILE_SIZE // (1024*1024)} MB)",
        )

    extracted = _extract_text(content, file_type)
    status = "ready" if extracted and not extracted.startswith("[") else "processing"

    doc = Document(
        tenant_id=user.tenant_id,
        uploaded_by=user.id,
        filename=file.filename,
        file_type=file_type,
        size_bytes=len(content),
        category=category.strip() or "uncategorized",
        processing_status=status,
        extracted_text=extracted,
        chunk_count=max(1, len(extracted) // 1000) if extracted else 0,
    )

    session.add(doc)
    await session.commit()
    await session.refresh(doc)

    return {
        "id": str(doc.id),
        "filename": doc.filename,
        "file_type": doc.file_type,
        "size_bytes": doc.size_bytes,
        "category": doc.category,
        "processing_status": doc.processing_status,
        "chunk_count": doc.chunk_count,
        "uploaded_at": doc.uploaded_at.isoformat(),
        "extracted_preview": (extracted[:200] + "...") if extracted and len(extracted) > 200 else extracted,
    }


@router.get("")
async def list_documents(
    category: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """List all documents for the current tenant."""
    stmt = select(Document).where(Document.tenant_id == user.tenant_id)
    if category:
        stmt = stmt.where(Document.category == category)
    stmt = stmt.order_by(desc(Document.uploaded_at))

    rows = (await session.execute(stmt)).scalars().all()

    return [
        {
            "id": str(d.id),
            "filename": d.filename,
            "file_type": d.file_type,
            "size_bytes": d.size_bytes,
            "category": d.category,
            "processing_status": d.processing_status,
            "chunk_count": d.chunk_count,
            "uploaded_at": d.uploaded_at.isoformat(),
            "has_text": bool(d.extracted_text),
            "text_length": len(d.extracted_text) if d.extracted_text else 0,
        }
        for d in rows
    ]


@router.get("/{doc_id}")
async def get_document(
    doc_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Get full document details including extracted text."""
    stmt = (
        select(Document)
        .where(Document.id == doc_id)
        .where(Document.tenant_id == user.tenant_id)
    )
    doc = (await session.execute(stmt)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "id": str(doc.id),
        "filename": doc.filename,
        "file_type": doc.file_type,
        "size_bytes": doc.size_bytes,
        "category": doc.category,
        "processing_status": doc.processing_status,
        "chunk_count": doc.chunk_count,
        "uploaded_at": doc.uploaded_at.isoformat(),
        "extracted_text": doc.extracted_text or "",
        "error_message": doc.error_message,
    }


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Delete a document (hard delete for v1.0)."""
    stmt = (
        select(Document)
        .where(Document.id == doc_id)
        .where(Document.tenant_id == user.tenant_id)
    )
    doc = (await session.execute(stmt)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    await session.delete(doc)
    await session.commit()
    return {"id": str(doc_id), "status": "deleted"}