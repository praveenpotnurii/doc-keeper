from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import UserProfile
from .serializers import RegisterSerializer, UserProfileSerializer, CustomTokenObtainPairSerializer


class UserProfileModelTest(TestCase):
    """Test cases for UserProfile model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = self.user.profile
    
    def test_user_profile_created_automatically(self):
        """Test that UserProfile is created automatically when User is created"""
        self.assertIsInstance(self.profile, UserProfile)
        self.assertEqual(self.profile.user, self.user)
    
    def test_storage_usage_percentage(self):
        """Test storage usage percentage calculation"""
        self.profile.storage_limit = 1000
        self.profile.storage_used = 250
        self.profile.save()
        
        self.assertEqual(self.profile.storage_usage_percentage, 25.0)
    
    def test_storage_usage_percentage_zero_limit(self):
        """Test storage usage percentage with zero limit"""
        self.profile.storage_limit = 0
        self.profile.storage_used = 100
        self.profile.save()
        
        self.assertEqual(self.profile.storage_usage_percentage, 0)
    
    def test_formatted_storage_used(self):
        """Test formatted storage used display"""
        test_cases = [
            (500, "500.0 bytes"),
            (1536, "1.5 KB"),
            (1572864, "1.5 MB"),
            (1610612736, "1.5 GB"),
        ]
        
        for size, expected in test_cases:
            self.profile.storage_used = size
            self.profile.save()
            self.assertEqual(self.profile.formatted_storage_used, expected)
    
    def test_formatted_storage_limit(self):
        """Test formatted storage limit display"""
        self.profile.storage_limit = 1073741824  # 1GB
        self.profile.save()
        
        self.assertEqual(self.profile.formatted_storage_limit, "1.0 GB")
    
    def test_can_upload_file(self):
        """Test file upload permission based on storage"""
        self.profile.storage_limit = 1000
        self.profile.storage_used = 800
        self.profile.save()
        
        self.assertTrue(self.profile.can_upload_file(100))  # Under limit
        self.assertTrue(self.profile.can_upload_file(200))  # At limit
        self.assertFalse(self.profile.can_upload_file(300))  # Over limit
    
    def test_profile_str_representation(self):
        """Test string representation of UserProfile"""
        expected = f"{self.user.username}'s Profile"
        self.assertEqual(str(self.profile), expected)


class RegisterSerializerTest(TestCase):
    """Test cases for RegisterSerializer"""
    
    def test_valid_registration_data(self):
        """Test serializer with valid registration data"""
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'complexpassword123',
            'password_confirm': 'complexpassword123',
            'first_name': 'John',
            'last_name': 'Doe'
        }
        serializer = RegisterSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        
        user = serializer.save()
        self.assertEqual(user.username, 'newuser')
        self.assertEqual(user.email, 'new@example.com')
        self.assertTrue(user.check_password('complexpassword123'))
    
    def test_password_mismatch(self):
        """Test serializer validation with mismatched passwords"""
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'password123',
            'password_confirm': 'differentpassword',
        }
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)
    
    def test_duplicate_email(self):
        """Test serializer validation with duplicate email"""
        User.objects.create_user(
            username='existing',
            email='existing@example.com',
            password='password123'
        )
        
        data = {
            'username': 'newuser',
            'email': 'existing@example.com',
            'password': 'ComplexPassword123!',
            'password_confirm': 'ComplexPassword123!',
        }
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)


class AuthenticationAPITest(APITestCase):
    """Test cases for authentication API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.login_url = '/api/auth/login/'
        self.register_url = '/api/auth/register/'
        self.logout_url = '/api/auth/logout/'
        self.profile_url = '/api/auth/profile/'
    
    def get_tokens(self, user):
        """Helper method to get JWT tokens for a user"""
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
    
    def test_user_registration(self):
        """Test user registration endpoint"""
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'complexpassword123',
            'password_confirm': 'complexpassword123',
            'first_name': 'New',
            'last_name': 'User'
        }
        
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('tokens', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], 'newuser')
        
        # Verify user was created
        self.assertTrue(User.objects.filter(username='newuser').exists())
    
    def test_user_login(self):
        """Test user login endpoint"""
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
    
    def test_user_login_invalid_credentials(self):
        """Test user login with invalid credentials"""
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_user_logout(self):
        """Test user logout endpoint"""
        tokens = self.get_tokens(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        
        data = {'refresh': tokens['refresh']}
        response = self.client.post(self.logout_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_user_profile_get(self):
        """Test get user profile endpoint"""
        tokens = self.get_tokens(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')
        self.assertEqual(response.data['email'], 'test@example.com')
        self.assertIn('storage_used', response.data)
        self.assertIn('storage_limit', response.data)
    
    def test_user_profile_update(self):
        """Test update user profile endpoint"""
        tokens = self.get_tokens(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        
        data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'updated@example.com'
        }
        
        response = self.client.patch(self.profile_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'Updated')
        self.assertEqual(response.data['last_name'], 'Name')
        self.assertEqual(response.data['email'], 'updated@example.com')
        
        # Verify user was updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')
    
    def test_profile_access_requires_authentication(self):
        """Test that profile access requires authentication"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_change_password(self):
        """Test password change endpoint"""
        tokens = self.get_tokens(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        
        change_password_url = '/api/auth/change-password/'
        data = {
            'old_password': 'testpass123',
            'new_password': 'newpassword456'
        }
        
        response = self.client.post(change_password_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpassword456'))
        self.assertFalse(self.user.check_password('testpass123'))
    
    def test_change_password_invalid_old_password(self):
        """Test password change with invalid old password"""
        tokens = self.get_tokens(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        
        change_password_url = '/api/auth/change-password/'
        data = {
            'old_password': 'wrongpassword',
            'new_password': 'newpassword456'
        }
        
        response = self.client.post(change_password_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_user_stats(self):
        """Test user statistics endpoint"""
        tokens = self.get_tokens(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        
        stats_url = '/api/auth/stats/'
        response = self.client.get(stats_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        expected_fields = [
            'total_files', 'total_revisions', 'storage_used', 'storage_limit',
            'storage_usage_percentage', 'formatted_storage_used',
            'formatted_storage_limit', 'account_created', 'last_login'
        ]
        
        for field in expected_fields:
            self.assertIn(field, response.data)


class CustomTokenObtainPairSerializerTest(TestCase):
    """Test cases for CustomTokenObtainPairSerializer"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
    
    def test_token_contains_custom_claims(self):
        """Test that JWT token contains custom claims"""
        token = CustomTokenObtainPairSerializer.get_token(self.user)
        self.assertEqual(token['username'], 'testuser')
        self.assertEqual(token['email'], 'test@example.com')
    
    def test_validate_includes_user_data(self):
        """Test that validation response includes user data"""
        from unittest.mock import patch
        
        serializer = CustomTokenObtainPairSerializer()
        serializer.user = self.user
        
        # Mock the parent validation
        parent_data = {
            'access': 'mock_access_token',
            'refresh': 'mock_refresh_token'
        }
        
        with patch.object(CustomTokenObtainPairSerializer.__bases__[0], 'validate', return_value=parent_data):
            result = serializer.validate({})
            self.assertIn('user', result)
            self.assertEqual(result['user']['username'], 'testuser')
            self.assertEqual(result['user']['email'], 'test@example.com')