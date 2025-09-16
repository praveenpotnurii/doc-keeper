"""
Custom permissions for file access control
"""
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
import logging

from .models import FileDocument, FileRevision
from .models_extensions import FileAccessLog

logger = logging.getLogger(__name__)


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    message = "You can only access your own files."
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for any authenticated user (but we'll override this)
        if request.method in permissions.SAFE_METHODS:
            return self._check_owner(request.user, obj)
        
        # Write permissions only to the owner
        return self._check_owner(request.user, obj)
    
    def _check_owner(self, user, obj):
        """Check if user owns the object"""
        if hasattr(obj, 'owner'):
            return obj.owner == user
        elif hasattr(obj, 'document'):
            return obj.document.owner == user
        return False


class FileAccessPermission(permissions.BasePermission):
    """
    Comprehensive file access permission with logging
    """
    message = "Access denied to this file."
    
    def has_permission(self, request, view):
        """Check if user has general permission to access files"""
        if not request.user.is_authenticated:
            return False
        
        # Check if user account is active
        if not request.user.is_active:
            self.message = "Your account is not active."
            return False
        
        # Check for rate limiting (optional)
        if self._is_rate_limited(request.user):
            self.message = "Too many requests. Please try again later."
            return False
        
        return True
    
    def has_object_permission(self, request, view, obj):
        """Check specific object permissions"""
        if not self.has_permission(request, view):
            return False
        
        # Check ownership
        if not self._is_owner(request.user, obj):
            self._log_unauthorized_access(request, obj)
            return False
        
        # Additional checks based on request method
        if request.method in ['DELETE']:
            return self._can_delete(request.user, obj)
        elif request.method in ['PUT', 'PATCH']:
            return self._can_modify(request.user, obj)
        
        return True
    
    def _is_owner(self, user, obj):
        """Check if user is the owner"""
        if isinstance(obj, FileDocument):
            return obj.owner == user
        elif isinstance(obj, FileRevision):
            return obj.document.owner == user
        elif hasattr(obj, 'owner'):
            return obj.owner == user
        elif hasattr(obj, 'document'):
            return obj.document.owner == user
        return False
    
    def _can_delete(self, user, obj):
        """Check if user can delete the object"""
        # For now, owners can delete anything they own
        # This could be extended to check for shared files, etc.
        return self._is_owner(user, obj)
    
    def _can_modify(self, user, obj):
        """Check if user can modify the object"""
        # Basic ownership check - can be extended
        return self._is_owner(user, obj)
    
    def _is_rate_limited(self, user):
        """Check if user is rate limited"""
        # Simple rate limiting - max 1000 requests per hour
        one_hour_ago = timezone.now() - timedelta(hours=1)
        recent_requests = FileAccessLog.objects.filter(
            user=user,
            accessed_at__gte=one_hour_ago
        ).count()
        
        return recent_requests > 1000
    
    def _log_unauthorized_access(self, request, obj):
        """Log unauthorized access attempts"""
        try:
            document = obj if isinstance(obj, FileDocument) else getattr(obj, 'document', None)
            if document:
                logger.warning(
                    f"Unauthorized access attempt by {request.user.username} "
                    f"to file {document.id} ({document.name})"
                )
        except Exception:
            pass  # Don't fail if logging fails


class StorageQuotaPermission(permissions.BasePermission):
    """
    Permission to check storage quota before uploads
    """
    message = "Storage quota exceeded."
    
    def has_permission(self, request, view):
        """Check storage quota for upload operations"""
        if request.method not in ['POST', 'PUT']:
            return True  # Only check for uploads
        
        # Check if file is being uploaded
        if 'file' not in request.data and 'file_data' not in request.data:
            return True
        
        user = request.user
        if not hasattr(user, 'profile'):
            return True  # No quota if no profile
        
        # Get file size
        file_obj = request.data.get('file') or request.data.get('file_data')
        if not file_obj:
            return True
        
        file_size = getattr(file_obj, 'size', 0)
        if file_size == 0:
            return True
        
        # Check quota
        profile = user.profile
        if profile.storage_used + file_size > profile.storage_limit:
            available = profile.storage_limit - profile.storage_used
            self.message = (
                f"Upload would exceed storage limit. "
                f"Available: {available} bytes, Required: {file_size} bytes"
            )
            return False
        
        return True


class FileTypePermission(permissions.BasePermission):
    """
    Permission to restrict file types based on user level
    """
    # Define allowed extensions by user type
    BASIC_ALLOWED = {'.txt', '.pdf', '.jpg', '.png', '.gif', '.doc', '.docx'}
    PREMIUM_ALLOWED = BASIC_ALLOWED | {'.zip', '.rar', '.mp4', '.avi', '.psd', '.ai'}
    ADMIN_ALLOWED = None  # No restrictions
    
    def has_permission(self, request, view):
        """Check file type permissions"""
        if request.method not in ['POST', 'PUT']:
            return True
        
        # Get uploaded file
        file_obj = request.data.get('file') or request.data.get('file_data')
        if not file_obj:
            return True
        
        filename = getattr(file_obj, 'name', '')
        if not filename:
            return True
        
        # Get file extension
        import os
        ext = os.path.splitext(filename)[1].lower()
        
        # Check permissions based on user type
        user = request.user
        if user.is_superuser:
            return True  # Admins can upload anything
        
        # For now, all users get premium permissions
        # This could be extended to check user subscription level
        allowed_extensions = self.PREMIUM_ALLOWED
        
        if allowed_extensions and ext not in allowed_extensions:
            self.message = f"File type '{ext}' is not allowed for your account level."
            return False
        
        return True


class ReadOnlyPermission(permissions.BasePermission):
    """
    Permission class for read-only access
    """
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS


class FileViewPermission(permissions.BasePermission):
    """
    Permission for viewing file details and downloading
    """
    def has_object_permission(self, request, view, obj):
        # Only allow GET requests
        if request.method not in permissions.SAFE_METHODS:
            return False
        
        # Check ownership
        user = request.user
        if isinstance(obj, FileDocument):
            return obj.owner == user
        elif isinstance(obj, FileRevision):
            return obj.document.owner == user
        
        return False


class BulkOperationPermission(permissions.BasePermission):
    """
    Permission for bulk operations like bulk delete
    """
    message = "Bulk operations require special permission."
    
    def has_permission(self, request, view):
        """Check if user can perform bulk operations"""
        user = request.user
        
        # Basic authentication check
        if not user.is_authenticated:
            return False
        
        # Limit bulk operations to prevent abuse
        urls = request.data.get('urls', [])
        if len(urls) > 100:  # Max 100 files at once
            self.message = "Cannot delete more than 100 files at once."
            return False
        
        # Check if all files belong to the user
        if request.method == 'POST' and urls:
            user_file_urls = set(
                FileDocument.objects.filter(owner=user).values_list('url', flat=True)
            )
            
            invalid_urls = [url for url in urls if url not in user_file_urls]
            if invalid_urls:
                self.message = f"You don't own some of the specified files: {invalid_urls[:5]}"
                return False
        
        return True


# Middleware for additional security
class FileAccessMiddleware:
    """
    Middleware to add additional security layers for file access
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Process request before view
        self._process_request(request)
        
        response = self.get_response(request)
        
        # Process response after view
        self._process_response(request, response)
        
        return response
    
    def _process_request(self, request):
        """Add security headers and checks"""
        # Add security context to request
        request.security_context = {
            'ip_address': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'timestamp': timezone.now(),
        }
    
    def _process_response(self, request, response):
        """Add security headers to response"""
        # Add security headers for file downloads
        if hasattr(request, 'resolver_match') and request.resolver_match:
            if 'files' in request.resolver_match.app_name or '':
                # Prevent caching of sensitive files
                response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response['Pragma'] = 'no-cache'
                response['Expires'] = '0'
                
                # Add content security policy
                response['Content-Security-Policy'] = "default-src 'none'"
                
                # Prevent MIME type sniffing
                response['X-Content-Type-Options'] = 'nosniff'
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


# Decorator for additional permission checks
def require_file_owner(view_func):
    """
    Decorator to ensure user owns the file being accessed
    """
    def wrapper(request, *args, **kwargs):
        # Get file ID or URL from kwargs
        file_id = kwargs.get('file_id') or kwargs.get('pk')
        file_url = kwargs.get('url')
        
        if file_id:
            try:
                document = FileDocument.objects.get(id=file_id)
                if document.owner != request.user:
                    raise PermissionDenied("You don't own this file")
            except FileDocument.DoesNotExist:
                raise PermissionDenied("File not found")
        
        elif file_url:
            try:
                document = FileDocument.objects.get(url=file_url, owner=request.user)
            except FileDocument.DoesNotExist:
                raise PermissionDenied("File not found or access denied")
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


# Utility functions for permission checking
def user_can_access_file(user, file_document):
    """Check if user can access a specific file"""
    if not user.is_authenticated:
        return False
    
    return file_document.owner == user


def user_can_upload_file(user, file_size=0):
    """Check if user can upload a file of given size"""
    if not user.is_authenticated:
        return False, "User not authenticated"
    
    if not hasattr(user, 'profile'):
        return True, "No quota restrictions"
    
    profile = user.profile
    if profile.storage_used + file_size > profile.storage_limit:
        return False, "Storage quota exceeded"
    
    return True, "Upload allowed"


def log_file_access(user, document, access_type='view', request=None):
    """Log file access for audit purposes"""
    try:
        ip_address = None
        user_agent = ""
        
        if request:
            ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0]
            if not ip_address:
                ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        FileAccessLog.objects.create(
            document=document,
            user=user,
            access_type=access_type,
            ip_address=ip_address,
            user_agent=user_agent[:500]  # Limit length
        )
    except Exception as e:
        # Don't fail the request if logging fails
        logger.error(f"Failed to log file access: {str(e)}")


# Permission sets for different use cases
OWNER_PERMISSIONS = [permissions.IsAuthenticated, FileAccessPermission]
UPLOAD_PERMISSIONS = [permissions.IsAuthenticated, StorageQuotaPermission, FileTypePermission]
BULK_PERMISSIONS = [permissions.IsAuthenticated, BulkOperationPermission]
VIEW_PERMISSIONS = [permissions.IsAuthenticated, FileViewPermission]