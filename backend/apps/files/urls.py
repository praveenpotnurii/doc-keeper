"""
Files URLs
"""
from django.urls import path, re_path
from . import views

urlpatterns = [
    # File listing and upload
    path('', views.FileListCreateView.as_view(), name='file-list-create'),
    
    # File statistics
    path('stats/', views.file_stats_view, name='file-stats'),
    
    # Bulk operations
    path('bulk-delete/', views.bulk_delete_view, name='bulk-delete'),
    
    # File-specific operations with URL path
    # Note: These need to be at the end to avoid conflicts
    re_path(r'^(?P<url>.+)/revisions/$', views.FileRevisionListView.as_view(), name='file-revisions'),
    re_path(r'^(?P<url>.+)/$', views.FileDetailView.as_view(), name='file-detail'),
]