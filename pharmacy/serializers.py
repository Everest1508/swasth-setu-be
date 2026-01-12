from rest_framework import serializers
from .models import Pharmacist, Prescription, Order, Medicine, MedicineStock, OrderItem
from django.contrib.auth import get_user_model

User = get_user_model()


class PharmacistSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    id = serializers.IntegerField(source='pk', read_only=True)
    distance = serializers.SerializerMethodField()

    class Meta:
        model = Pharmacist
        fields = ('id', 'name', 'email', 'store_name', 'store_address', 
                  'latitude', 'longitude', 'phone', 'is_active', 'distance')

    def validate_latitude(self, value):
        """Round latitude to 6 decimal places"""
        if value is not None:
            return round(float(value), 6)
        return value

    def validate_longitude(self, value):
        """Round longitude to 6 decimal places"""
        if value is not None:
            return round(float(value), 6)
        return value

    def update(self, instance, validated_data):
        # Ensure coordinates are rounded
        if 'latitude' in validated_data and validated_data['latitude'] is not None:
            validated_data['latitude'] = round(float(validated_data['latitude']), 6)
        if 'longitude' in validated_data and validated_data['longitude'] is not None:
            validated_data['longitude'] = round(float(validated_data['longitude']), 6)
        return super().update(instance, validated_data)

    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_email(self, obj):
        return obj.user.email

    def get_distance(self, obj):
        """Calculate distance if user location is provided"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            user = request.user
            if user.latitude and user.longitude and obj.latitude and obj.longitude:
                # Simple distance calculation (Haversine formula would be better)
                # For now, return None and calculate in view
                return None
        return None


class PrescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prescription
        fields = ('id', 'title', 'image', 'notes', 'created_at', 'updated_at')
        read_only_fields = ('patient', 'created_at', 'updated_at')

    def create(self, validated_data):
        validated_data['patient'] = self.context['request'].user
        return super().create(validated_data)


class OrderSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    pharmacist_name = serializers.SerializerMethodField()
    pharmacist_store = serializers.SerializerMethodField()
    prescription_title = serializers.SerializerMethodField()
    prescription_image = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ('id', 'patient', 'patient_name', 'pharmacist', 'pharmacist_name', 
                  'pharmacist_store', 'prescription', 'prescription_title', 'prescription_image',
                  'appointment', 'prescription_text', 'status', 'delivery_address', 
                  'patient_latitude', 'patient_longitude', 'notes', 'total_amount', 
                  'created_at', 'updated_at')
        read_only_fields = ('patient', 'created_at', 'updated_at')

    def get_patient_name(self, obj):
        return obj.patient.get_full_name() or obj.patient.username

    def get_pharmacist_name(self, obj):
        return obj.pharmacist.name

    def get_pharmacist_store(self, obj):
        return obj.pharmacist.store_name

    def get_prescription_title(self, obj):
        return obj.prescription.title if obj.prescription else None

    def get_prescription_image(self, obj):
        """Return prescription image URL if available"""
        if obj.prescription and obj.prescription.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.prescription.image.url)
            return obj.prescription.image.url
        return None


class OrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ('pharmacist', 'prescription', 'appointment', 'prescription_text',
                  'delivery_address', 'patient_latitude', 'patient_longitude', 'notes')

    def validate_patient_latitude(self, value):
        """Round latitude to 6 decimal places"""
        if value is not None:
            return round(float(value), 6)
        return value

    def validate_patient_longitude(self, value):
        """Round longitude to 6 decimal places"""
        if value is not None:
            return round(float(value), 6)
        return value

    def create(self, validated_data):
        validated_data['patient'] = self.context['request'].user
        # Ensure coordinates are rounded
        if 'patient_latitude' in validated_data and validated_data['patient_latitude'] is not None:
            validated_data['patient_latitude'] = round(float(validated_data['patient_latitude']), 6)
        if 'patient_longitude' in validated_data and validated_data['patient_longitude'] is not None:
            validated_data['patient_longitude'] = round(float(validated_data['patient_longitude']), 6)
        return super().create(validated_data)


class MedicineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medicine
        fields = ('id', 'name', 'generic_name', 'manufacturer', 'description', 'unit', 'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at')


class MedicineStockSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source='medicine.name', read_only=True)
    medicine_generic_name = serializers.CharField(source='medicine.generic_name', read_only=True)
    medicine_unit = serializers.CharField(source='medicine.unit', read_only=True)
    pharmacist_store_name = serializers.CharField(source='pharmacist.store_name', read_only=True)
    is_in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = MedicineStock
        fields = ('id', 'pharmacist', 'pharmacist_store_name', 'medicine', 'medicine_name', 
                  'medicine_generic_name', 'medicine_unit', 'quantity', 'price_per_unit', 
                  'expiry_date', 'batch_number', 'is_available', 'is_in_stock', 
                  'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at')


class MedicineStockCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating stock (pharmacist only)"""
    class Meta:
        model = MedicineStock
        fields = ('medicine', 'quantity', 'price_per_unit', 'expiry_date', 'batch_number', 'is_available')

    def create(self, validated_data):
        # Get pharmacist from request user
        user = self.context['request'].user
        if not user.is_pharmacist:
            raise serializers.ValidationError("Only pharmacists can create medicine stock")
        
        pharmacist = getattr(user, 'pharmacist_profile', None)
        if not pharmacist:
            raise serializers.ValidationError("Pharmacist profile not found")
        
        validated_data['pharmacist'] = pharmacist
        return super().create(validated_data)


class MedicineSearchResultSerializer(serializers.Serializer):
    """Serializer for medicine search results with stock info"""
    medicine = MedicineSerializer()
    available_pharmacists = serializers.SerializerMethodField()

    def get_available_pharmacists(self, obj):
        """Get list of pharmacists who have this medicine in stock"""
        stocks = MedicineStock.objects.filter(
            medicine=obj['medicine'],
            is_available=True,
            quantity__gt=0
        ).select_related('pharmacist')
        
        return [
            {
                'pharmacist_id': stock.pharmacist.id,
                'store_name': stock.pharmacist.store_name,
                'store_address': stock.pharmacist.store_address,
                'quantity': stock.quantity,
                'price_per_unit': float(stock.price_per_unit),
                'distance_km': stock.pharmacist.distance_km if hasattr(stock.pharmacist, 'distance_km') else None,
            }
            for stock in stocks
        ]


class OrderItemSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source='medicine.name', read_only=True)
    medicine_unit = serializers.CharField(source='medicine.unit', read_only=True)

    class Meta:
        model = OrderItem
        fields = ('id', 'order', 'medicine', 'medicine_name', 'medicine_unit', 
                  'medicine_stock', 'quantity', 'price_per_unit', 'total_price')
        read_only_fields = ('total_price',)

