from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('refresh/', views.refresh_view, name='refresh'),
    path('verify-email/', views.verify_email_view, name='verify-email'),
    path('resend-verification/', views.resend_verification_view, name='resend-verification'),
    path('forgot-password/', views.forgot_password_view, name='forgot-password'),
    path('reset-password/', views.reset_password_view, name='reset-password'),
    path('me/', views.me_view, name='me'),
    path('me/profile/', views.me_profile_view, name='me-profile'),
    path('change-password/', views.change_password_view, name='change-password'),
    path('admin/users/', views.admin_users_view, name='admin-users'),
    path('admin/users/<int:user_id>/', views.admin_user_delete_view, name='admin-user-delete'),
    path('admin/users/<int:user_id>/lock/', views.admin_user_lock_view, name='admin-user-lock'),
    path('admin/dashboard/', views.admin_dashboard_view, name='admin-dashboard'),
]