from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, Http404
from django.core.exceptions import ValidationError
import os
import mimetypes

from .models import FileDocument, FileRevision
from .serializers import (
    FileDocumentSerializer, FileDocumentListSerializer, 
    FileDocumentDetailSerializer, FileRevisionSerializer,
    FileUploadSerializer
)
from .utils import create_file_document, update_user_storage_usage
from .validators import validate_file_upload
from .permissions import (
    FileAccessPermission, StorageQuotaPermission, FileTypePermission,
    BulkOperationPermission, log_file_access, UPLOAD_PERMISSIONS, OWNER_PERMISSIONS
)


class FileListCreateView(APIView):
    """
    List user's files or create a new file
    GET /api/files/ - List all files for authenticated user
    POST /api/files/ - Upload a new file
    """
    permission_classes = [permissions.IsAuthenticated, StorageQuotaPermission, FileTypePermission]
    parser_classes = [MultiPartParser, FormParser]
    
    def get(self, request):
        """List all files for the authenticated user"""
        user = request.user
        documents = FileDocument.objects.filter(owner=user)
        
        # Add search functionality
        search = request.query_params.get('search', None)
        if search:
            documents = documents.filter(
                name__icontains=search
            ) | documents.filter(
                url__icontains=search
            )
        
        # Add ordering
        ordering = request.query_params.get('ordering', '-updated_at')
        if ordering:
            documents = documents.order_by(ordering)
        
        serializer = FileDocumentListSerializer(documents, many=True, context={'request': request})
        return Response({
            'count': documents.count(),
            'results': serializer.data
        })
    
    def post(self, request):
        """Upload a new file or create new revision"""
        serializer = FileUploadSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        name = serializer.validated_data.get('name')
        file_obj = serializer.validated_data['file']
        url = serializer.validated_data.get('url')  # Optional now
        user = request.user
        
        try:
            # Validate file upload
            validate_file_upload(file_obj, user, url)
            
            # Create or update document (URL will be auto-generated if not provided)
            document, revision = create_file_document(user, name, file_obj, url)
            
            # Return the created document
            doc_serializer = FileDocumentDetailSerializer(document, context={'request': request})
            return Response(doc_serializer.data, status=status.HTTP_201_CREATED)
            
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': 'File upload failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FileDetailView(APIView):
    """
    Retrieve, update, or delete a specific file
    GET /api/files/{url}/ - Get file details or download
    PUT /api/files/{url}/ - Upload new revision
    DELETE /api/files/{url}/ - Delete file and all revisions
    """
    permission_classes = [permissions.IsAuthenticated, FileAccessPermission, StorageQuotaPermission, FileTypePermission]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_object(self, user, url):
        """Get file document for the user"""
        try:
            return FileDocument.objects.get(owner=user, url=url)
        except FileDocument.DoesNotExist:
            raise Http404("File not found")
    
    def get(self, request, url):
        """Get file details or download file"""
        user = request.user
        document = self.get_object(user, url)
        
        # Check if this is a download request
        download = request.query_params.get('download', 'false').lower() == 'true'
        
        # Log file access
        access_type = 'download' if download else 'view'
        log_file_access(user, document, access_type, request)
        revision_num = request.query_params.get('revision', None)
        
        if download:
            # Download specific revision or latest
            if revision_num is not None:
                try:
                    revision = document.revisions.get(revision_number=int(revision_num))
                except (FileRevision.DoesNotExist, ValueError):
                    return Response({'error': 'Revision not found'}, status=status.HTTP_404_NOT_FOUND)
            else:
                revision = document.get_latest_revision()
                
            if not revision or not revision.file_data:
                return Response({'error': 'File data not found'}, status=status.HTTP_404_NOT_FOUND)
            
            # Serve file
            try:
                # Get the original filename from the file path
                import os
                original_filename = os.path.basename(revision.file_data.name)
                
                # Extract the actual filename after the revision prefix (e.g., "1_Assignment2.zip" -> "Assignment2.zip")
                # The filename format is: revision_number_original_filename
                if '_' in original_filename:
                    # Split only on the first underscore to handle filenames with underscores
                    parts = original_filename.split('_', 1)
                    if len(parts) > 1 and parts[0].isdigit():
                        actual_filename = parts[1]
                    else:
                        actual_filename = original_filename
                else:
                    actual_filename = original_filename
                
                # Always determine content type based on the actual filename extension
                # Don't rely on stored content_type as it might be incorrect
                import mimetypes
                content_type, _ = mimetypes.guess_type(actual_filename)
                if not content_type:
                    # If mimetypes can't determine it, use the stored content_type as fallback
                    content_type = revision.content_type if revision.content_type else 'application/octet-stream'
                
                # Debug logging
                print(f"DEBUG: Downloading revision {revision.revision_number} for document {document.name}")
                print(f"DEBUG: File path: {revision.file_data.path}")
                print(f"DEBUG: Original filename: {original_filename}")
                print(f"DEBUG: Actual filename: {actual_filename}")
                print(f"DEBUG: File size: {revision.file_size}")
                print(f"DEBUG: Content type: {content_type}")
                
                # Reset file pointer to beginning
                revision.file_data.seek(0)
                
                response = HttpResponse(
                    revision.file_data.read(),
                    content_type=content_type
                )
                response['Content-Disposition'] = f'attachment; filename="{actual_filename}"'
                response['Content-Length'] = revision.file_size
                
                # Add cache-busting headers to prevent browser caching issues
                response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response['Pragma'] = 'no-cache'
                response['Expires'] = '0'
                
                return response
            except Exception as e:
                print(f"DEBUG: Error reading file: {str(e)}")
                return Response({'error': 'File could not be read'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Return file details
        serializer = FileDocumentDetailSerializer(document, context={'request': request})
        return Response(serializer.data)
    
    def put(self, request, url):
        """Upload new revision of existing file"""
        user = request.user
        document = self.get_object(user, url)
        
        # Check if file is provided
        if 'file' not in request.data:
            return Response({'error': 'File is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        file_obj = request.data['file']
        
        try:
            # Validate file upload
            validate_file_upload(file_obj, user)
            
            # Create new revision
            revision = FileRevision.objects.create(
                document=document,
                file_data=file_obj
            )
            
            # Update document name if provided
            name = request.data.get('name')
            if name and name != document.name:
                document.name = name
                document.save()
            
            # Update user storage
            update_user_storage_usage(user)
            
            # Return updated document
            serializer = FileDocumentDetailSerializer(document, context={'request': request})
            return Response(serializer.data)
            
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': 'File upload failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, url):
        """Delete file and all its revisions"""
        user = request.user
        document = self.get_object(user, url)
        
        # Delete all revision files
        for revision in document.revisions.all():
            if revision.file_data and revision.file_data.storage.exists(revision.file_data.name):
                revision.file_data.delete()
        
        # Delete document (cascades to revisions)
        document.delete()
        
        # Update user storage
        update_user_storage_usage(user)
        
        return Response({'message': 'File deleted successfully'}, status=status.HTTP_200_OK)


class FileRevisionListView(APIView):
    """
    List all revisions for a specific file
    GET /api/files/{url}/revisions/ - List all revisions
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, url):
        """List all revisions for a file"""
        user = request.user
        
        try:
            document = FileDocument.objects.get(owner=user, url=url)
        except FileDocument.DoesNotExist:
            raise Http404("File not found")
        
        revisions = document.revisions.all()
        serializer = FileRevisionSerializer(revisions, many=True, context={'request': request})
        
        return Response({
            'document': {
                'id': document.id,
                'name': document.name,
                'url': document.url,
            },
            'revisions': serializer.data
        })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def file_stats_view(request):
    """
    Get file statistics for the authenticated user
    """
    user = request.user
    
    # Calculate statistics
    documents = user.file_documents.all()
    total_documents = documents.count()
    total_revisions = sum(doc.get_revision_count() for doc in documents)
    
    # File type breakdown
    file_types = {}
    total_size = 0
    
    for document in documents:
        for revision in document.revisions.all():
            ext = revision.file_extension.lstrip('.') if revision.file_extension else 'unknown'
            file_types[ext] = file_types.get(ext, 0) + 1
            total_size += revision.file_size
    
    # Storage info from user profile
    storage_info = {}
    if hasattr(user, 'profile'):
        profile = user.profile
        storage_info = {
            'storage_used': profile.storage_used,
            'storage_limit': profile.storage_limit,
            'storage_usage_percentage': profile.storage_usage_percentage,
            'formatted_storage_used': profile.formatted_storage_used,
            'formatted_storage_limit': profile.formatted_storage_limit,
        }
    
    return Response({
        'total_documents': total_documents,
        'total_revisions': total_revisions,
        'file_types': file_types,
        **storage_info
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, BulkOperationPermission])
def bulk_delete_view(request):
    """
    Delete multiple files at once
    POST /api/files/bulk-delete/ with {"urls": ["/path1", "/path2"]}
    """
    urls = request.data.get('urls', [])
    
    if not urls or not isinstance(urls, list):
        return Response({'error': 'URLs list is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    user = request.user
    deleted_count = 0
    errors = []
    
    for url in urls:
        try:
            document = FileDocument.objects.get(owner=user, url=url)
            
            # Delete all revision files
            for revision in document.revisions.all():
                if revision.file_data and revision.file_data.storage.exists(revision.file_data.name):
                    revision.file_data.delete()
            
            document.delete()
            deleted_count += 1
            
        except FileDocument.DoesNotExist:
            errors.append(f"File not found: {url}")
        except Exception as e:
            errors.append(f"Error deleting {url}: {str(e)}")
    
    # Update user storage
    update_user_storage_usage(user)
    
    return Response({
        'deleted_count': deleted_count,
        'errors': errors
    })


# Path-based URL routing helper
def get_file_view(request, path=''):
    """
    Route requests to appropriate view based on path
    This handles the wildcard URL matching for file paths
    """
    # Ensure path starts with /
    if not path.startswith('/'):
        path = '/' + path
    
    if request.method == 'GET':
        view = FileDetailView()
        return view.get(request, path)
    elif request.method == 'PUT':
        view = FileDetailView()
        return view.put(request, path)
    elif request.method == 'DELETE':
        view = FileDetailView()
        return view.delete(request, path)
    else:
        return Response({'error': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
