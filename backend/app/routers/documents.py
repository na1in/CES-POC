"""
Document endpoints — upload, list, stream, soft delete.

POST   /api/payments/{id}/documents              — upload supporting document (multipart)
GET    /api/payments/{id}/documents              — list document metadata
GET    /api/payments/{id}/documents/{doc_id}     — download / stream file
DELETE /api/payments/{id}/documents/{doc_id}     — soft delete
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, Form, status
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, get_current_user
from app.database import get_db
from app.services import storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payments", tags=["documents"])

_VALID_DOCUMENT_TYPES = {
    "supporting_evidence",
    "sender_correspondence",
    "bank_statement",
    "fraud_report",
    "policy_document",
    "other",
}


# ── POST /documents ───────────────────────────────────────────────────────────

@router.post("/{payment_id}/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(
    payment_id: str,
    file: UploadFile,
    document_type: str = Form(...),
    description: str = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Upload a supporting document (multipart/form-data). Max 20 MB."""
    if document_type not in _VALID_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"document_type must be one of {sorted(_VALID_DOCUMENT_TYPES)}",
        )

    exists = await db.execute(
        text("SELECT 1 FROM payments WHERE payment_id = :id"),
        {"id": payment_id},
    )
    if exists.one_or_none() is None:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found")

    content_type = file.content_type or "application/octet-stream"
    if content_type not in storage._ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type '{content_type}' is not allowed",
        )

    data = await file.read()
    if len(data) > storage.MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {storage.MAX_FILE_SIZE_BYTES // (1024*1024)} MB",
        )

    storage_path = await storage.save(payment_id, file.filename or "upload", data)

    result = await db.execute(text("""
        INSERT INTO case_documents (
            payment_id, uploaded_by, file_name, file_type, file_size_bytes,
            storage_path, document_type, description
        )
        VALUES (
            :payment_id, :uploader, :file_name, :file_type, :file_size,
            :storage_path, CAST(:doc_type AS document_type), :description
        )
        RETURNING document_id, uploaded_at
    """), {
        "payment_id": payment_id,
        "uploader": current_user.user_id,
        "file_name": file.filename or "upload",
        "file_type": content_type,
        "file_size": len(data),
        "storage_path": storage_path,
        "doc_type": document_type,
        "description": description,
    })
    row = result.mappings().one()

    await db.execute(text("""
        INSERT INTO audit_log (payment_id, action_type, actor, actor_user_id, details, timestamp)
        VALUES (:pid, 'document_uploaded', :actor, :actor_uid,
                CAST(:details AS jsonb), now())
    """), {
        "pid": payment_id,
        "actor": current_user.name,
        "actor_uid": current_user.user_id,
        "details": (
            f'{{"document_id": {row["document_id"]}, '
            f'"file_name": "{file.filename}", "document_type": "{document_type}"}}'
        ),
    })

    await db.commit()
    logger.info("%s uploaded document %d for %s", current_user.user_id, row["document_id"], payment_id)

    return {
        "document_id": row["document_id"],
        "payment_id": payment_id,
        "file_name": file.filename,
        "file_type": content_type,
        "file_size_bytes": len(data),
        "document_type": document_type,
        "uploaded_at": row["uploaded_at"].isoformat(),
    }


# ── GET /documents ────────────────────────────────────────────────────────────

@router.get("/{payment_id}/documents")
async def list_documents(
    payment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List metadata for all non-deleted documents on a payment."""
    exists = await db.execute(
        text("SELECT 1 FROM payments WHERE payment_id = :id"),
        {"id": payment_id},
    )
    if exists.one_or_none() is None:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found")

    rows = await db.execute(text("""
        SELECT document_id, payment_id, uploaded_by, file_name, file_type,
               file_size_bytes, document_type, description, uploaded_at
        FROM case_documents
        WHERE payment_id = :id AND is_deleted = false
        ORDER BY uploaded_at ASC
    """), {"id": payment_id})

    return {"documents": [dict(r) for r in rows.mappings()]}


# ── GET /documents/{doc_id} ───────────────────────────────────────────────────

@router.get("/{payment_id}/documents/{doc_id}")
async def download_document(
    payment_id: str,
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Stream document file content."""
    doc_row = await db.execute(text("""
        SELECT file_name, file_type, storage_path
        FROM case_documents
        WHERE document_id = :doc_id AND payment_id = :pid AND is_deleted = false
    """), {"doc_id": doc_id, "pid": payment_id})
    doc = doc_row.mappings().one_or_none()

    if doc is None:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

    file_path = storage.full_path(doc["storage_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    def _iter_file():
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                yield chunk

    return StreamingResponse(
        _iter_file(),
        media_type=doc["file_type"],
        headers={"Content-Disposition": f'attachment; filename="{doc["file_name"]}"'},
    )


# ── DELETE /documents/{doc_id} ────────────────────────────────────────────────

@router.delete("/{payment_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    payment_id: str,
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Soft delete a document (is_deleted = true). File remains on disk."""
    result = await db.execute(text("""
        UPDATE case_documents
        SET is_deleted = true
        WHERE document_id = :doc_id AND payment_id = :pid AND is_deleted = false
        RETURNING document_id
    """), {"doc_id": doc_id, "pid": payment_id})

    if result.one_or_none() is None:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

    await db.commit()
    logger.info("%s soft-deleted document %d from %s", current_user.user_id, doc_id, payment_id)
