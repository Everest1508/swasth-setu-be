"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('login/', views.user_login, name='user_login'),
    path('register/', views.user_register, name='user_register'),
    path('logout/', views.user_logout, name='user_logout'),
    path('admin/', admin.site.urls),
    
    # Admin panel routes
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/users/', views.manage_users, name='admin_manage_users'),
    path('admin-panel/doctors/', views.manage_doctors, name='admin_manage_doctors'),
    path('admin-panel/pharmacists/', views.manage_pharmacists, name='admin_manage_pharmacists'),
    path('admin-panel/doctor-applications/', views.doctor_applications, name='admin_doctor_applications'),
    path('admin-panel/pharmacist-applications/', views.pharmacist_applications, name='admin_pharmacist_applications'),
    path('admin-panel/toggle-user/<int:user_id>/', views.toggle_user_status, name='admin_toggle_user'),
    path('admin-panel/toggle-doctor/<int:doctor_id>/', views.toggle_doctor_status, name='admin_toggle_doctor'),
    path('admin-panel/toggle-pharmacist/<int:pharmacist_id>/', views.toggle_pharmacist_status, name='admin_toggle_pharmacist'),
    path('admin-panel/approve-doctor/<int:app_id>/', views.approve_doctor_application, name='admin_approve_doctor'),
    path('admin-panel/approve-pharmacist/<int:app_id>/', views.approve_pharmacist_application, name='admin_approve_pharmacist'),
    path('admin-panel/reject/<str:app_type>/<int:app_id>/', views.reject_application, name='admin_reject_application'),
    
    # Application routes
    path('apply/doctor/', views.apply_doctor, name='admin_apply_doctor'),
    path('apply/pharmacist/', views.apply_pharmacist, name='admin_apply_pharmacist'),
    
    # API routes
    path('api/auth/', include('api.urls')),
    path('api/appointments/', include('appointments.urls')),
    path('api/video-calls/', include('video_calls.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('api/pharmacy/', include('pharmacy.urls')),
]

# Serve media and static files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
