"""
Management command for file cleanup and maintenance
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import os

from apps.files.models import FileDocument, FileRevision
from apps.files.models_extensions import FileMetadata, cleanup_old_revisions
from apps.files.storage import StorageQuotaManager


class Command(BaseCommand):
    help = 'Cleanup and maintain file storage system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cleanup-revisions',
            action='store_true',
            help='Clean up old revisions (keep 5 most recent per document)'
        )
        
        parser.add_argument(
            '--keep-revisions',
            type=int,
            default=5,
            help='Number of revisions to keep per document'
        )
        
        parser.add_argument(
            '--cleanup-orphaned',
            action='store_true',
            help='Clean up orphaned files without database records'
        )
        
        parser.add_argument(
            '--update-quotas',
            action='store_true',
            help='Recalculate storage quotas for all users'
        )
        
        parser.add_argument(
            '--process-metadata',
            action='store_true',
            help='Process metadata for files missing it'
        )
        
        parser.add_argument(
            '--user',
            type=str,
            help='Process only specific user (username)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        specific_user = options.get('user')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made")
            )
        
        # Get users to process
        if specific_user:
            try:
                users = [User.objects.get(username=specific_user)]
                self.stdout.write(f"Processing user: {specific_user}")
            except User.DoesNotExist:
                raise CommandError(f"User '{specific_user}' does not exist")
        else:
            users = User.objects.filter(file_documents__isnull=False).distinct()
            self.stdout.write(f"Processing {users.count()} users")
        
        # Execute cleanup tasks
        if options.get('cleanup_revisions'):
            self._cleanup_revisions(users, options.get('keep_revisions', 5), dry_run)
        
        if options.get('cleanup_orphaned'):
            self._cleanup_orphaned_files(dry_run)
        
        if options.get('update_quotas'):
            self._update_quotas(users, dry_run)
        
        if options.get('process_metadata'):
            self._process_metadata(users, dry_run)
        
        if not any([
            options.get('cleanup_revisions'),
            options.get('cleanup_orphaned'),
            options.get('update_quotas'),
            options.get('process_metadata')
        ]):
            self.stdout.write(
                self.style.WARNING(
                    "No cleanup tasks specified. Use --help to see available options."
                )
            )

    def _cleanup_revisions(self, users, keep_count, dry_run):
        """Clean up old revisions"""
        self.stdout.write(f"Cleaning up revisions (keeping {keep_count} per document)...")
        
        total_cleaned = 0
        
        for user in users:
            if dry_run:
                # Count what would be cleaned
                documents = FileDocument.objects.filter(owner=user)
                user_cleaned = 0
                for doc in documents:
                    revision_count = doc.revisions.count()
                    if revision_count > keep_count:
                        user_cleaned += revision_count - keep_count
                
                self.stdout.write(f"  {user.username}: would clean {user_cleaned} revisions")
                total_cleaned += user_cleaned
            else:
                # Actually clean up
                user_cleaned = cleanup_old_revisions(user, keep_count)
                if user_cleaned > 0:
                    self.stdout.write(f"  {user.username}: cleaned {user_cleaned} revisions")
                total_cleaned += user_cleaned
        
        action = "Would clean" if dry_run else "Cleaned"
        self.stdout.write(
            self.style.SUCCESS(f"{action} {total_cleaned} old revisions")
        )

    def _cleanup_orphaned_files(self, dry_run):
        """Clean up orphaned files"""
        self.stdout.write("Cleaning up orphaned files...")
        
        from django.conf import settings
        import os
        
        media_root = settings.MEDIA_ROOT
        uploads_dir = os.path.join(media_root, 'uploads')
        
        if not os.path.exists(uploads_dir):
            self.stdout.write("No uploads directory found")
            return
        
        orphaned_files = []
        total_size = 0
        
        # Walk through all files in uploads directory
        for root, dirs, files in os.walk(uploads_dir):
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, media_root)
                
                # Check if file is referenced in database
                if not FileRevision.objects.filter(file_data=relative_path).exists():
                    file_size = os.path.getsize(file_path)
                    orphaned_files.append((file_path, file_size))
                    total_size += file_size
        
        if orphaned_files:
            self.stdout.write(f"Found {len(orphaned_files)} orphaned files ({total_size} bytes)")
            
            if not dry_run:
                for file_path, file_size in orphaned_files:
                    try:
                        os.remove(file_path)
                        self.stdout.write(f"  Deleted: {file_path}")
                    except OSError as e:
                        self.stdout.write(
                            self.style.ERROR(f"  Error deleting {file_path}: {e}")
                        )
                
                self.stdout.write(
                    self.style.SUCCESS(f"Cleaned up {len(orphaned_files)} orphaned files")
                )
            else:
                self.stdout.write(f"Would delete {len(orphaned_files)} orphaned files")
        else:
            self.stdout.write("No orphaned files found")

    def _update_quotas(self, users, dry_run):
        """Update storage quotas"""
        self.stdout.write("Updating storage quotas...")
        
        for user in users:
            if hasattr(user, 'profile'):
                old_usage = user.profile.storage_used
                
                if not dry_run:
                    new_usage = StorageQuotaManager.update_user_quota(user)
                    if old_usage != new_usage:
                        self.stdout.write(
                            f"  {user.username}: {old_usage} -> {new_usage} bytes"
                        )
                else:
                    # Calculate what new usage would be
                    total_usage = sum(
                        revision.file_size 
                        for doc in user.file_documents.all() 
                        for revision in doc.revisions.all()
                    )
                    if old_usage != total_usage:
                        self.stdout.write(
                            f"  {user.username}: would update {old_usage} -> {total_usage} bytes"
                        )
        
        action = "Would update" if dry_run else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} storage quotas"))

    def _process_metadata(self, users, dry_run):
        """Process missing metadata"""
        self.stdout.write("Processing missing metadata...")
        
        # Find revisions without metadata
        revisions_without_metadata = FileRevision.objects.filter(
            metadata__isnull=True,
            document__owner__in=users
        )
        
        count = revisions_without_metadata.count()
        
        if count == 0:
            self.stdout.write("No revisions missing metadata")
            return
        
        self.stdout.write(f"Found {count} revisions missing metadata")
        
        if not dry_run:
            processed = 0
            for revision in revisions_without_metadata:
                try:
                    # This will auto-create metadata via signal
                    FileMetadata.objects.create(revision=revision)
                    processed += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Error processing metadata for revision {revision.id}: {e}"
                        )
                    )
            
            self.stdout.write(
                self.style.SUCCESS(f"Processed metadata for {processed} revisions")
            )
        else:
            self.stdout.write(f"Would process metadata for {count} revisions")