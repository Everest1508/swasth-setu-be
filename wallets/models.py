from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import uuid


class Wallet(models.Model):
    """Wallet model for storing user balance"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wallet'
    )
    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Current wallet balance"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Wallet - {self.user.get_full_name()} - ₹{self.balance}"

    def add_balance(self, amount):
        """Add balance to wallet"""
        self.balance += Decimal(str(amount))
        self.save()

    def deduct_balance(self, amount):
        """Deduct balance from wallet"""
        if self.balance >= Decimal(str(amount)):
            self.balance -= Decimal(str(amount))
            self.save()
            return True
        return False

    @classmethod
    def get_or_create_wallet(cls, user):
        """Get or create wallet for a user"""
        wallet, created = cls.objects.get_or_create(user=user)
        return wallet, created


class Transaction(models.Model):
    """Transaction model for tracking all wallet transactions"""
    TRANSACTION_TYPE_CHOICES = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('wallet', 'Wallet'),
        ('upi', 'UPI'),
        ('card', 'Card'),
        ('netbanking', 'Net Banking'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    transaction_type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPE_CHOICES
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    balance_after = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Wallet balance after this transaction"
    )
    description = models.TextField(help_text="Transaction description")
    
    # Related entities
    appointment = models.ForeignKey(
        'appointments.Appointment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        help_text="Related appointment if payment is for consultation"
    )
    order = models.ForeignKey(
        'pharmacy.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        help_text="Related order if payment is for pharmacy order"
    )
    
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='wallet'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # Payment gateway details (if applicable)
    payment_gateway_transaction_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Transaction ID from payment gateway"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['wallet', '-created_at']),
            models.Index(fields=['appointment']),
            models.Index(fields=['order']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.get_transaction_type_display()} - ₹{self.amount} - {self.wallet.user.get_full_name()}"

    def complete(self):
        """Mark transaction as completed"""
        self.status = 'completed'
        self.save()

    def fail(self):
        """Mark transaction as failed"""
        self.status = 'failed'
        self.save()
