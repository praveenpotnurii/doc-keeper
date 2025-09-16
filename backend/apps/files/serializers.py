from rest_framework import serializers
from django.contrib.auth.models import User
from django.core.files.uploadedfile import UploadedFile
import mimetypes
import os
from .models import FileDocument, FileRevision


class FileRevisionSerializer(serializers.ModelSerializer):
    """
    Serializer for FileRevision model
    """
    # Read-only computed fields
    file_extension = serializers.ReadOnlyField()
    formatted_file_size = serializers.ReadOnlyField()
    
    # File upload field with validation
    file_data = serializers.FileField(
        write_only=True,
        required=True,
        help_text="The file to upload"
    )
    
    # Display file URL for downloads
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = FileRevision
        fields = [
            'id', 'revision_number', 'uploaded_at', 'file_size',
            'content_type', 'file_extension', 'formatted_file_size',
            'file_data', 'file_url'
        ]
        read_only_fields = [
            'id', 'revision_number', 'uploaded_at', 'file_size',
            'content_type', 'file_extension', 'formatted_file_size'
        ]
    
    def get_file_url(self, obj):
        """Get file download URL"""
        if obj.file_data:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file_data.url)
        return None
    
    def validate_file_data(self, value):
        """
        Validate uploaded file
        """
        if not isinstance(value, UploadedFile):
            raise serializers.ValidationError("Invalid file upload")
        
        # File size validation (10MB max)
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size too large. Maximum size is {max_size // (1024*1024)}MB"
            )
        
        # File type validation (basic check)
        if value.size == 0:
            raise serializers.ValidationError("File is empty")
        
        return value
    
    def create(self, validated_data):
        """
        Create new file revision with automatic content type detection
        """
        file_data = validated_data['file_data']
        
        # Auto-detect content type
        content_type, _ = mimetypes.guess_type(file_data.name)
        if content_type:
            validated_data['content_type'] = content_type
        
        return super().create(validated_data)


class FileRevisionListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for listing revisions
    """
    file_extension = serializers.ReadOnlyField()
    formatted_file_size = serializers.ReadOnlyField()
    
    class Meta:
        model = FileRevision
        fields = [
            'id', 'revision_number', 'uploaded_at', 'file_size',
            'formatted_file_size', 'file_extension', 'content_type'
        ]


class FileDocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for FileDocument model with nested revisions
    """
    # Read-only owner information
    owner = serializers.StringRelatedField(read_only=True)
    owner_id = serializers.ReadOnlyField(source='owner.id')
    
    # Revision information
    latest_revision = FileRevisionListSerializer(
        source='get_latest_revision',
        read_only=True
    )
    revision_count = serializers.ReadOnlyField(source='get_revision_count')
    
    # All revisions (optional, for detailed view)
    revisions = FileRevisionListSerializer(many=True, read_only=True)
    
    class Meta:
        model = FileDocument
        fields = [
            'id', 'url', 'name', 'owner', 'owner_id', 
            'created_at', 'updated_at', 'latest_revision',
            'revision_count', 'revisions'
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']
    
    def validate_url(self, value):
        """
        Validate URL path format
        """
        if not value.startswith('/'):
            raise serializers.ValidationError("URL must start with '/'")
        
        if value.endswith('/'):
            raise serializers.ValidationError("URL cannot end with '/'")
        
        # Check for invalid characters
        invalid_chars = ['..', '//', '<', '>', '"', '|', '?', '*']
        for char in invalid_chars:
            if char in value:
                raise serializers.ValidationError(f"URL contains invalid character: {char}")
        
        return value
    
    def validate(self, attrs):
        """
        Validate that URL is unique for this user
        """
        user = self.context['request'].user
        url = attrs.get('url')
        
        if url:
            # Check for existing document with same URL for this user
            existing = FileDocument.objects.filter(owner=user, url=url)
            if self.instance:
                existing = existing.exclude(id=self.instance.id)
            
            if existing.exists():
                raise serializers.ValidationError({
                    'url': 'You already have a document at this URL path'
                })
        
        return attrs
    
    def create(self, validated_data):
        """
        Create document with current user as owner
        """
        user = self.context['request'].user
        validated_data['owner'] = user
        return super().create(validated_data)


class FileDocumentListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for listing documents
    """
    latest_revision = FileRevisionListSerializer(
        source='get_latest_revision',
        read_only=True
    )
    revision_count = serializers.ReadOnlyField(source='get_revision_count')
    
    class Meta:
        model = FileDocument
        fields = [
            'id', 'url', 'name', 'created_at', 'updated_at',
            'latest_revision', 'revision_count'
        ]


class FileUploadSerializer(serializers.Serializer):
    """
    Serializer for file upload operations
    """
    url = serializers.CharField(
        max_length=500,
        required=False,
        help_text="URL path where the file should be accessible (optional, will be auto-generated if not provided)"
    )
    name = serializers.CharField(
        max_length=255,
        required=False,
        help_text="Display name for the file (optional, will use filename if not provided)"
    )
    file = serializers.FileField(
        help_text="The file to upload"
    )
    
    def validate_url(self, value):
        """
        Validate URL path format (only if provided)
        """
        if value:  # Only validate if URL is provided
            if not value.startswith('/'):
                raise serializers.ValidationError("URL must start with '/'")
            
            if value.endswith('/'):
                raise serializers.ValidationError("URL cannot end with '/'")
        
        return value
    
    def validate_file(self, value):
        """
        Validate uploaded file
        """
        # File size validation (10MB max)
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size too large. Maximum size is {max_size // (1024*1024)}MB"
            )
        
        if value.size == 0:
            raise serializers.ValidationError("File is empty")
        
        return value
    
    def validate(self, attrs):
        """
        Set default name if not provided
        """
        if not attrs.get('name'):
            file_obj = attrs.get('file')
            if file_obj:
                attrs['name'] = os.path.basename(file_obj.name)
        
        return attrs


class FileDocumentDetailSerializer(FileDocumentSerializer):
    """
    Detailed serializer for single document view
    """
    # Include all revisions in detail view
    class Meta(FileDocumentSerializer.Meta):
        fields = FileDocumentSerializer.Meta.fields
    
    def to_representation(self, instance):
        """
        Customize representation to include all revisions
        """
        data = super().to_representation(instance)
        
        # Include all revisions in detail view
        if not self.context.get('exclude_revisions', False):
            revisions = instance.revisions.all()
            data['revisions'] = FileRevisionListSerializer(
                revisions, 
                many=True, 
                context=self.context
            ).data
        
        return data