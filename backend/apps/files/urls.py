"""
Files URLs
"""
from django.urls import path, re_path
from . import views
from .api_extensions import (
    FileAnalyticsView, file_metadata_view, cleanup_user_files,
    file_duplicates_view, storage_breakdown_view, verify_file_integrity
)

urlpatterns = [
    # File listing and upload
    path('', views.FileListCreateView.as_view(), name='file-list-create'),
    
    # File statistics and analytics
    path('stats/', views.file_stats_view, name='file-stats'),
    path('analytics/', FileAnalyticsView.as_view(), name='file-analytics'),
    path('storage-breakdown/', storage_breakdown_view, name='storage-breakdown'),
    
    # File management
    path('cleanup/', cleanup_user_files, name='cleanup-files'),
    path('duplicates/', file_duplicates_view, name='file-duplicates'),
    path('<int:file_id>/metadata/', file_metadata_view, name='file-metadata'),
    path('<int:file_id>/verify/', verify_file_integrity, name='verify-integrity'),
    
    # Bulk operations
    path('bulk-delete/', views.bulk_delete_view, name='bulk-delete'),
    
    # File-specific operations with URL path
    # Note: These need to be at the end to avoid conflicts
    re_path(r'^(?P<url>.+)/revisions/$', views.FileRevisionListView.as_view(), name='file-revisions'),
    re_path(r'^(?P<url>.+)/$', views.FileDetailView.as_view(), name='file-detail'),
]