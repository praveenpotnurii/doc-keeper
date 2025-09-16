from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    readonly_fields = ('created_at', 'storage_used', 'formatted_storage_used', 'formatted_storage_limit', 'storage_usage_percentage')


class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = UserAdmin.list_display + ('get_storage_used', 'get_file_count')
    
    def get_storage_used(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.formatted_storage_used
        return "N/A"
    get_storage_used.short_description = 'Storage Used'
    
    def get_file_count(self, obj):
        return obj.file_documents.count()
    get_file_count.short_description = 'Files Count'


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'formatted_storage_used', 'formatted_storage_limit', 'storage_usage_percentage', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'storage_used', 'formatted_storage_used', 'formatted_storage_limit', 'storage_usage_percentage')
    
    fieldsets = (
        (None, {
            'fields': ('user',)
        }),
        ('Storage Information', {
            'fields': ('storage_limit', 'storage_used', 'formatted_storage_used', 'formatted_storage_limit', 'storage_usage_percentage')
        }),
        ('Metadata', {
            'fields': ('created_at', 'last_login_ip'),
            'classes': ('collapse',)
        })
    )
