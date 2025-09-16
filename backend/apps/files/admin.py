from django.contrib import admin
from .models import FileDocument, FileRevision


class FileRevisionInline(admin.TabularInline):
    model = FileRevision
    extra = 0
    readonly_fields = ('uploaded_at', 'file_size', 'formatted_file_size')
    fields = ('revision_number', 'file_data', 'uploaded_at', 'formatted_file_size', 'content_type')


@admin.register(FileDocument)
class FileDocumentAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'owner', 'get_revision_count', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at', 'owner')
    search_fields = ('name', 'url', 'owner__username')
    readonly_fields = ('created_at', 'updated_at', 'get_revision_count')
    inlines = [FileRevisionInline]
    
    fieldsets = (
        (None, {
            'fields': ('name', 'url', 'owner')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'get_revision_count'),
            'classes': ('collapse',)
        })
    )


@admin.register(FileRevision)
class FileRevisionAdmin(admin.ModelAdmin):
    list_display = ('document', 'revision_number', 'formatted_file_size', 'file_extension', 'uploaded_at')
    list_filter = ('uploaded_at', 'content_type', 'document__owner')
    search_fields = ('document__name', 'document__url', 'document__owner__username')
    readonly_fields = ('uploaded_at', 'file_size', 'formatted_file_size', 'file_extension')
    
    fieldsets = (
        (None, {
            'fields': ('document', 'revision_number', 'file_data')
        }),
        ('File Information', {
            'fields': ('file_size', 'formatted_file_size', 'file_extension', 'content_type', 'uploaded_at'),
            'classes': ('collapse',)
        })
    )
