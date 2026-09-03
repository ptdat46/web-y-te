from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('refresh/', views.refresh_view, name='refresh'),
    path('me/', views.me_view, name='me'),
    path('change-password/', views.change_password_view, name='change-password'),
    path('admin/users/', views.admin_users_view, name='admin-users'),
    path('admin/users/<int:user_id>/', views.admin_user_delete_view, name='admin-user-delete'),
]