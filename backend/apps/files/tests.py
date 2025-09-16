from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
import tempfile
import os
from .models import FileDocument, FileRevision
from .serializers import (
    FileDocumentSerializer, FileRevisionSerializer, 
    FileUploadSerializer, FileDocumentDetailSerializer
)


class FileDocumentModelTest(TestCase):
    """Test cases for FileDocument model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.document = FileDocument.objects.create(
            url='/documents/test.txt',
            name='test.txt',
            owner=self.user
        )
    
    def test_file_document_creation(self):
        """Test FileDocument creation"""
        self.assertEqual(self.document.url, '/documents/test.txt')
        self.assertEqual(self.document.name, 'test.txt')
        self.assertEqual(self.document.owner, self.user)
    
    def test_file_document_str_representation(self):
        """Test string representation of FileDocument"""
        expected = f"test.txt (/documents/test.txt) - testuser"
        self.assertEqual(str(self.document), expected)
    
    def test_unique_together_constraint(self):
        """Test that owner and URL combination must be unique"""
        with self.assertRaises(Exception):
            FileDocument.objects.create(
                url='/documents/test.txt',
                name='duplicate.txt',
                owner=self.user
            )
    
    def test_get_latest_revision_no_revisions(self):
        """Test get_latest_revision when no revisions exist"""
        self.assertIsNone(self.document.get_latest_revision())
    
    def test_get_revision_count_no_revisions(self):
        """Test get_revision_count when no revisions exist"""
        self.assertEqual(self.document.get_revision_count(), 0)


class FileRevisionModelTest(TestCase):
    """Test cases for FileRevision model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.document = FileDocument.objects.create(
            url='/documents/test.txt',
            name='test.txt',
            owner=self.user
        )
        
        # Create a test file
        self.test_file = SimpleUploadedFile(
            "test.txt",
            b"This is test content",
            content_type="text/plain"
        )
    
    def test_file_revision_creation(self):
        """Test FileRevision creation"""
        revision = FileRevision.objects.create(
            document=self.document,
            file_data=self.test_file,
            file_size=20,
            content_type='text/plain'
        )
        
        self.assertEqual(revision.document, self.document)
        self.assertEqual(revision.file_size, 20)
        self.assertEqual(revision.content_type, 'text/plain')
        self.assertEqual(revision.revision_number, 0)  # Auto-incremented
    
    def test_auto_increment_revision_number(self):
        """Test that revision numbers auto-increment"""
        rev1 = FileRevision.objects.create(
            document=self.document,
            file_data=self.test_file,
            file_size=20
        )
        
        rev2 = FileRevision.objects.create(
            document=self.document,
            file_data=SimpleUploadedFile("test2.txt", b"content2"),
            file_size=8
        )
        
        self.assertEqual(rev1.revision_number, 0)
        self.assertEqual(rev2.revision_number, 1)
    
    def test_auto_set_file_size(self):
        """Test that file size is auto-set if not provided"""
        revision = FileRevision.objects.create(
            document=self.document,
            file_data=self.test_file
        )
        
        self.assertEqual(revision.file_size, self.test_file.size)
    
    def test_file_extension_property(self):
        """Test file_extension property"""
        revision = FileRevision.objects.create(
            document=self.document,
            file_data=SimpleUploadedFile("test.pdf", b"content"),
            file_size=7
        )
        
        # Note: The extension comes from the stored file path
        self.assertTrue(revision.file_extension.endswith('.pdf'))
    
    def test_formatted_file_size_property(self):
        """Test formatted_file_size property"""
        test_cases = [
            (500, "500.0 bytes"),
            (1536, "1.5 KB"),
            (1572864, "1.5 MB"),
            (1610612736, "1.5 GB"),
        ]
        
        for i, (size, expected) in enumerate(test_cases):
            # Create a unique document for each test case to avoid conflicts
            document = FileDocument.objects.create(
                url=f'/documents/test{i}.txt',
                name=f'test{i}.txt',
                owner=self.user
            )
            # Create content of the appropriate size
            content = b"x" * size
            revision = FileRevision.objects.create(
                document=document,
                file_data=SimpleUploadedFile(f"test{size}.txt", content)
            )
            self.assertEqual(revision.formatted_file_size, expected)
        
        # Test zero bytes separately without file_data to avoid auto-sizing
        document = FileDocument.objects.create(
            url='/documents/test_zero.txt',
            name='test_zero.txt',
            owner=self.user
        )
        revision = FileRevision(
            document=document,
            file_data=SimpleUploadedFile("empty.txt", b""),
            file_size=0
        )
        # Set file_size after file_data to override auto-sizing
        revision.save()
        revision.file_size = 0
        revision.save()
        self.assertEqual(revision.formatted_file_size, "0 bytes")
    
    def test_unique_together_constraint(self):
        """Test that document and revision_number combination must be unique"""
        FileRevision.objects.create(
            document=self.document,
            file_data=self.test_file,
            revision_number=5,
            file_size=20
        )
        
        with self.assertRaises(Exception):
            FileRevision.objects.create(
                document=self.document,
                file_data=SimpleUploadedFile("test2.txt", b"content2"),
                revision_number=5,
                file_size=8
            )


class FileUploadSerializerTest(TestCase):
    """Test cases for FileUploadSerializer"""
    
    def setUp(self):
        self.test_file = SimpleUploadedFile(
            "test.txt",
            b"This is test content",
            content_type="text/plain"
        )
    
    def test_valid_upload_data_with_url(self):
        """Test serializer with valid upload data including URL"""
        data = {
            'url': '/documents/test.txt',
            'name': 'Test Document',
            'file': self.test_file
        }
        serializer = FileUploadSerializer(data=data)
        self.assertTrue(serializer.is_valid())
    
    def test_valid_upload_data_without_url(self):
        """Test serializer with valid upload data without URL"""
        data = {
            'name': 'Test Document',
            'file': self.test_file
        }
        serializer = FileUploadSerializer(data=data)
        self.assertTrue(serializer.is_valid())
    
    def test_auto_set_name_from_filename(self):
        """Test that name is auto-set from filename if not provided"""
        data = {
            'file': self.test_file
        }
        serializer = FileUploadSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['name'], 'test.txt')
    
    def test_invalid_url_format(self):
        """Test validation of invalid URL formats"""
        invalid_urls = [
            'documents/test.txt',  # No leading slash
            '/documents/test.txt/',  # Trailing slash
        ]
        
        for invalid_url in invalid_urls:
            data = {
                'url': invalid_url,
                'file': self.test_file
            }
            serializer = FileUploadSerializer(data=data)
            self.assertFalse(serializer.is_valid())
            self.assertIn('url', serializer.errors)
    
    def test_file_size_validation(self):
        """Test file size validation"""
        # Create a file that's too large (> 10MB)
        large_file = SimpleUploadedFile(
            "large.txt",
            b"x" * (11 * 1024 * 1024),  # 11MB
            content_type="text/plain"
        )
        
        data = {
            'file': large_file
        }
        serializer = FileUploadSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('file', serializer.errors)
    
    def test_empty_file_validation(self):
        """Test empty file validation"""
        empty_file = SimpleUploadedFile("empty.txt", b"")
        
        data = {
            'file': empty_file
        }
        serializer = FileUploadSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('file', serializer.errors)


class FileAPITest(APITestCase):
    """Test cases for file management API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        
        # Get JWT token for authentication
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        
        self.files_url = '/api/files/'
        
        # Create test file
        self.test_file = SimpleUploadedFile(
            "test.txt",
            b"This is test content",
            content_type="text/plain"
        )
    
    def authenticate(self, user=None):
        """Helper method to authenticate a user"""
        if user is None:
            user = self.user
        refresh = RefreshToken.for_user(user)
        token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    
    def test_file_upload_authenticated(self):
        """Test file upload with authentication"""
        self.authenticate()
        
        data = {
            'url': '/documents/test.txt',
            'name': 'Test Document',
            'file': self.test_file
        }
        
        response = self.client.post(self.files_url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Test Document')
        self.assertEqual(response.data['url'], '/documents/test.txt')
        
        # Verify document was created
        self.assertTrue(FileDocument.objects.filter(
            owner=self.user,
            url='/documents/test.txt'
        ).exists())
    
    def test_file_upload_unauthenticated(self):
        """Test file upload without authentication"""
        data = {
            'url': '/documents/test.txt',
            'file': self.test_file
        }
        
        response = self.client.post(self.files_url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_file_list_authenticated(self):
        """Test file listing with authentication"""
        self.authenticate()
        
        # Create a test document
        document = FileDocument.objects.create(
            url='/documents/test.txt',
            name='test.txt',
            owner=self.user
        )
        
        response = self.client.get(self.files_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], document.id)
    
    def test_file_list_user_isolation(self):
        """Test that users only see their own files"""
        self.authenticate()
        
        # Create document for current user
        user_doc = FileDocument.objects.create(
            url='/documents/user_file.txt',
            name='user_file.txt',
            owner=self.user
        )
        
        # Create document for other user
        other_doc = FileDocument.objects.create(
            url='/documents/other_file.txt',
            name='other_file.txt',
            owner=self.other_user
        )
        
        response = self.client.get(self.files_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], user_doc.id)
    
    def test_file_detail_get(self):
        """Test getting file details using URL-encoded path"""
        self.authenticate()
        
        document = FileDocument.objects.create(
            url='/documents/test.txt',
            name='test.txt',
            owner=self.user
        )
        
        # URL encode the path for the API
        import urllib.parse
        encoded_url = urllib.parse.quote('/documents/test.txt', safe='')
        url = f'/api/files/{encoded_url}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], document.id)
    
    def test_file_detail_access_other_user_file(self):
        """Test that users cannot access other users' files"""
        self.authenticate()
        
        # Create document for other user
        FileDocument.objects.create(
            url='/documents/other.txt',
            name='other.txt',
            owner=self.other_user
        )
        
        import urllib.parse
        encoded_url = urllib.parse.quote('/documents/other.txt', safe='')
        url = f'/api/files/{encoded_url}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_file_upload_new_version(self):
        """Test uploading a new version of existing file"""
        self.authenticate()
        
        # Create initial document
        document = FileDocument.objects.create(
            url='/documents/test.txt',
            name='test.txt',
            owner=self.user
        )
        
        # Upload new version
        new_file = SimpleUploadedFile(
            "test_v2.txt",
            b"This is updated content",
            content_type="text/plain"
        )
        
        import urllib.parse
        encoded_url = urllib.parse.quote('/documents/test.txt', safe='')
        url = f'/api/files/{encoded_url}/'
        data = {'file': new_file}
        
        response = self.client.put(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify revision was created
        document.refresh_from_db()
        self.assertEqual(document.get_revision_count(), 1)
    
    def test_file_delete(self):
        """Test file deletion"""
        self.authenticate()
        
        document = FileDocument.objects.create(
            url='/documents/test.txt',
            name='test.txt',
            owner=self.user
        )
        
        import urllib.parse
        encoded_url = urllib.parse.quote('/documents/test.txt', safe='')
        url = f'/api/files/{encoded_url}/'
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify document was deleted
        self.assertFalse(FileDocument.objects.filter(id=document.id).exists())
    
    def test_file_revisions_list(self):
        """Test listing file revisions"""
        self.authenticate()
        
        document = FileDocument.objects.create(
            url='/documents/test.txt',
            name='test.txt',
            owner=self.user
        )
        
        # Create revisions
        rev1 = FileRevision.objects.create(
            document=document,
            file_data=self.test_file,
            file_size=20
        )
        
        rev2 = FileRevision.objects.create(
            document=document,
            file_data=SimpleUploadedFile("test2.txt", b"content2"),
            file_size=8
        )
        
        import urllib.parse
        encoded_url = urllib.parse.quote('/documents/test.txt', safe='')
        url = f'/api/files/{encoded_url}/revisions/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['revisions']), 2)
    
    def test_file_download_latest(self):
        """Test downloading latest file version"""
        self.authenticate()
        
        document = FileDocument.objects.create(
            url='/documents/test.txt',
            name='test.txt',
            owner=self.user
        )
        
        FileRevision.objects.create(
            document=document,
            file_data=self.test_file,
            file_size=20,
            content_type='text/plain'
        )
        
        import urllib.parse
        encoded_url = urllib.parse.quote('/documents/test.txt', safe='')
        url = f'/api/files/{encoded_url}/'
        response = self.client.get(url, {'download': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/plain')
    
    def test_file_download_specific_revision(self):
        """Test downloading specific file revision"""
        self.authenticate()
        
        document = FileDocument.objects.create(
            url='/documents/test.txt',
            name='test.txt',
            owner=self.user
        )
        
        # Create multiple revisions
        rev1 = FileRevision.objects.create(
            document=document,
            file_data=SimpleUploadedFile("test1.txt", b"version 1"),
            file_size=9,
            content_type='text/plain'
        )
        
        FileRevision.objects.create(
            document=document,
            file_data=SimpleUploadedFile("test2.txt", b"version 2"),
            file_size=9,
            content_type='text/plain'
        )
        
        # Download specific revision
        import urllib.parse
        encoded_url = urllib.parse.quote('/documents/test.txt', safe='')
        url = f'/api/files/{encoded_url}/'
        response = self.client.get(url, {
            'download': 'true',
            'revision': rev1.revision_number
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, b"version 1")
    
    def test_bulk_delete(self):
        """Test bulk delete operation"""
        self.authenticate()
        
        # Create multiple documents
        doc1 = FileDocument.objects.create(
            url='/documents/test1.txt',
            name='test1.txt',
            owner=self.user
        )
        
        doc2 = FileDocument.objects.create(
            url='/documents/test2.txt',
            name='test2.txt',
            owner=self.user
        )
        
        url = '/api/files/bulk-delete/'
        data = {
            'urls': ['/documents/test1.txt', '/documents/test2.txt']
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['deleted_count'], 2)
        
        # Verify documents were deleted
        self.assertFalse(FileDocument.objects.filter(id=doc1.id).exists())
        self.assertFalse(FileDocument.objects.filter(id=doc2.id).exists())
    
    def test_file_stats(self):
        """Test file statistics endpoint"""
        self.authenticate()
        
        # Create document with revision
        document = FileDocument.objects.create(
            url='/documents/test.txt',
            name='test.txt',
            owner=self.user
        )
        
        FileRevision.objects.create(
            document=document,
            file_data=self.test_file,
            file_size=20
        )
        
        url = '/api/files/stats/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        expected_fields = [
            'total_documents', 'total_revisions', 'file_types',
            'storage_used', 'storage_limit'
        ]
        
        for field in expected_fields:
            self.assertIn(field, response.data)
        
        self.assertEqual(response.data['total_documents'], 1)
        self.assertEqual(response.data['total_revisions'], 1)


class FileSerializersTest(TestCase):
    """Test cases for file serializers"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.document = FileDocument.objects.create(
            url='/documents/test.txt',
            name='test.txt',
            owner=self.user
        )
    
    def test_file_document_serializer_url_validation(self):
        """Test FileDocumentSerializer URL validation"""
        invalid_urls = [
            'documents/test.txt',  # No leading slash
            '/documents/test.txt/',  # Trailing slash
            '/documents/../test.txt',  # Path traversal
            '/documents/test<>.txt',  # Invalid characters
        ]
        
        for invalid_url in invalid_urls:
            data = {
                'url': invalid_url,
                'name': 'test.txt'
            }
            serializer = FileDocumentSerializer(
                data=data,
                context={'request': type('MockRequest', (), {'user': self.user})()}
            )
            self.assertFalse(serializer.is_valid())
            self.assertIn('url', serializer.errors)
    
    def test_file_revision_serializer_file_validation(self):
        """Test FileRevisionSerializer file validation"""
        # Test empty file
        empty_file = SimpleUploadedFile("empty.txt", b"")
        data = {'file_data': empty_file}
        
        serializer = FileRevisionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('file_data', serializer.errors)
    
    def test_file_document_detail_serializer_includes_revisions(self):
        """Test that FileDocumentDetailSerializer includes revisions"""
        # Create revision
        FileRevision.objects.create(
            document=self.document,
            file_data=SimpleUploadedFile("test.txt", b"content"),
            file_size=7
        )
        
        serializer = FileDocumentDetailSerializer(
            self.document,
            context={'request': type('MockRequest', (), {'user': self.user})()}
        )
        
        data = serializer.data
        self.assertIn('revisions', data)
        self.assertEqual(len(data['revisions']), 1)