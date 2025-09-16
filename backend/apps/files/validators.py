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
    Validate file extension - now allows any extension as per requirements
    """
    # Allow any file extension as per requirements
    # Only perform basic filename validation
    filename = file_obj.name
    if not filename:
        raise ValidationError('Filename is required.')
    
    # No extension restrictions - all file types are allowed


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
    Validate file content type - now allows any content type as per requirements
    """
    # Allow any content type as per requirements
    # Only basic validation for empty content type
    content_type = getattr(file_obj, 'content_type', None)
    
    # No content type restrictions - all file types are allowed
    # This ensures the requirement "stores files of any type" is met


def validate_file_content(file_obj):
    """
    Basic file content validation - minimal restrictions for security
    """
    # Reset file pointer
    file_obj.seek(0)
    
    # Read first few bytes to check for empty files
    header = file_obj.read(16)
    file_obj.seek(0)  # Reset pointer
    
    if len(header) == 0:
        raise ValidationError('File appears to be empty.')
    
    # Minimal security check - only block obviously dangerous executable types
    # This maintains the requirement to accept "any type" while providing basic security
    dangerous_signatures = [
        b'\x4d\x5a',  # PE executable (MZ) - only block Windows executables
    ]
    
    for signature in dangerous_signatures:
        if header.startswith(signature):
            raise ValidationError('Windows executable files are not allowed for security reasons.')


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