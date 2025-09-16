from django.db import models
from django.contrib.auth.models import User
import os


def user_file_path(instance, filename):
    """Generate file path for user uploads"""
    # Remove any path traversal attempts
    filename = os.path.basename(filename)
    # Create path: uploads/user_id/document_id/revision_number_filename
    return f'uploads/user_{instance.document.owner.id}/{instance.document.id}/{instance.revision_number}_{filename}'


class FileDocument(models.Model):
    """
    Represents a file document with a specific URL path.
    Multiple revisions can exist for the same document.
    """
    url = models.CharField(
        max_length=500, 
        help_text="The URL path where this file should be accessible (e.g., '/documents/reviews/review.pdf')"
    )
    name = models.CharField(
        max_length=255,
        help_text="Original filename"
    )
    owner = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='file_documents'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        # Ensure each user can only have one document per URL path
        unique_together = ['owner', 'url']
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.name} ({self.url}) - {self.owner.username}"
    
    def get_latest_revision(self):
        """Get the most recent revision of this document"""
        return self.revisions.order_by('-revision_number').first()
    
    def get_revision_count(self):
        """Get total number of revisions for this document"""
        return self.revisions.count()


class FileRevision(models.Model):
    """
    Represents a specific revision of a file document.
    Each revision stores the actual file data.
    """
    document = models.ForeignKey(
        FileDocument,
        on_delete=models.CASCADE,
        related_name='revisions'
    )
    file_data = models.FileField(
        upload_to=user_file_path
        # No file extension restrictions - allows any file type as per requirements
    )
    revision_number = models.PositiveIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_size = models.PositiveIntegerField(
        help_text="File size in bytes"
    )
    content_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="MIME type of the file"
    )
    
    class Meta:
        # Ensure unique revision numbers per document
        unique_together = ['document', 'revision_number']
        ordering = ['-revision_number']
    
    def __str__(self):
        return f"{self.document.name} - Revision {self.revision_number}"
    
    def save(self, *args, **kwargs):
        # Auto-set file size if not provided
        if self.file_data and not self.file_size:
            self.file_size = self.file_data.size
        
        # Auto-increment revision number if not set
        if not self.revision_number:
            last_revision = FileRevision.objects.filter(
                document=self.document
            ).order_by('-revision_number').first()
            
            self.revision_number = (last_revision.revision_number + 1) if last_revision else 0
        
        super().save(*args, **kwargs)
    
    @property
    def file_extension(self):
        """Get file extension"""
        if self.file_data:
            return os.path.splitext(self.file_data.name)[1].lower()
        return ''
    
    @property
    def formatted_file_size(self):
        """Get human-readable file size"""
        if not self.file_size:
            return "0 bytes"
        
        size = float(self.file_size)  # Use a copy, don't modify the original
        for unit in ['bytes', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
