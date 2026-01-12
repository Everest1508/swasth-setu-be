from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Q, Sum, F
from math import radians, cos, sin, asin, sqrt
import logging
from .models import Pharmacist, Prescription, Order, Medicine, MedicineStock, OrderItem

logger = logging.getLogger(__name__)
from .serializers import (
    PharmacistSerializer, 
    PrescriptionSerializer, 
    OrderSerializer,
    OrderCreateSerializer,
    MedicineSerializer,
    MedicineStockSerializer,
    MedicineStockCreateUpdateSerializer,
    MedicineSearchResultSerializer,
    OrderItemSerializer
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


# Medicine Management Views

class MedicineListView(generics.ListCreateAPIView):
    """List all medicines or create new medicine"""
    queryset = Medicine.objects.all()
    serializer_class = MedicineSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Medicine.objects.all()
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(generic_name__icontains=search) |
                Q(manufacturer__icontains=search)
            )
        return queryset

    def create(self, request, *args, **kwargs):
        """Create medicine with better error handling"""
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if medicine with same name already exists
        medicine_name = serializer.validated_data.get('name', '').strip()
        if medicine_name:
            existing_medicine = Medicine.objects.filter(name__iexact=medicine_name).first()
            if existing_medicine:
                return Response(
                    {
                        'error': f'Medicine with name "{medicine_name}" already exists.',
                        'existing_medicine_id': existing_medicine.id,
                        'existing_medicine': MedicineSerializer(existing_medicine).data
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        try:
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Exception as e:
            logger.error(f"Error creating medicine: {str(e)}")
            return Response(
                {'error': f'Failed to create medicine: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


class MedicineDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or delete medicine"""
    queryset = Medicine.objects.all()
    serializer_class = MedicineSerializer
    permission_classes = [IsAuthenticated]


class MedicineStockListView(generics.ListCreateAPIView):
    """List medicine stock for pharmacist or create new stock"""
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        logger.info(f"[MEDICINE_STOCK_LIST] API called by user: {user.username} (ID: {user.id}, is_pharmacist: {user.is_pharmacist})")
        
        if user.is_pharmacist:
            pharmacist = getattr(user, 'pharmacist_profile', None)
            if pharmacist:
                queryset = MedicineStock.objects.filter(pharmacist=pharmacist).select_related('medicine', 'pharmacist')
                stock_count = queryset.count()
                logger.info(f"[MEDICINE_STOCK_LIST] Pharmacist: {pharmacist.store_name} (ID: {pharmacist.id}), Found {stock_count} stock items")
                
                # Log each stock item
                for stock in queryset:
                    logger.debug(
                        f"[MEDICINE_STOCK] ID: {stock.id}, Medicine: {stock.medicine.name}, "
                        f"Quantity: {stock.quantity}, Price: ₹{stock.price_per_unit}, "
                        f"Available: {stock.is_available}, In Stock: {stock.is_in_stock}"
                    )
                
                return queryset
            else:
                logger.warning(f"[MEDICINE_STOCK_LIST] User {user.username} is pharmacist but has no pharmacist_profile")
        else:
            logger.warning(f"[MEDICINE_STOCK_LIST] User {user.username} is not a pharmacist")
        
        return MedicineStock.objects.none()

    def list(self, request, *args, **kwargs):
        """Override list to add debug logging"""
        logger.info(f"[MEDICINE_STOCK_LIST] GET request - User: {request.user.username}")
        response = super().list(request, *args, **kwargs)
        
        if response.status_code == 200:
            data = response.data
            count = len(data) if isinstance(data, list) else (data.get('count', 0) if isinstance(data, dict) else 0)
            logger.info(f"[MEDICINE_STOCK_LIST] Response: {count} items returned, Status: {response.status_code}")
        else:
            logger.warning(f"[MEDICINE_STOCK_LIST] Response Status: {response.status_code}, Data: {response.data}")
        
        return response

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return MedicineStockCreateUpdateSerializer
        return MedicineStockSerializer

    def perform_create(self, serializer):
        user = self.request.user
        logger.info(f"[MEDICINE_STOCK_CREATE] Creating stock - User: {user.username}")
        
        if not user.is_pharmacist:
            from rest_framework.exceptions import PermissionDenied
            logger.error(f"[MEDICINE_STOCK_CREATE] Permission denied - User {user.username} is not a pharmacist")
            raise PermissionDenied("Only pharmacists can create medicine stock")
        
        pharmacist = getattr(user, 'pharmacist_profile', None)
        if not pharmacist:
            from rest_framework.exceptions import PermissionDenied
            logger.error(f"[MEDICINE_STOCK_CREATE] Pharmacist profile not found for user {user.username}")
            raise PermissionDenied("Pharmacist profile not found")
        
        logger.info(f"[MEDICINE_STOCK_CREATE] Creating stock for pharmacist: {pharmacist.store_name}")
        serializer.save(pharmacist=pharmacist)
        logger.info(f"[MEDICINE_STOCK_CREATE] Stock created successfully - ID: {serializer.instance.id}")


class MedicineStockDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or delete medicine stock"""
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_pharmacist:
            pharmacist = getattr(user, 'pharmacist_profile', None)
            if pharmacist:
                return MedicineStock.objects.filter(pharmacist=pharmacist).select_related('medicine', 'pharmacist')
        return MedicineStock.objects.none()

    def get_serializer_class(self):
        return MedicineStockCreateUpdateSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_medicines(request):
    """Search medicines with availability from nearby pharmacists"""
    search_query = request.query_params.get('search', '').strip()
    latitude = request.query_params.get('latitude')
    longitude = request.query_params.get('longitude')
    max_distance = float(request.query_params.get('max_distance', 50))  # Default 50km

    if not search_query:
        return Response(
            {'error': 'Search query is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Search medicines
    medicines = Medicine.objects.filter(
        Q(name__icontains=search_query) |
        Q(generic_name__icontains=search_query) |
        Q(manufacturer__icontains=search_query)
    )

    results = []
    for medicine in medicines:
        # Get available stocks
        stocks = MedicineStock.objects.filter(
            medicine=medicine,
            is_available=True,
            quantity__gt=0
        ).select_related('pharmacist', 'medicine')

        # Filter by distance if location provided
        available_pharmacists = []
        if latitude and longitude:
            try:
                user_lat = float(latitude)
                user_lon = float(longitude)
                
                for stock in stocks:
                    if stock.pharmacist.latitude and stock.pharmacist.longitude:
                        distance = calculate_distance(
                            user_lat, user_lon,
                            float(stock.pharmacist.latitude), float(stock.pharmacist.longitude)
                        )
                        if distance <= max_distance:
                            stock.pharmacist.distance_km = round(distance, 2)
                            available_pharmacists.append({
                                'pharmacist_id': stock.pharmacist.id,
                                'store_name': stock.pharmacist.store_name,
                                'store_address': stock.pharmacist.store_address,
                                'quantity': stock.quantity,
                                'price_per_unit': float(stock.price_per_unit),
                                'distance_km': round(distance, 2),
                                'stock_id': stock.id,
                            })
            except ValueError:
                pass
        else:
            # No location filter, return all available
            for stock in stocks:
                available_pharmacists.append({
                    'pharmacist_id': stock.pharmacist.id,
                    'store_name': stock.pharmacist.store_name,
                    'store_address': stock.pharmacist.store_address,
                    'quantity': stock.quantity,
                    'price_per_unit': float(stock.price_per_unit),
                    'distance_km': None,
                    'stock_id': stock.id,
                })

        if available_pharmacists:
            medicine_serializer = MedicineSerializer(medicine)
            results.append({
                'medicine': medicine_serializer.data,
                'available_pharmacists': available_pharmacists,
            })

    return Response(results, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_medicine_order(request):
    """Create an order with medicine items"""
    pharmacist_id = request.data.get('pharmacist_id')
    items = request.data.get('items', [])  # List of {medicine_id, quantity, stock_id}
    delivery_address = request.data.get('delivery_address', '')
    patient_latitude = request.data.get('patient_latitude')
    patient_longitude = request.data.get('patient_longitude')
    notes = request.data.get('notes', '')

    if not pharmacist_id or not items:
        return Response(
            {'error': 'pharmacist_id and items are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        pharmacist = Pharmacist.objects.get(id=pharmacist_id, is_active=True)
    except Pharmacist.DoesNotExist:
        return Response(
            {'error': 'Pharmacist not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Validate items and calculate total
    order_items = []
    total_amount = 0

    for item in items:
        medicine_id = item.get('medicine_id')
        quantity = item.get('quantity')
        stock_id = item.get('stock_id')

        if not medicine_id or not quantity or quantity <= 0:
            return Response(
                {'error': f'Invalid item: medicine_id and quantity required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            medicine = Medicine.objects.get(id=medicine_id)
        except Medicine.DoesNotExist:
            return Response(
                {'error': f'Medicine {medicine_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get stock if stock_id provided
        stock = None
        price_per_unit = 0
        if stock_id:
            try:
                stock = MedicineStock.objects.get(
                    id=stock_id,
                    pharmacist=pharmacist,
                    medicine=medicine,
                    is_available=True
                )
                if stock.quantity < quantity:
                    return Response(
                        {'error': f'Insufficient stock for {medicine.name}. Available: {stock.quantity}, Requested: {quantity}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                price_per_unit = stock.price_per_unit
            except MedicineStock.DoesNotExist:
                return Response(
                    {'error': f'Stock not found for {medicine.name}'},
                    status=status.HTTP_404_NOT_FOUND
                )

        item_total = quantity * price_per_unit
        total_amount += item_total

        order_items.append({
            'medicine': medicine,
            'medicine_stock': stock,
            'quantity': quantity,
            'price_per_unit': price_per_unit,
            'total_price': item_total,
        })

    # Create order
    order = Order.objects.create(
        patient=request.user,
        pharmacist=pharmacist,
        prescription_text=f"Medicine order: {', '.join([item['medicine'].name for item in order_items])}",
        delivery_address=delivery_address,
        patient_latitude=round(float(patient_latitude), 6) if patient_latitude else None,
        patient_longitude=round(float(patient_longitude), 6) if patient_longitude else None,
        notes=notes,
        total_amount=total_amount,
        status='pending'
    )

    # Create order items and update stock
    for item_data in order_items:
        OrderItem.objects.create(
            order=order,
            medicine=item_data['medicine'],
            medicine_stock=item_data['medicine_stock'],
            quantity=item_data['quantity'],
            price_per_unit=item_data['price_per_unit'],
            total_price=item_data['total_price'],
        )

        # Update stock quantity
        if item_data['medicine_stock']:
            stock = item_data['medicine_stock']
            stock.quantity -= item_data['quantity']
            if stock.quantity == 0:
                stock.is_available = False
            stock.save()

    serializer = OrderSerializer(order, context={'request': request})
    return Response(serializer.data, status=status.HTTP_201_CREATED)

