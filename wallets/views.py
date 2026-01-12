from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction as db_transaction
from decimal import Decimal
import logging

from .models import Wallet, Transaction
from .serializers import (
    WalletSerializer,
    TransactionSerializer,
    PaymentSerializer,
    AddBalanceSerializer
)
from appointments.models import Appointment
from pharmacy.models import Order

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_wallet(request):
    """Get current user's wallet"""
    wallet, created = Wallet.get_or_create_wallet(request.user)
    serializer = WalletSerializer(wallet)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_transactions(request):
    """Get current user's transaction history"""
    wallet, created = Wallet.get_or_create_wallet(request.user)
    transactions = wallet.transactions.all()[:50]  # Last 50 transactions
    serializer = TransactionSerializer(transactions, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_balance(request):
    """Add balance to wallet"""
    serializer = AddBalanceSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    amount = serializer.validated_data['amount']
    payment_method = serializer.validated_data['payment_method']
    payment_gateway_transaction_id = serializer.validated_data.get('payment_gateway_transaction_id', '')
    
    try:
        wallet, created = Wallet.get_or_create_wallet(request.user)
        
        with db_transaction.atomic():
            # Add balance
            wallet.add_balance(amount)
            
            # Create credit transaction
            transaction = Transaction.objects.create(
                wallet=wallet,
                transaction_type='credit',
                amount=amount,
                balance_after=wallet.balance,
                description=f"Wallet recharge via {payment_method}",
                payment_method=payment_method,
                payment_gateway_transaction_id=payment_gateway_transaction_id,
                status='completed'
            )
        
        logger.info(f"Balance added to wallet: User={request.user.id}, Amount={amount}")
        
        return Response({
            'message': 'Balance added successfully',
            'wallet': WalletSerializer(wallet).data,
            'transaction': TransactionSerializer(transaction).data
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error adding balance: {str(e)}")
        return Response(
            {'error': 'Failed to add balance. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_payment(request):
    """Process payment for appointment or order"""
    serializer = PaymentSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    amount = serializer.validated_data['amount']
    description = serializer.validated_data['description']
    appointment_id = serializer.validated_data.get('appointment_id')
    order_id = serializer.validated_data.get('order_id')
    payment_method = serializer.validated_data.get('payment_method', 'wallet')
    
    try:
        wallet, created = Wallet.get_or_create_wallet(request.user)
        
        # Verify user has sufficient balance if paying from wallet
        if payment_method == 'wallet' and wallet.balance < amount:
            return Response(
                {'error': 'Insufficient wallet balance. Please add money to your wallet.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get related appointment or order
        appointment = None
        order = None
        
        if appointment_id:
            appointment = get_object_or_404(Appointment, id=appointment_id)
            # Verify user is the patient
            if appointment.patient != request.user:
                return Response(
                    {'error': 'You are not authorized to pay for this appointment.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            # Verify appointment is not already paid
            if appointment.transactions.filter(status='completed').exists():
                return Response(
                    {'error': 'This appointment has already been paid.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if order_id:
            order = get_object_or_404(Order, id=order_id)
            # Verify user is the patient
            if order.patient != request.user:
                return Response(
                    {'error': 'You are not authorized to pay for this order.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            # Verify order is not already paid
            if order.transactions.filter(status='completed').exists():
                return Response(
                    {'error': 'This order has already been paid.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        with db_transaction.atomic():
            # Deduct from wallet if payment method is wallet
            if payment_method == 'wallet':
                if not wallet.deduct_balance(amount):
                    return Response(
                        {'error': 'Insufficient wallet balance.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Create debit transaction
            transaction = Transaction.objects.create(
                wallet=wallet,
                transaction_type='debit',
                amount=amount,
                balance_after=wallet.balance,
                description=description,
                appointment=appointment,
                order=order,
                payment_method=payment_method,
                status='completed'
            )
            
            # Credit to recipient's wallet
            if appointment:
                # Credit to doctor's wallet
                doctor_wallet, _ = Wallet.get_or_create_wallet(appointment.doctor.user)
                doctor_wallet.add_balance(amount)
                
                # Create credit transaction for doctor
                Transaction.objects.create(
                    wallet=doctor_wallet,
                    transaction_type='credit',
                    amount=amount,
                    balance_after=doctor_wallet.balance,
                    description=f"Payment received for appointment #{appointment.id}",
                    appointment=appointment,
                    payment_method='wallet',
                    status='completed'
                )
            
            elif order:
                # Credit to pharmacist's wallet
                pharmacist_wallet, _ = Wallet.get_or_create_wallet(order.pharmacist.user)
                pharmacist_wallet.add_balance(amount)
                
                # Create credit transaction for pharmacist
                Transaction.objects.create(
                    wallet=pharmacist_wallet,
                    transaction_type='credit',
                    amount=amount,
                    balance_after=pharmacist_wallet.balance,
                    description=f"Payment received for order #{order.id}",
                    order=order,
                    payment_method='wallet',
                    status='completed'
                )
        
        logger.info(
            f"Payment processed: User={request.user.id}, Amount={amount}, "
            f"Appointment={appointment_id}, Order={order_id}"
        )
        
        return Response({
            'message': 'Payment processed successfully',
            'wallet': WalletSerializer(wallet).data,
            'transaction': TransactionSerializer(transaction).data
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error processing payment: {str(e)}")
        return Response(
            {'error': 'Failed to process payment. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pay_appointment(request, appointment_id):
    """Pay for a specific appointment"""
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    # Verify user is the patient
    if appointment.patient != request.user:
        return Response(
            {'error': 'You are not authorized to pay for this appointment.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Check if already paid
    if appointment.transactions.filter(status='completed').exists():
        return Response(
            {'error': 'This appointment has already been paid.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Use doctor's fee as amount
    amount = appointment.doctor.fee
    description = f"Payment for consultation with Dr. {appointment.doctor.user.get_full_name()}"
    
    # Process payment
    payment_data = {
        'amount': str(amount),
        'description': description,
        'appointment_id': appointment_id,
        'payment_method': 'wallet'
    }
    
    serializer = PaymentSerializer(data=payment_data)
    if serializer.is_valid():
        return process_payment(request)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pay_order(request, order_id):
    """Pay for a specific order"""
    order = get_object_or_404(Order, id=order_id)
    
    # Verify user is the patient
    if order.patient != request.user:
        return Response(
            {'error': 'You are not authorized to pay for this order.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Check if already paid
    if order.transactions.filter(status='completed').exists():
        return Response(
            {'error': 'This order has already been paid.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Use order total as amount
    if not order.total_amount:
        return Response(
            {'error': 'Order total amount is not set.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    amount = order.total_amount
    description = f"Payment for order #{order.id} from {order.pharmacist.store_name}"
    
    # Process payment
    payment_data = {
        'amount': str(amount),
        'description': description,
        'order_id': order_id,
        'payment_method': 'wallet'
    }
    
    serializer = PaymentSerializer(data=payment_data)
    if serializer.is_valid():
        return process_payment(request)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
