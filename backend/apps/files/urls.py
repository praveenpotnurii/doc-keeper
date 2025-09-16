"""
Files URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# These will be expanded in Commit 6
urlpatterns = [
    # File management endpoints (to be added in Commit 6)
    # path('', views.FileListCreateView.as_view(), name='file-list-create'),
    # path('<path:url>/', views.FileRetrieveUpdateDeleteView.as_view(), name='file-detail'),
    # path('<path:url>/revisions/', views.FileRevisionListView.as_view(), name='file-revisions'),
]