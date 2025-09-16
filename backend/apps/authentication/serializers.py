from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import UserProfile


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom token serializer to include user information in login response
    """
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims
        token['username'] = user.username
        token['email'] = user.email
        
        return token
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add user information to response
        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
        }
        
        return data


class RegisterSerializer(serializers.ModelSerializer):
    """
    User registration serializer
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    email = serializers.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ('username', 'password', 'password_confirm', 'email', 
                 'first_name', 'last_name')
    
    def validate(self, attrs):
        """
        Validate that passwords match and email is unique
        """
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."}
            )
        
        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError(
                {"email": "A user with this email already exists."}
            )
        
        return attrs
    
    def create(self, validated_data):
        """
        Create user with encrypted password
        """
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """
    User profile serializer for getting/updating user information
    """
    # Include profile information
    storage_used = serializers.ReadOnlyField(source='profile.storage_used')
    storage_limit = serializers.ReadOnlyField(source='profile.storage_limit')
    storage_usage_percentage = serializers.ReadOnlyField(source='profile.storage_usage_percentage')
    formatted_storage_used = serializers.ReadOnlyField(source='profile.formatted_storage_used')
    formatted_storage_limit = serializers.ReadOnlyField(source='profile.formatted_storage_limit')
    
    # User statistics
    total_files = serializers.SerializerMethodField()
    total_revisions = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name',
                 'date_joined', 'last_login', 'storage_used', 'storage_limit',
                 'storage_usage_percentage', 'formatted_storage_used',
                 'formatted_storage_limit', 'total_files', 'total_revisions')
        read_only_fields = ('id', 'username', 'date_joined', 'last_login')
    
    def get_total_files(self, obj):
        """Get total number of files for user"""
        return obj.file_documents.count()
    
    def get_total_revisions(self, obj):
        """Get total number of file revisions for user"""
        return sum(doc.get_revision_count() for doc in obj.file_documents.all())
    
    def validate_email(self, value):
        """
        Validate that email is unique (excluding current user)
        """
        if User.objects.filter(email=value).exclude(id=self.instance.id).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value


class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for password change endpoint
    """
    old_password = serializers.CharField(required=True, style={'input_type': 'password'})
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    
    def validate_old_password(self, value):
        """
        Validate that the old password is correct
        """
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Invalid old password.")
        return value