from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    """
    Extended user profile for additional user information
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    created_at = models.DateTimeField(auto_now_add=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    
    # Storage limits (for future use)
    storage_limit = models.BigIntegerField(
        default=1073741824,  # 1GB default
        help_text="Storage limit in bytes"
    )
    storage_used = models.BigIntegerField(
        default=0,
        help_text="Storage currently used in bytes"
    )
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    @property
    def storage_usage_percentage(self):
        """Calculate storage usage as percentage"""
        if self.storage_limit == 0:
            return 0
        return (self.storage_used / self.storage_limit) * 100
    
    @property
    def formatted_storage_used(self):
        """Get human-readable storage used"""
        size = self.storage_used
        for unit in ['bytes', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    @property
    def formatted_storage_limit(self):
        """Get human-readable storage limit"""
        size = self.storage_limit
        for unit in ['bytes', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def can_upload_file(self, file_size):
        """Check if user can upload a file of given size"""
        return (self.storage_used + file_size) <= self.storage_limit


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create user profile when user is created"""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save user profile when user is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()
