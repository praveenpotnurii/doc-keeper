"""
Custom storage backend for file management with enhanced features
"""
import os
import hashlib
import logging
from django.core.files.storage import FileSystemStorage
from django.core.files.base import ContentFile
from django.conf import settings
from django.utils.deconstruct import deconstructible

logger = logging.getLogger(__name__)


@deconstructible
class SecureFileStorage(FileSystemStorage):
    """
    Custom storage backend with enhanced security and organization
    """
    
    def __init__(self, location=None, base_url=None):
        if location is None:
            location = os.path.join(settings.MEDIA_ROOT, 'secure_uploads')
        if base_url is None:
            base_url = settings.MEDIA_URL + 'secure_uploads/'
        super().__init__(location, base_url)
    
    def get_valid_name(self, name):
        """
        Return a filename that's suitable for use in the target storage system
        """
        # Remove directory path and get basename
        name = os.path.basename(name)
        
        # Replace potentially problematic characters
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', ';']
        for char in invalid_chars:
            name = name.replace(char, '_')
        
        # Ensure name isn't empty
        if not name or name.startswith('.'):
            name = 'unnamed_file' + (name if name.startswith('.') else '')
        
        # Limit length
        if len(name) > 255:
            name_part, ext = os.path.splitext(name)
            max_name_length = 255 - len(ext)
            name = name_part[:max_name_length] + ext
        
        return super().get_valid_name(name)
    
    def get_available_name(self, name, max_length=None):
        """
        Return a filename that's free on the target storage system
        """
        if max_length is None:
            max_length = 255
        
        name = self.get_valid_name(name)
        
        # If file doesn't exist, return as is
        if not self.exists(name):
            return name
        
        # Generate unique name
        root, ext = os.path.splitext(name)
        counter = 1
        
        while True:
            candidate = f"{root}_{counter}{ext}"
            if len(candidate) > max_length:
                # Truncate root to fit
                max_root_length = max_length - len(f"_{counter}{ext}")
                candidate = f"{root[:max_root_length]}_{counter}{ext}"
            
            if not self.exists(candidate):
                return candidate
            
            counter += 1
            if counter > 9999:  # Prevent infinite loop
                raise ValueError(f"Could not find available name for {name}")


class FileHashManager:
    """
    Manages file content hashing for deduplication and integrity
    """
    
    @staticmethod
    def calculate_hash(file_obj, algorithm='sha256'):
        """
        Calculate hash of file content
        """
        if algorithm not in ['md5', 'sha1', 'sha256']:
            algorithm = 'sha256'
        
        hasher = getattr(hashlib, algorithm)()
        
        # Reset file pointer
        file_obj.seek(0)
        
        # Read in chunks for memory efficiency
        for chunk in iter(lambda: file_obj.read(8192), b""):
            hasher.update(chunk)
        
        # Reset file pointer
        file_obj.seek(0)
        
        return hasher.hexdigest()
    
    @staticmethod
    def verify_integrity(file_path, expected_hash, algorithm='sha256'):
        """
        Verify file integrity against expected hash
        """
        try:
            with open(file_path, 'rb') as f:
                actual_hash = FileHashManager.calculate_hash(f, algorithm)
                return actual_hash == expected_hash
        except (IOError, OSError):
            return False


class RevisionManager:
    """
    Manages file revisions and their organization
    """
    
    @staticmethod
    def generate_revision_path(document, revision_number, filename):
        """
        Generate organized file path for revision
        Format: uploads/user_{user_id}/{doc_id}/r{revision_number}_{filename}
        """
        clean_filename = SecureFileStorage().get_valid_name(filename)
        return f"uploads/user_{document.owner.id}/{document.id}/r{revision_number}_{clean_filename}"
    
    @staticmethod
    def get_next_revision_number(document):
        """
        Get the next available revision number for a document
        """
        from .models import FileRevision
        
        last_revision = FileRevision.objects.filter(
            document=document
        ).order_by('-revision_number').first()
        
        return (last_revision.revision_number + 1) if last_revision else 0
    
    @staticmethod
    def cleanup_old_revisions(document, keep_count=10):
        """
        Clean up old revisions, keeping only the most recent ones
        """
        from .models import FileRevision
        
        revisions = document.revisions.order_by('-revision_number')
        
        if revisions.count() <= keep_count:
            return 0  # Nothing to clean up
        
        old_revisions = revisions[keep_count:]
        deleted_count = 0
        
        for revision in old_revisions:
            try:
                # Delete file first
                if revision.file_data and revision.file_data.storage.exists(revision.file_data.name):
                    revision.file_data.delete(save=False)
                
                # Delete revision record
                revision.delete()
                deleted_count += 1
                
            except Exception as e:
                logger.error(f"Error deleting revision {revision.id}: {str(e)}")
        
        return deleted_count


class FileMetadataExtractor:
    """
    Extracts and manages file metadata
    """
    
    @staticmethod
    def extract_metadata(file_obj):
        """
        Extract comprehensive metadata from uploaded file
        """
        import mimetypes
        from datetime import datetime
        
        metadata = {
            'filename': getattr(file_obj, 'name', 'unknown'),
            'size': getattr(file_obj, 'size', 0),
            'content_type': getattr(file_obj, 'content_type', None),
            'uploaded_at': datetime.now(),
        }
        
        # Guess content type if not provided
        if not metadata['content_type']:
            metadata['content_type'], _ = mimetypes.guess_type(metadata['filename'])
        
        # Calculate file hash
        try:
            metadata['sha256_hash'] = FileHashManager.calculate_hash(file_obj, 'sha256')
        except Exception as e:
            logger.warning(f"Could not calculate file hash: {str(e)}")
            metadata['sha256_hash'] = None
        
        # Extract file extension
        metadata['extension'] = os.path.splitext(metadata['filename'])[1].lower()
        
        # Basic file type classification
        metadata['file_category'] = FileMetadataExtractor._classify_file_type(
            metadata['extension'], 
            metadata['content_type']
        )
        
        return metadata
    
    @staticmethod
    def _classify_file_type(extension, content_type):
        """
        Classify file into broad categories
        """
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.svg', '.webp'}
        document_extensions = {'.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt'}
        spreadsheet_extensions = {'.xls', '.xlsx', '.csv', '.ods'}
        presentation_extensions = {'.ppt', '.pptx', '.odp'}
        archive_extensions = {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'}
        video_extensions = {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm'}
        audio_extensions = {'.mp3', '.wav', '.flac', '.ogg', '.m4a'}
        
        if extension in image_extensions or (content_type and content_type.startswith('image/')):
            return 'image'
        elif extension in document_extensions or (content_type and 'document' in content_type):
            return 'document'
        elif extension in spreadsheet_extensions or (content_type and 'spreadsheet' in content_type):
            return 'spreadsheet'
        elif extension in presentation_extensions or (content_type and 'presentation' in content_type):
            return 'presentation'
        elif extension in archive_extensions or (content_type and 'archive' in content_type):
            return 'archive'
        elif extension in video_extensions or (content_type and content_type.startswith('video/')):
            return 'video'
        elif extension in audio_extensions or (content_type and content_type.startswith('audio/')):
            return 'audio'
        else:
            return 'other'


class StorageQuotaManager:
    """
    Manages user storage quotas and usage
    """
    
    @staticmethod
    def check_quota_available(user, additional_size):
        """
        Check if user has enough quota for additional storage
        """
        if not hasattr(user, 'profile'):
            return True, 0  # No quota limits if no profile
        
        profile = user.profile
        current_usage = profile.storage_used
        quota_limit = profile.storage_limit
        
        if current_usage + additional_size > quota_limit:
            available = quota_limit - current_usage
            return False, available
        
        return True, quota_limit - current_usage - additional_size
    
    @staticmethod
    def update_user_quota(user):
        """
        Recalculate and update user's storage usage
        """
        if not hasattr(user, 'profile'):
            return 0
        
        total_usage = 0
        
        # Calculate total size from all user's file revisions
        for document in user.file_documents.all():
            for revision in document.revisions.all():
                total_usage += revision.file_size
        
        # Update profile
        user.profile.storage_used = total_usage
        user.profile.save(update_fields=['storage_used'])
        
        return total_usage
    
    @staticmethod
    def get_quota_status(user):
        """
        Get detailed quota status for user
        """
        if not hasattr(user, 'profile'):
            return {
                'has_quota': False,
                'usage': 0,
                'limit': 0,
                'percentage': 0,
                'available': float('inf')
            }
        
        profile = user.profile
        usage = profile.storage_used
        limit = profile.storage_limit
        percentage = (usage / limit * 100) if limit > 0 else 0
        available = max(0, limit - usage)
        
        return {
            'has_quota': True,
            'usage': usage,
            'limit': limit,
            'percentage': percentage,
            'available': available,
            'formatted_usage': profile.formatted_storage_used,
            'formatted_limit': profile.formatted_storage_limit,
        }


# Configure custom storage as default for file uploads
secure_file_storage = SecureFileStorage()