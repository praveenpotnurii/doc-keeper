"""
Custom validators for file uploads and management
"""
import os
import re
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.conf import settings


def validate_file_size(file_obj, max_size_mb=10):
    """
    Validate file size
    """
    max_size = max_size_mb * 1024 * 1024  # Convert MB to bytes
    
    if file_obj.size > max_size:
        raise ValidationError(
            f'File size too large. Maximum size allowed is {max_size_mb}MB. '
            f'Your file is {file_obj.size / (1024*1024):.1f}MB.'
        )
    
    if file_obj.size == 0:
        raise ValidationError('File is empty.')


def validate_file_extension(file_obj, allowed_extensions=None):
    """
    Validate file extension
    """
    if allowed_extensions is None:
        allowed_extensions = [
            'pdf', 'doc', 'docx', 'txt', 'rtf',
            'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff',
            'zip', 'rar', '7z', 'tar', 'gz',
            'csv', 'xlsx', 'xls', 'ods',
            'ppt', 'pptx', 'odp',
            'mp4', 'avi', 'mov', 'wmv', 'flv',
            'mp3', 'wav', 'flac', 'ogg'
        ]
    
    filename = file_obj.name
    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    
    if ext not in allowed_extensions:
        raise ValidationError(
            f'File type ".{ext}" not allowed. '
            f'Allowed types: {", ".join(allowed_extensions)}'
        )


def validate_filename(filename):
    """
    Validate filename for security and compatibility
    """
    # Check for empty filename
    if not filename or filename.strip() == '':
        raise ValidationError('Filename cannot be empty.')
    
    # Check filename length
    if len(filename) > 255:
        raise ValidationError('Filename too long. Maximum 255 characters allowed.')
    
    # Check for potentially dangerous filenames
    dangerous_names = [
        'con', 'prn', 'aux', 'nul',
        'com1', 'com2', 'com3', 'com4', 'com5', 'com6', 'com7', 'com8', 'com9',
        'lpt1', 'lpt2', 'lpt3', 'lpt4', 'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9'
    ]
    
    name_without_ext = os.path.splitext(filename)[0].lower()
    if name_without_ext in dangerous_names:
        raise ValidationError(f'Filename "{filename}" is not allowed.')
    
    # Check for invalid characters
    invalid_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
    for char in invalid_chars:
        if char in filename:
            raise ValidationError(f'Filename contains invalid character: {char}')
    
    # Check for control characters
    if any(ord(char) < 32 for char in filename):
        raise ValidationError('Filename contains invalid control characters.')


def validate_url_path(url_path):
    """
    Validate URL path format and security
    """
    # Check for empty path
    if not url_path or url_path.strip() == '':
        raise ValidationError('URL path cannot be empty.')
    
    # Must start with /
    if not url_path.startswith('/'):
        raise ValidationError('URL path must start with "/".')
    
    # Cannot end with / (except root)
    if len(url_path) > 1 and url_path.endswith('/'):
        raise ValidationError('URL path cannot end with "/" (except root path).')
    
    # Check length
    if len(url_path) > 500:
        raise ValidationError('URL path too long. Maximum 500 characters allowed.')
    
    # Check for invalid patterns
    invalid_patterns = [
        r'\.\./',  # Directory traversal
        r'/\.\.', 
        r'//+',    # Double slashes
        r'[\x00-\x1f]',  # Control characters
        r'[<>"|?*]',     # Invalid URL characters
    ]
    
    for pattern in invalid_patterns:
        if re.search(pattern, url_path):
            raise ValidationError(f'URL path contains invalid pattern.')
    
    # Check for reserved paths
    reserved_paths = [
        '/admin', '/api', '/static', '/media',
        '/api-auth', '/docs', '/swagger'
    ]
    
    for reserved in reserved_paths:
        if url_path.startswith(reserved + '/') or url_path == reserved:
            raise ValidationError(f'URL path "{reserved}" is reserved.')


def validate_content_type(file_obj, allowed_types=None):
    """
    Validate file content type
    """
    if allowed_types is None:
        allowed_types = [
            # Documents
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain',
            'text/rtf',
            
            # Images
            'image/jpeg',
            'image/png',
            'image/gif',
            'image/bmp',
            'image/tiff',
            
            # Archives
            'application/zip',
            'application/x-rar-compressed',
            'application/x-7z-compressed',
            
            # Spreadsheets
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'text/csv',
            
            # Presentations
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            
            # Video
            'video/mp4',
            'video/avi',
            'video/quicktime',
            
            # Audio
            'audio/mpeg',
            'audio/wav',
            'audio/flac',
        ]
    
    # Get content type from file
    content_type = getattr(file_obj, 'content_type', None)
    
    if content_type and content_type not in allowed_types:
        raise ValidationError(
            f'File content type "{content_type}" not allowed.'
        )


def validate_file_content(file_obj):
    """
    Basic file content validation
    """
    # Reset file pointer
    file_obj.seek(0)
    
    # Read first few bytes to check for common file signatures
    header = file_obj.read(16)
    file_obj.seek(0)  # Reset pointer
    
    if len(header) == 0:
        raise ValidationError('File appears to be empty.')
    
    # Check for potentially malicious files
    malicious_signatures = [
        b'\x4d\x5a',  # PE executable (MZ)
        b'\x7f\x45\x4c\x46',  # ELF executable
    ]
    
    for signature in malicious_signatures:
        if header.startswith(signature):
            raise ValidationError('Executable files are not allowed.')


def validate_user_storage_limit(user, additional_size):
    """
    Validate that user has enough storage space
    """
    if hasattr(user, 'profile'):
        current_usage = user.profile.storage_used
        storage_limit = user.profile.storage_limit
        
        if current_usage + additional_size > storage_limit:
            available_space = storage_limit - current_usage
            raise ValidationError(
                f'Not enough storage space. '
                f'Available: {available_space / (1024*1024):.1f}MB, '
                f'Required: {additional_size / (1024*1024):.1f}MB'
            )


def validate_file_upload(file_obj, user=None, url_path=None):
    """
    Comprehensive file upload validation
    """
    # Basic file validations
    validate_file_size(file_obj)
    validate_file_extension(file_obj)
    validate_filename(file_obj.name)
    validate_content_type(file_obj)
    validate_file_content(file_obj)
    
    # URL path validation
    if url_path:
        validate_url_path(url_path)
    
    # User storage validation
    if user:
        validate_user_storage_limit(user, file_obj.size)