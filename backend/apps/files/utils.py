"""
Utility functions for file handling and management
"""
import os
import hashlib
import mimetypes
from django.core.files.storage import default_storage
from django.conf import settings
from .models import FileDocument, FileRevision


def generate_file_hash(file_obj):
    """
    Generate MD5 hash for file content
    """
    hasher = hashlib.md5()
    
    # Reset file pointer to beginning
    file_obj.seek(0)
    
    # Read file in chunks to handle large files
    for chunk in iter(lambda: file_obj.read(4096), b""):
        hasher.update(chunk)
    
    # Reset file pointer back to beginning
    file_obj.seek(0)
    
    return hasher.hexdigest()


def get_file_mime_type(filename):
    """
    Get MIME type for a file based on its extension
    """
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or 'application/octet-stream'


def validate_file_extension(filename, allowed_extensions=None):
    """
    Validate file extension against allowed list
    """
    if allowed_extensions is None:
        # Default allowed extensions from model
        allowed_extensions = [
            'pdf', 'doc', 'docx', 'txt', 'jpg', 'jpeg', 'png', 'gif',
            'zip', 'rar', 'csv', 'xlsx', 'xls', 'ppt', 'pptx'
        ]
    
    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    return ext in allowed_extensions


def calculate_user_storage_usage(user):
    """
    Calculate total storage used by a user
    """
    total_size = 0
    
    # Sum up file sizes from all user's file revisions
    for document in user.file_documents.all():
        for revision in document.revisions.all():
            if revision.file_data:
                total_size += revision.file_size
    
    return total_size


def update_user_storage_usage(user):
    """
    Update user's storage usage in their profile
    """
    if hasattr(user, 'profile'):
        storage_used = calculate_user_storage_usage(user)
        user.profile.storage_used = storage_used
        user.profile.save()
        return storage_used
    return 0


def check_user_storage_limit(user, additional_size=0):
    """
    Check if user has enough storage space
    """
    if hasattr(user, 'profile'):
        current_usage = user.profile.storage_used
        storage_limit = user.profile.storage_limit
        
        if current_usage + additional_size > storage_limit:
            return False, storage_limit - current_usage
    
    return True, 0


def get_safe_filename(filename):
    """
    Generate a safe filename by removing potentially dangerous characters
    """
    # Remove path components
    filename = os.path.basename(filename)
    
    # Replace unsafe characters
    unsafe_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    
    # Ensure filename is not empty
    if not filename:
        filename = 'unnamed_file'
    
    return filename


def create_file_document(user, url, name, file_obj):
    """
    Create or update a file document with a new revision
    """
    # Get or create the document
    document, created = FileDocument.objects.get_or_create(
        owner=user,
        url=url,
        defaults={'name': name}
    )
    
    # If document exists but name is different, update it
    if not created and document.name != name:
        document.name = name
        document.save()
    
    # Create new revision
    revision = FileRevision.objects.create(
        document=document,
        file_data=file_obj,
        content_type=get_file_mime_type(file_obj.name)
    )
    
    # Update user storage usage
    update_user_storage_usage(user)
    
    return document, revision


def delete_file_revision(revision):
    """
    Delete a file revision and update storage usage
    """
    user = revision.document.owner
    
    # Delete the actual file
    if revision.file_data:
        if default_storage.exists(revision.file_data.name):
            default_storage.delete(revision.file_data.name)
    
    # Delete the revision
    revision.delete()
    
    # Update storage usage
    update_user_storage_usage(user)


def delete_file_document(document):
    """
    Delete a file document and all its revisions
    """
    user = document.owner
    
    # Delete all revision files
    for revision in document.revisions.all():
        if revision.file_data:
            if default_storage.exists(revision.file_data.name):
                default_storage.delete(revision.file_data.name)
    
    # Delete the document (will cascade delete revisions)
    document.delete()
    
    # Update storage usage
    update_user_storage_usage(user)


def get_file_stats_for_user(user):
    """
    Get comprehensive file statistics for a user
    """
    documents = user.file_documents.all()
    total_documents = documents.count()
    total_revisions = sum(doc.get_revision_count() for doc in documents)
    
    # File type breakdown
    file_types = {}
    total_size = 0
    
    for document in documents:
        for revision in document.revisions.all():
            ext = revision.file_extension or 'unknown'
            file_types[ext] = file_types.get(ext, 0) + 1
            total_size += revision.file_size
    
    return {
        'total_documents': total_documents,
        'total_revisions': total_revisions,
        'total_size': total_size,
        'file_types': file_types,
        'storage_usage': user.profile.storage_used if hasattr(user, 'profile') else 0,
        'storage_limit': user.profile.storage_limit if hasattr(user, 'profile') else 0,
    }


def format_file_size(size_bytes):
    """
    Format file size in human-readable format
    """
    if size_bytes == 0:
        return "0 bytes"
    
    size_names = ["bytes", "KB", "MB", "GB", "TB"]
    size = float(size_bytes)
    i = 0
    
    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    return f"{size:.1f} {size_names[i]}"