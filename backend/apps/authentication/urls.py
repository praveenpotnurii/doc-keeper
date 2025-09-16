"""
Authentication URLs
"""
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView
)

# These will be expanded in Commit 4
urlpatterns = [
    # JWT Token endpoints
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # Custom auth endpoints (to be added in Commit 4)
    # path('register/', views.RegisterView.as_view(), name='register'),
    # path('logout/', views.LogoutView.as_view(), name='logout'),
    # path('profile/', views.ProfileView.as_view(), name='profile'),
]