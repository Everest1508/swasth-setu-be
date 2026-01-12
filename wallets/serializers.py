from rest_framework import serializers
from .models import Wallet, Transaction
from appointments.models import Appointment
from pharmacy.models import Order


class WalletSerializer(serializers.ModelSerializer):
    """Serializer for Wallet model"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Wallet
        fields = ('id', 'user', 'user_name', 'user_email', 'balance', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for Transaction model"""
    wallet_user = serializers.CharField(source='wallet.user.get_full_name', read_only=True)
    appointment_doctor = serializers.CharField(
        source='appointment.doctor.user.get_full_name',
        read_only=True,
        allow_null=True
    )
    order_pharmacist = serializers.CharField(
        source='order.pharmacist.store_name',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = Transaction
        fields = (
            'id', 'wallet', 'wallet_user', 'transaction_type', 'amount',
            'balance_after', 'description', 'appointment', 'appointment_doctor',
            'order', 'order_pharmacist', 'payment_method', 'status',
            'payment_gateway_transaction_id', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class PaymentSerializer(serializers.Serializer):
    """Serializer for payment processing"""
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)
    description = serializers.CharField(max_length=500)
    appointment_id = serializers.IntegerField(required=False, allow_null=True)
    order_id = serializers.IntegerField(required=False, allow_null=True)
    payment_method = serializers.ChoiceField(
        choices=Transaction.PAYMENT_METHOD_CHOICES,
        default='wallet'
    )

    def validate(self, data):
        """Validate that either appointment_id or order_id is provided"""
        appointment_id = data.get('appointment_id')
        order_id = data.get('order_id')
        
        if not appointment_id and not order_id:
            raise serializers.ValidationError(
                "Either appointment_id or order_id must be provided"
            )
        
        if appointment_id and order_id:
            raise serializers.ValidationError(
                "Only one of appointment_id or order_id should be provided"
            )
        
        return data


class AddBalanceSerializer(serializers.Serializer):
    """Serializer for adding balance to wallet"""
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)
    payment_method = serializers.ChoiceField(
        choices=['upi', 'card', 'netbanking'],
        required=True
    )
    payment_gateway_transaction_id = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True
    )


