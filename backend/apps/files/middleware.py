"""
Security middleware for file access
"""
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponseForbidden
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
import logging
import json
from datetime import timedelta

from .models_extensions import FileAccessLog

logger = logging.getLogger(__name__)


class FileSecurityMiddleware(MiddlewareMixin):
    """
    Middleware for additional file security measures
    """
    
    def process_request(self, request):
        """Process incoming requests for security"""
        # Skip non-file requests
        if not self._is_file_request(request):
            return None
        
        # Add security context
        request.file_security = {
            'ip_address': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'timestamp': timezone.now(),
            'is_suspicious': False,
        }
        
        # Check for suspicious activity
        if self._is_suspicious_request(request):
            request.file_security['is_suspicious'] = True
            logger.warning(f"Suspicious file access from {request.file_security['ip_address']}")
            
            # Optionally block suspicious requests
            if getattr(settings, 'BLOCK_SUSPICIOUS_FILE_ACCESS', False):
                return HttpResponseForbidden("Access denied due to suspicious activity")
        
        # Rate limiting
        if self._is_rate_limited(request):
            logger.warning(f"Rate limit exceeded for {request.file_security['ip_address']}")
            return HttpResponseForbidden("Rate limit exceeded. Please try again later.")
        
        return None
    
    def process_response(self, request, response):
        """Process outgoing responses"""
        if not self._is_file_request(request):
            return response
        
        # Add security headers for file responses
        if response.status_code == 200:
            self._add_security_headers(request, response)
        
        # Log the response
        if hasattr(request, 'file_security'):
            self._log_file_response(request, response)
        
        return response
    
    def _is_file_request(self, request):
        """Check if this is a file-related request"""
        path = request.path
        return (
            path.startswith('/api/files/') or
            path.startswith('/media/') or
            'download' in request.GET
        )
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')
    
    def _is_suspicious_request(self, request):
        """Detect suspicious file access patterns"""
        ip = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        
        # Check for suspicious user agents
        suspicious_agents = [
            'wget', 'curl', 'bot', 'crawler', 'spider', 'scraper',
            'python-requests', 'java/', 'go-http-client'
        ]
        
        for agent in suspicious_agents:
            if agent in user_agent:
                return True
        
        # Check for rapid sequential requests from same IP
        cache_key = f"file_requests_{ip}"
        recent_requests = cache.get(cache_key, 0)
        
        if recent_requests > 50:  # More than 50 requests in the cache period
            return True
        
        # Increment counter
        cache.set(cache_key, recent_requests + 1, timeout=300)  # 5-minute window
        
        return False
    
    def _is_rate_limited(self, request):
        """Check if IP is rate limited"""
        ip = self._get_client_ip(request)
        
        # Different limits for authenticated vs anonymous users
        if request.user.is_authenticated:
            limit = getattr(settings, 'AUTHENTICATED_FILE_RATE_LIMIT', 1000)
        else:
            limit = getattr(settings, 'ANONYMOUS_FILE_RATE_LIMIT', 100)
        
        # Check requests in last hour
        cache_key = f"file_rate_limit_{ip}"
        requests_count = cache.get(cache_key, 0)
        
        if requests_count >= limit:
            return True
        
        # Increment counter
        cache.set(cache_key, requests_count + 1, timeout=3600)  # 1-hour window
        
        return False
    
    def _add_security_headers(self, request, response):
        """Add security headers to file responses"""
        # Prevent caching of sensitive files
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        
        # Content security policy
        response['Content-Security-Policy'] = "default-src 'none'"
        
        # Prevent MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        
        # Frame options
        response['X-Frame-Options'] = 'DENY'
        
        # XSS protection
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    def _log_file_response(self, request, response):
        """Log file response for audit"""
        if not getattr(settings, 'LOG_FILE_ACCESS_RESPONSES', True):
            return
        
        try:
            log_data = {
                'ip': request.file_security.get('ip_address'),
                'user_agent': request.file_security.get('user_agent'),
                'method': request.method,
                'path': request.path,
                'status_code': response.status_code,
                'user_id': request.user.id if request.user.is_authenticated else None,
                'timestamp': request.file_security.get('timestamp').isoformat(),
                'suspicious': request.file_security.get('is_suspicious'),
            }
            
            logger.info(f"File access: {json.dumps(log_data)}")
            
        except Exception as e:
            logger.error(f"Failed to log file response: {str(e)}")


class FileAccessAuditMiddleware(MiddlewareMixin):
    """
    Middleware for comprehensive file access auditing
    """
    
    def process_response(self, request, response):
        """Log detailed file access for audit purposes"""
        if not self._should_audit(request, response):
            return response
        
        try:
            self._create_audit_log(request, response)
        except Exception as e:
            logger.error(f"Failed to create audit log: {str(e)}")
        
        return response
    
    def _should_audit(self, request, response):
        """Determine if this request should be audited"""
        # Only audit successful file operations
        if response.status_code not in [200, 201]:
            return False
        
        # Only audit file-related requests
        if not request.path.startswith('/api/files/'):
            return False
        
        return True
    
    def _create_audit_log(self, request, response):
        """Create detailed audit log entry"""
        if not request.user.is_authenticated:
            return
        
        # Extract file information from request
        file_info = self._extract_file_info(request)
        if not file_info:
            return
        
        # Create audit log (this could be stored in a separate audit table)
        audit_data = {
            'user_id': request.user.id,
            'username': request.user.username,
            'action': self._determine_action(request),
            'file_info': file_info,
            'ip_address': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'timestamp': timezone.now().isoformat(),
            'status_code': response.status_code,
        }
        
        # Log to file or external service
        logger.info(f"File audit: {json.dumps(audit_data)}")
    
    def _extract_file_info(self, request):
        """Extract file information from request"""
        path_parts = request.path.strip('/').split('/')
        
        if len(path_parts) < 3 or path_parts[1] != 'files':
            return None
        
        if path_parts[2] == 'stats' or path_parts[2] == 'analytics':
            return {'type': 'stats'}
        
        # For file operations, try to extract file URL or ID
        if len(path_parts) > 2:
            return {
                'type': 'file_operation',
                'file_identifier': '/'.join(path_parts[2:])
            }
        
        return {'type': 'file_list'}
    
    def _determine_action(self, request):
        """Determine the action being performed"""
        method = request.method.upper()
        
        if 'download=true' in request.GET.urlencode():
            return 'DOWNLOAD'
        elif method == 'GET':
            return 'VIEW'
        elif method == 'POST':
            return 'UPLOAD'
        elif method == 'PUT':
            return 'UPDATE'
        elif method == 'DELETE':
            return 'DELETE'
        
        return method
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')


class FileDownloadSecurityMiddleware(MiddlewareMixin):
    """
    Specialized middleware for file download security
    """
    
    def process_response(self, request, response):
        """Secure file downloads"""
        if not self._is_file_download(request, response):
            return response
        
        # Add download-specific security headers
        self._secure_download_response(response)
        
        # Log download
        self._log_download(request, response)
        
        return response
    
    def _is_file_download(self, request, response):
        """Check if this is a file download"""
        return (
            response.status_code == 200 and
            ('download=true' in request.GET.urlencode() or
             'attachment' in response.get('Content-Disposition', ''))
        )
    
    def _secure_download_response(self, response):
        """Add security headers for file downloads"""
        # Force download (don't display in browser)
        if 'Content-Disposition' not in response:
            response['Content-Disposition'] = 'attachment'
        
        # Prevent caching
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        
        # Security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
    
    def _log_download(self, request, response):
        """Log file download"""
        if request.user.is_authenticated:
            try:
                logger.info(
                    f"File download by {request.user.username} "
                    f"from {self._get_client_ip(request)} "
                    f"- Size: {response.get('Content-Length', 'unknown')} bytes"
                )
            except Exception:
                pass
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')