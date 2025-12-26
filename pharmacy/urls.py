from django.urls import path
from . import views

urlpatterns = [
    # Pharmacist endpoints
    path('pharmacists/', views.PharmacistListView.as_view(), name='pharmacist-list'),
    path('pharmacists/<int:pk>/', views.PharmacistDetailView.as_view(), name='pharmacist-detail'),
    path('pharmacists/nearest/', views.nearest_pharmacists, name='nearest-pharmacists'),
    path('pharmacists/profile/', views.PharmacistProfileView.as_view(), name='pharmacist-profile'),
    
    # Prescription endpoints
    path('prescriptions/', views.PrescriptionListView.as_view(), name='prescription-list'),
    path('prescriptions/<int:pk>/', views.PrescriptionDetailView.as_view(), name='prescription-detail'),
    
    # Order endpoints
    path('orders/', views.OrderListView.as_view(), name='order-list'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
]

