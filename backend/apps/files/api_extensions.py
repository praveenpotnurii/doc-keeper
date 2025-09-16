"""
Extended API views for enhanced file management
"""
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta

from .models import FileDocument, FileRevision
from .models_extensions import (
    FileMetadata, FileAccessLog, get_file_statistics, cleanup_old_revisions
)
from .storage import StorageQuotaManager, FileHashManager


class FileAnalyticsView(APIView):
    """
    Advanced file analytics and statistics
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get comprehensive file analytics"""
        user = request.user
        days = int(request.query_params.get('days', 30))
        
        stats = get_file_statistics(user, days)
        
        # Additional analytics
        recent_activity = FileAccessLog.objects.filter(
            user=user,
            accessed_at__gte=timezone.now() - timedelta(days=days)
        ).values('access_type').annotate(count=Count('id'))
        
        # Most accessed files
        popular_files = FileDocument.objects.filter(
            owner=user,
            access_logs__accessed_at__gte=timezone.now() - timedelta(days=days)
        ).annotate(
            access_count=Count('access_logs')
        ).order_by('-access_count')[:10]
        
        return Response({
            'statistics': stats,
            'activity': {item['access_type']: item['count'] for item in recent_activity},
            'popular_files': [
                {
                    'id': f.id,
                    'name': f.name,
                    'url': f.url,
                    'access_count': f.access_count
                }
                for f in popular_files
            ]
        })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def file_metadata_view(request, file_id):
    """Get detailed metadata for a file"""
    user = request.user
    
    try:
        document = FileDocument.objects.get(id=file_id, owner=user)
    except FileDocument.DoesNotExist:
        return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get all revisions with metadata
    revisions_data = []
    for revision in document.revisions.all():
        revision_data = {
            'id': revision.id,
            'revision_number': revision.revision_number,
            'uploaded_at': revision.uploaded_at,
            'file_size': revision.file_size,
            'formatted_size': revision.formatted_file_size,
            'content_type': revision.content_type,
            'extension': revision.file_extension,
        }
        
        # Add metadata if available
        try:
            metadata = revision.metadata
            revision_data.update({
                'sha256_hash': metadata.sha256_hash,
                'file_category': metadata.file_category,
                'extra_metadata': metadata.extra_metadata,
                'is_processed': metadata.is_processed,
            })
        except FileMetadata.DoesNotExist:
            revision_data['metadata_available'] = False
        
        revisions_data.append(revision_data)
    
    return Response({
        'document': {
            'id': document.id,
            'name': document.name,
            'url': document.url,
            'created_at': document.created_at,
            'updated_at': document.updated_at,
        },
        'revisions': revisions_data
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def cleanup_user_files(request):
    """Clean up user's old file revisions"""
    user = request.user
    keep_count = int(request.data.get('keep_revisions', 5))
    
    if keep_count < 1:
        return Response(
            {'error': 'keep_revisions must be at least 1'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        cleaned_count = cleanup_old_revisions(user, keep_count)
        
        # Get updated storage info
        quota_status = StorageQuotaManager.get_quota_status(user)
        
        return Response({
            'message': f'Cleaned up {cleaned_count} old revisions',
            'cleaned_count': cleaned_count,
            'storage': quota_status
        })
        
    except Exception as e:
        return Response(
            {'error': f'Cleanup failed: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def file_duplicates_view(request):
    """Find duplicate files based on content hash"""
    user = request.user
    
    # Find files with same hash
    duplicates = []
    
    # Get all metadata with hashes
    metadata_with_hashes = FileMetadata.objects.filter(
        revision__document__owner=user,
        sha256_hash__isnull=False,
        sha256_hash__ne=''
    ).exclude(sha256_hash='')
    
    # Group by hash
    hash_groups = {}
    for metadata in metadata_with_hashes:
        hash_val = metadata.sha256_hash
        if hash_val not in hash_groups:
            hash_groups[hash_val] = []
        hash_groups[hash_val].append(metadata)
    
    # Find groups with multiple files
    for hash_val, metadata_list in hash_groups.items():
        if len(metadata_list) > 1:
            files = []
            for metadata in metadata_list:
                revision = metadata.revision
                files.append({
                    'document_id': revision.document.id,
                    'document_name': revision.document.name,
                    'document_url': revision.document.url,
                    'revision_id': revision.id,
                    'revision_number': revision.revision_number,
                    'file_size': revision.file_size,
                    'uploaded_at': revision.uploaded_at,
                })
            
            duplicates.append({
                'hash': hash_val,
                'file_count': len(files),
                'total_size': sum(f['file_size'] for f in files),
                'files': files
            })
    
    # Sort by potential space savings
    duplicates.sort(key=lambda x: x['total_size'], reverse=True)
    
    return Response({
        'duplicate_groups': len(duplicates),
        'duplicates': duplicates,
        'potential_savings': sum(
            (group['file_count'] - 1) * (group['total_size'] // group['file_count'])
            for group in duplicates
        )
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def storage_breakdown_view(request):
    """Get detailed storage breakdown by category"""
    user = request.user
    
    # Storage by file category
    category_breakdown = FileMetadata.objects.filter(
        revision__document__owner=user
    ).values('file_category').annotate(
        file_count=Count('id'),
        total_size=Sum('revision__file_size')
    )
    
    # Storage by date (last 12 months)
    monthly_data = []
    for i in range(12):
        month_start = timezone.now() - timedelta(days=30 * (i + 1))
        month_end = timezone.now() - timedelta(days=30 * i)
        
        month_stats = FileRevision.objects.filter(
            document__owner=user,
            uploaded_at__gte=month_start,
            uploaded_at__lt=month_end
        ).aggregate(
            count=Count('id'),
            size=Sum('file_size')
        )
        
        monthly_data.append({
            'month': month_start.strftime('%Y-%m'),
            'uploads': month_stats['count'] or 0,
            'size': month_stats['size'] or 0
        })
    
    # Get quota status
    quota_status = StorageQuotaManager.get_quota_status(user)
    
    return Response({
        'quota': quota_status,
        'by_category': [
            {
                'category': item['file_category'],
                'file_count': item['file_count'],
                'total_size': item['total_size'] or 0,
                'formatted_size': format_file_size(item['total_size'] or 0)
            }
            for item in category_breakdown
        ],
        'monthly_uploads': list(reversed(monthly_data))
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def verify_file_integrity(request, file_id):
    """Verify file integrity using stored hash"""
    user = request.user
    
    try:
        document = FileDocument.objects.get(id=file_id, owner=user)
    except FileDocument.DoesNotExist:
        return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
    
    revision_id = request.data.get('revision_id')
    if revision_id:
        try:
            revision = document.revisions.get(id=revision_id)
        except FileRevision.DoesNotExist:
            return Response(
                {'error': 'Revision not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    else:
        revision = document.get_latest_revision()
        if not revision:
            return Response(
                {'error': 'No revisions found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    # Check if we have metadata with hash
    try:
        metadata = revision.metadata
        if not metadata.sha256_hash:
            return Response({
                'error': 'No hash available for verification'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify integrity
        file_path = revision.file_data.path
        is_valid = FileHashManager.verify_integrity(
            file_path, 
            metadata.sha256_hash, 
            'sha256'
        )
        
        return Response({
            'revision_id': revision.id,
            'revision_number': revision.revision_number,
            'integrity_valid': is_valid,
            'hash_algorithm': 'sha256',
            'stored_hash': metadata.sha256_hash
        })
        
    except FileMetadata.DoesNotExist:
        return Response({
            'error': 'No metadata available for verification'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Verification failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def format_file_size(size_bytes):
    """Format file size in human-readable format"""
    if size_bytes == 0:
        return "0 bytes"
    
    size_names = ["bytes", "KB", "MB", "GB", "TB"]
    size = float(size_bytes)
    i = 0
    
    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    return f"{size:.1f} {size_names[i]}"


# Log file access for analytics
def log_file_access(request, document, revision=None, access_type='view'):
    """Log file access for analytics"""
    try:
        # Get IP and User-Agent
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0]
        if not ip_address:
            ip_address = request.META.get('REMOTE_ADDR')
        
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]  # Limit length
        
        FileAccessLog.objects.create(
            document=document,
            revision=revision,
            user=request.user,
            access_type=access_type,
            ip_address=ip_address,
            user_agent=user_agent
        )
    except Exception:
        # Don't fail the request if logging fails
        pass