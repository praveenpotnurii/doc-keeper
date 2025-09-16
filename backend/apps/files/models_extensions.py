"""
Extensions and enhancements for file models
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
import json
import logging

from .storage import secure_file_storage, FileMetadataExtractor, StorageQuotaManager
from .models import FileDocument, FileRevision

logger = logging.getLogger(__name__)


class FileMetadata(models.Model):
    """
    Extended metadata for file revisions
    """
    revision = models.OneToOneField(
        FileRevision,
        on_delete=models.CASCADE,
        related_name='metadata'
    )
    
    # File hashes for integrity checking
    sha256_hash = models.CharField(max_length=64, blank=True)
    md5_hash = models.CharField(max_length=32, blank=True)
    
    # File classification
    file_category = models.CharField(
        max_length=20,
        choices=[
            ('image', 'Image'),
            ('document', 'Document'),
            ('spreadsheet', 'Spreadsheet'),
            ('presentation', 'Presentation'),
            ('archive', 'Archive'),
            ('video', 'Video'),
            ('audio', 'Audio'),
            ('other', 'Other'),
        ],
        default='other'
    )
    
    # Extended metadata as JSON
    extra_metadata = models.JSONField(default=dict, blank=True)
    
    # Processing status
    is_processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "File Metadata"
        verbose_name_plural = "File Metadata"
    
    def __str__(self):
        return f"Metadata for {self.revision}"
    
    def save(self, *args, **kwargs):
        # Auto-process metadata if not done
        if not self.is_processed and self.revision.file_data:
            try:
                self._extract_metadata()
                self.is_processed = True
            except Exception as e:
                self.processing_error = str(e)
                logger.error(f"Error processing metadata for revision {self.revision.id}: {str(e)}")
        
        super().save(*args, **kwargs)
    
    def _extract_metadata(self):
        """Extract metadata from file"""
        if not self.revision.file_data:
            return
        
        try:
            file_obj = self.revision.file_data.open('rb')
            metadata = FileMetadataExtractor.extract_metadata(file_obj)
            file_obj.close()
            
            # Update fields
            self.sha256_hash = metadata.get('sha256_hash', '')
            self.file_category = metadata.get('file_category', 'other')
            self.extra_metadata = {
                'original_filename': metadata.get('filename', ''),
                'detected_content_type': metadata.get('content_type', ''),
                'file_extension': metadata.get('extension', ''),
            }
            
        except Exception as e:
            raise ValidationError(f"Could not extract metadata: {str(e)}")


class FileAccessLog(models.Model):
    """
    Log file access for analytics and security
    """
    document = models.ForeignKey(
        FileDocument,
        on_delete=models.CASCADE,
        related_name='access_logs'
    )
    revision = models.ForeignKey(
        FileRevision,
        on_delete=models.CASCADE,
        related_name='access_logs',
        null=True, blank=True
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    access_type = models.CharField(
        max_length=20,
        choices=[
            ('view', 'View Details'),
            ('download', 'Download File'),
            ('upload', 'Upload Revision'),
            ('delete', 'Delete File'),
        ]
    )
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    accessed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-accessed_at']
        indexes = [
            models.Index(fields=['document', '-accessed_at']),
            models.Index(fields=['user', '-accessed_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} {self.access_type} {self.document.name} at {self.accessed_at}"


class FileShare(models.Model):
    """
    File sharing with external users (future feature)
    """
    document = models.ForeignKey(
        FileDocument,
        on_delete=models.CASCADE,
        related_name='shares'
    )
    shared_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Sharing configuration
    share_token = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Access control
    require_password = models.BooleanField(default=False)
    password_hash = models.CharField(max_length=128, blank=True)
    max_downloads = models.PositiveIntegerField(null=True, blank=True)
    download_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Share of {self.document.name} by {self.shared_by.username}"
    
    def is_valid(self):
        """Check if share is still valid"""
        if not self.is_active:
            return False
        
        if self.expires_at and self.expires_at < timezone.now():
            return False
        
        if self.max_downloads and self.download_count >= self.max_downloads:
            return False
        
        return True


# Model managers for enhanced functionality
class FileDocumentManager(models.Manager):
    """Custom manager for FileDocument"""
    
    def for_user(self, user):
        """Get all documents for a user"""
        return self.filter(owner=user)
    
    def search(self, user, query):
        """Search documents by name or URL"""
        return self.for_user(user).filter(
            models.Q(name__icontains=query) | 
            models.Q(url__icontains=query)
        )
    
    def by_category(self, user, category):
        """Get documents by file category"""
        return self.for_user(user).filter(
            revisions__metadata__file_category=category
        ).distinct()
    
    def recent(self, user, days=7):
        """Get recently modified documents"""
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(days=days)
        return self.for_user(user).filter(updated_at__gte=cutoff)


class FileRevisionManager(models.Manager):
    """Custom manager for FileRevision"""
    
    def for_document(self, document):
        """Get all revisions for a document"""
        return self.filter(document=document)
    
    def latest_for_documents(self, documents):
        """Get latest revision for each document"""
        latest_revisions = []
        for doc in documents:
            latest = self.filter(document=doc).order_by('-revision_number').first()
            if latest:
                latest_revisions.append(latest)
        return latest_revisions


# Monkey patch the existing models to add managers
# This allows us to enhance existing models without migration
FileDocument.add_to_class('enhanced_objects', FileDocumentManager())
FileRevision.add_to_class('enhanced_objects', FileRevisionManager())


# Signal handlers for automatic processing
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver


@receiver(post_save, sender=FileRevision)
def create_file_metadata(sender, instance, created, **kwargs):
    """Automatically create metadata for new revisions"""
    if created:
        try:
            FileMetadata.objects.create(revision=instance)
        except Exception as e:
            logger.error(f"Error creating metadata for revision {instance.id}: {str(e)}")


@receiver(post_save, sender=FileRevision)
def update_user_storage(sender, instance, created, **kwargs):
    """Update user storage quota when revision is saved"""
    if created:
        try:
            StorageQuotaManager.update_user_quota(instance.document.owner)
        except Exception as e:
            logger.error(f"Error updating storage quota: {str(e)}")


@receiver(pre_delete, sender=FileRevision)
def cleanup_revision_files(sender, instance, **kwargs):
    """Clean up files when revision is deleted"""
    try:
        # Delete the actual file
        if instance.file_data and instance.file_data.storage.exists(instance.file_data.name):
            instance.file_data.delete(save=False)
    except Exception as e:
        logger.error(f"Error cleaning up revision files: {str(e)}")


@receiver(pre_delete, sender=FileDocument)
def update_storage_on_delete(sender, instance, **kwargs):
    """Update storage quota when document is deleted"""
    try:
        # Update quota after deletion
        def update_quota():
            StorageQuotaManager.update_user_quota(instance.owner)
        
        # Schedule update after deletion
        from django.db import transaction
        transaction.on_commit(update_quota)
        
    except Exception as e:
        logger.error(f"Error updating storage on delete: {str(e)}")


# Utility functions for enhanced file management
def get_file_statistics(user, days=30):
    """Get comprehensive file statistics for user"""
    from datetime import timedelta
    from django.db.models import Count, Sum
    
    cutoff = timezone.now() - timedelta(days=days)
    
    # Basic counts
    total_docs = FileDocument.objects.filter(owner=user).count()
    total_revisions = FileRevision.objects.filter(document__owner=user).count()
    recent_uploads = FileRevision.objects.filter(
        document__owner=user,
        uploaded_at__gte=cutoff
    ).count()
    
    # Category breakdown
    categories = FileMetadata.objects.filter(
        revision__document__owner=user
    ).values('file_category').annotate(
        count=Count('id')
    )
    
    # Storage info
    quota_status = StorageQuotaManager.get_quota_status(user)
    
    return {
        'total_documents': total_docs,
        'total_revisions': total_revisions,
        'recent_uploads': recent_uploads,
        'categories': {item['file_category']: item['count'] for item in categories},
        'storage': quota_status,
    }


def cleanup_old_revisions(user, keep_per_document=5):
    """Clean up old revisions for user"""
    from .storage import RevisionManager
    
    documents = FileDocument.objects.filter(owner=user)
    total_cleaned = 0
    
    for document in documents:
        cleaned = RevisionManager.cleanup_old_revisions(document, keep_per_document)
        total_cleaned += cleaned
    
    # Update storage quota
    StorageQuotaManager.update_user_quota(user)
    
    return total_cleaned