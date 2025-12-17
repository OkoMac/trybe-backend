"""File upload utilities - S3 and local storage"""

import os
import uuid
from typing import Optional, List
from datetime import datetime
from pathlib import Path
import mimetypes
import hashlib
from fastapi import UploadFile, HTTPException, status
from PIL import Image
import io

from app.core.config import settings


class FileUploadService:
    """Handle file uploads to local storage or S3"""

    ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    ALLOWED_DOCUMENT_TYPES = {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain"
    }
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

    def __init__(self):
        self.storage_type = getattr(settings, 'FILE_STORAGE', 'local')  # 'local' or 's3'
        self.upload_dir = Path("uploads")
        self.upload_dir.mkdir(exist_ok=True)

    async def upload_avatar(
        self,
        file: UploadFile,
        user_id: str,
        max_size: tuple = (800, 800)
    ) -> dict:
        """
        Upload and process avatar image

        Args:
            file: Uploaded file
            user_id: User ID
            max_size: Maximum dimensions (width, height)

        Returns:
            dict with url, filename, size
        """
        # Validate file type
        if file.content_type not in self.ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed: {', '.join(self.ALLOWED_IMAGE_TYPES)}"
            )

        # Read file content
        content = await file.read()

        # Check file size
        if len(content) > self.MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size: {self.MAX_IMAGE_SIZE / 1024 / 1024}MB"
            )

        # Process image (resize, optimize)
        processed_content = self._process_image(content, max_size)

        # Generate unique filename
        file_ext = Path(file.filename).suffix or '.jpg'
        filename = f"avatars/{user_id}_{uuid.uuid4().hex}{file_ext}"

        # Save file
        file_url = await self._save_file(filename, processed_content)

        return {
            "url": file_url,
            "filename": filename,
            "size": len(processed_content),
            "content_type": "image/jpeg"
        }

    async def upload_document(
        self,
        file: UploadFile,
        user_id: str,
        document_type: str = "general"
    ) -> dict:
        """
        Upload document (resume, portfolio, etc.)

        Args:
            file: Uploaded file
            user_id: User ID
            document_type: Type of document

        Returns:
            dict with url, filename, size
        """
        # Validate file type
        if file.content_type not in self.ALLOWED_DOCUMENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed: PDF, DOC, DOCX, TXT"
            )

        # Read file content
        content = await file.read()

        # Check file size
        if len(content) > self.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size: {self.MAX_FILE_SIZE / 1024 / 1024}MB"
            )

        # Generate unique filename
        file_ext = Path(file.filename).suffix
        safe_filename = self._sanitize_filename(Path(file.filename).stem)
        filename = f"documents/{user_id}/{document_type}/{safe_filename}_{uuid.uuid4().hex[:8]}{file_ext}"

        # Save file
        file_url = await self._save_file(filename, content)

        return {
            "url": file_url,
            "filename": filename,
            "size": len(content),
            "content_type": file.content_type,
            "original_filename": file.filename
        }

    async def upload_image(
        self,
        file: UploadFile,
        folder: str = "images",
        max_size: tuple = (1920, 1920)
    ) -> dict:
        """
        Upload general image

        Args:
            file: Uploaded file
            folder: Destination folder
            max_size: Maximum dimensions

        Returns:
            dict with url, filename, size
        """
        # Validate file type
        if file.content_type not in self.ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed: JPEG, PNG, GIF, WebP"
            )

        # Read file content
        content = await file.read()

        # Check file size
        if len(content) > self.MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size: {self.MAX_IMAGE_SIZE / 1024 / 1024}MB"
            )

        # Process image
        processed_content = self._process_image(content, max_size)

        # Generate unique filename
        file_ext = Path(file.filename).suffix or '.jpg'
        filename = f"{folder}/{uuid.uuid4().hex}{file_ext}"

        # Save file
        file_url = await self._save_file(filename, processed_content)

        return {
            "url": file_url,
            "filename": filename,
            "size": len(processed_content),
            "content_type": "image/jpeg"
        }

    def _process_image(self, content: bytes, max_size: tuple) -> bytes:
        """
        Resize and optimize image

        Args:
            content: Image bytes
            max_size: Maximum dimensions (width, height)

        Returns:
            Processed image bytes
        """
        try:
            # Open image
            image = Image.open(io.BytesIO(content))

            # Convert RGBA to RGB if needed
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background

            # Resize if needed
            image.thumbnail(max_size, Image.Resampling.LANCZOS)

            # Save to bytes
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=85, optimize=True)
            output.seek(0)

            return output.read()

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error processing image: {str(e)}"
            )

    async def _save_file(self, filename: str, content: bytes) -> str:
        """
        Save file to storage (local or S3)

        Args:
            filename: Relative filename
            content: File bytes

        Returns:
            File URL
        """
        if self.storage_type == 's3':
            return await self._save_to_s3(filename, content)
        else:
            return await self._save_to_local(filename, content)

    async def _save_to_local(self, filename: str, content: bytes) -> str:
        """Save file to local storage"""
        file_path = self.upload_dir / filename

        # Create directories
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        with open(file_path, 'wb') as f:
            f.write(content)

        # Return URL
        return f"/uploads/{filename}"

    async def _save_to_s3(self, filename: str, content: bytes) -> str:
        """
        Save file to AWS S3

        Note: Requires boto3 and AWS credentials
        """
        # TODO: Implement S3 upload
        # This requires:
        # 1. pip install boto3
        # 2. AWS credentials in settings
        # 3. S3 bucket configuration

        raise NotImplementedError("S3 upload not yet implemented. Using local storage.")

    def _sanitize_filename(self, filename: str) -> str:
        """Remove unsafe characters from filename"""
        # Remove non-alphanumeric characters (except dash and underscore)
        safe = "".join(c for c in filename if c.isalnum() or c in ('-', '_'))
        return safe[:50]  # Limit length

    def _calculate_checksum(self, content: bytes) -> str:
        """Calculate MD5 checksum of file"""
        return hashlib.md5(content).hexdigest()

    async def delete_file(self, filename: str) -> bool:
        """
        Delete file from storage

        Args:
            filename: Relative filename

        Returns:
            True if deleted successfully
        """
        if self.storage_type == 's3':
            # TODO: Implement S3 delete
            raise NotImplementedError("S3 delete not yet implemented")
        else:
            file_path = self.upload_dir / filename
            if file_path.exists():
                file_path.unlink()
                return True
            return False


# Global instance
file_upload_service = FileUploadService()
