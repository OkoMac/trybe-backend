"""File upload endpoints"""

from typing import List
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.utils.file_upload import file_upload_service
from app.core.rate_limit import rate_limit_moderate
from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    """File upload response"""
    url: str
    filename: str
    size: int
    content_type: str
    original_filename: str | None = None

    model_config = {"from_attributes": True}


router = APIRouter()


@router.post(
    "/upload/avatar",
    response_model=FileUploadResponse,
    dependencies=[Depends(rate_limit_moderate)]
)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload user avatar image

    - **Max size**: 5MB
    - **Allowed types**: JPEG, PNG, GIF, WebP
    - **Processing**: Resized to 800x800, optimized
    """
    # Upload avatar
    result = await file_upload_service.upload_avatar(
        file=file,
        user_id=str(current_user.id)
    )

    # Update user avatar URL in database
    current_user.avatar_url = result["url"]
    await db.commit()

    return FileUploadResponse(
        url=result["url"],
        filename=result["filename"],
        size=result["size"],
        content_type=result["content_type"]
    )


@router.post(
    "/upload/document",
    response_model=FileUploadResponse,
    dependencies=[Depends(rate_limit_moderate)]
)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = "resume",
    current_user: User = Depends(get_current_user)
):
    """
    Upload document (resume, portfolio, etc.)

    - **Max size**: 10MB
    - **Allowed types**: PDF, DOC, DOCX, TXT
    - **document_type**: resume, portfolio, certificate, other
    """
    # Validate document type
    valid_types = ["resume", "portfolio", "certificate", "cover_letter", "other"]
    if document_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document type. Allowed: {', '.join(valid_types)}"
        )

    # Upload document
    result = await file_upload_service.upload_document(
        file=file,
        user_id=str(current_user.id),
        document_type=document_type
    )

    return FileUploadResponse(
        url=result["url"],
        filename=result["filename"],
        size=result["size"],
        content_type=result["content_type"],
        original_filename=result["original_filename"]
    )


@router.post(
    "/upload/image",
    response_model=FileUploadResponse,
    dependencies=[Depends(rate_limit_moderate)]
)
async def upload_image(
    file: UploadFile = File(...),
    folder: str = "images",
    current_user: User = Depends(get_current_user)
):
    """
    Upload general image

    - **Max size**: 5MB
    - **Allowed types**: JPEG, PNG, GIF, WebP
    - **Processing**: Resized to max 1920x1920, optimized
    """
    # Upload image
    result = await file_upload_service.upload_image(
        file=file,
        folder=folder
    )

    return FileUploadResponse(
        url=result["url"],
        filename=result["filename"],
        size=result["size"],
        content_type=result["content_type"]
    )


@router.post(
    "/upload/multiple",
    response_model=List[FileUploadResponse],
    dependencies=[Depends(rate_limit_moderate)]
)
async def upload_multiple_images(
    files: List[UploadFile] = File(...),
    folder: str = "images",
    current_user: User = Depends(get_current_user)
):
    """
    Upload multiple images

    - **Max files**: 10
    - **Max size per file**: 5MB
    - **Allowed types**: JPEG, PNG, GIF, WebP
    """
    # Limit number of files
    if len(files) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 files allowed per upload"
        )

    # Upload all files
    results = []
    for file in files:
        result = await file_upload_service.upload_image(
            file=file,
            folder=folder
        )
        results.append(FileUploadResponse(
            url=result["url"],
            filename=result["filename"],
            size=result["size"],
            content_type=result["content_type"]
        ))

    return results


@router.delete("/delete/{filename:path}")
async def delete_file(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete uploaded file

    - Must be file owner or admin
    """
    # Check if file belongs to user (basic check - enhance with DB tracking)
    if not filename.startswith(f"avatars/{current_user.id}") and \
       not filename.startswith(f"documents/{current_user.id}"):
        # Check if user is admin
        if current_user.user_type != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this file"
            )

    # Delete file
    deleted = await file_upload_service.delete_file(filename)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    return {"success": True, "message": "File deleted successfully"}
