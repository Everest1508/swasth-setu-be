from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Q
from math import radians, cos, sin, asin, sqrt
from .models import Pharmacist, Prescription, Order
from .serializers import (
    PharmacistSerializer, 
    PrescriptionSerializer, 
    OrderSerializer,
    OrderCreateSerializer
)


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points using Haversine formula"""
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers
    
    return c * r


class PharmacistListView(generics.ListAPIView):
    """List all active pharmacists"""
    serializer_class = PharmacistSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Pharmacist.objects.filter(is_active=True)
        
        # If user location is provided, calculate distances
        user_lat = self.request.query_params.get('latitude')
        user_lon = self.request.query_params.get('longitude')
        
        if user_lat and user_lon:
            # Annotate with distance (we'll calculate in serializer)
            pass
        
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Calculate distances if user location provided
        user_lat = self.request.query_params.get('latitude')
        user_lon = self.request.query_params.get('longitude')
        
        if user_lat and user_lon:
            pharmacists = self.get_queryset()
            for pharmacist in pharmacists:
                if pharmacist.latitude and pharmacist.longitude:
                    distance = calculate_distance(
                        float(user_lat), float(user_lon),
                        float(pharmacist.latitude), float(pharmacist.longitude)
                    )
                    pharmacist.distance_km = round(distance, 2)
                else:
                    pharmacist.distance_km = None
        
        return context


class PharmacistDetailView(generics.RetrieveAPIView):
    """Get pharmacist details"""
    queryset = Pharmacist.objects.all()
    serializer_class = PharmacistSerializer
    permission_classes = [IsAuthenticated]


class PharmacistProfileView(generics.RetrieveUpdateAPIView):
    """Get or update pharmacist's own profile"""
    serializer_class = PharmacistSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        user = self.request.user
        if not user.is_pharmacist:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only pharmacists can access this endpoint")
        
        pharmacist, created = Pharmacist.objects.get_or_create(user=user)
        return pharmacist


class PrescriptionListView(generics.ListCreateAPIView):
    """List user's prescriptions or create new"""
    serializer_class = PrescriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Prescription.objects.filter(patient=self.request.user)


class PrescriptionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or delete prescription"""
    serializer_class = PrescriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Prescription.objects.filter(patient=self.request.user)


class OrderListView(generics.ListCreateAPIView):
    """List orders or create new order"""
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_pharmacist:
            # Pharmacist sees orders for their store
            pharmacist = getattr(user, 'pharmacist_profile', None)
            if pharmacist:
                return Order.objects.filter(pharmacist=pharmacist)
            return Order.objects.none()
        else:
            # Patient sees their own orders
            return Order.objects.filter(patient=user)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return OrderCreateSerializer
        return OrderSerializer

    def perform_create(self, serializer):
        serializer.save(patient=self.request.user)


class OrderDetailView(generics.RetrieveUpdateAPIView):
    """Get or update order"""
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_pharmacist:
            pharmacist = getattr(user, 'pharmacist_profile', None)
            if pharmacist:
                return Order.objects.filter(pharmacist=pharmacist)
            return Order.objects.none()
        return Order.objects.filter(patient=user)

    def perform_update(self, serializer):
        user = self.request.user
        instance = serializer.instance
        
        # Only pharmacist can update order status
        if user.is_pharmacist:
            new_status = serializer.validated_data.get('status', instance.status)
            serializer.save(status=new_status)
        else:
            # Patient can only update notes
            serializer.save()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def nearest_pharmacists(request):
    """Get nearest pharmacists based on user location"""
    latitude = request.query_params.get('latitude')
    longitude = request.query_params.get('longitude')
    
    if not latitude or not longitude:
        return Response(
            {'error': 'Latitude and longitude are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        user_lat = float(latitude)
        user_lon = float(longitude)
    except ValueError:
        return Response(
            {'error': 'Invalid latitude or longitude'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    pharmacists = Pharmacist.objects.filter(
        is_active=True,
        latitude__isnull=False,
        longitude__isnull=False
    )
    
    # Calculate distances
    pharmacists_with_distance = []
    for pharmacist in pharmacists:
        distance = calculate_distance(
            user_lat, user_lon,
            float(pharmacist.latitude), float(pharmacist.longitude)
        )
        pharmacists_with_distance.append({
            'pharmacist': pharmacist,
            'distance': round(distance, 2)
        })
    
    # Sort by distance
    pharmacists_with_distance.sort(key=lambda x: x['distance'])
    
    # Serialize
    serializer = PharmacistSerializer(
        [item['pharmacist'] for item in pharmacists_with_distance],
        many=True,
        context={'request': request}
    )
    
    # Add distance to each result
    result_data = serializer.data
    for i, item in enumerate(pharmacists_with_distance):
        result_data[i]['distance_km'] = item['distance']
    
    return Response(result_data, status=status.HTTP_200_OK)

