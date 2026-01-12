from django.db import models
from django.conf import settings


class Pharmacist(models.Model):
    """Pharmacist profile model"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pharmacist_profile'
    )
    store_name = models.CharField(max_length=200)
    store_address = models.TextField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['store_name']

    def __str__(self):
        return f"{self.store_name} - {self.user.get_full_name() or self.user.username}"

    @property
    def name(self):
        return self.user.get_full_name() or self.user.username



class Prescription(models.Model):
    """User-uploaded prescription model"""
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='prescriptions'
    )
    title = models.CharField(max_length=200, blank=True)
    image = models.ImageField(upload_to='prescriptions/', blank=True, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Prescription - {self.patient.get_full_name()} - {self.created_at.date()}"


class Order(models.Model):
    """Prescription order model"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready for Pickup'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    pharmacist = models.ForeignKey(
        Pharmacist,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )
    appointment = models.ForeignKey(
        'appointments.Appointment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )
    prescription_text = models.TextField(help_text="Prescription details from appointment or manual entry")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    delivery_address = models.TextField(blank=True)
    patient_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    patient_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    notes = models.TextField(blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.id} - {self.patient.get_full_name()} - {self.status}"


class Medicine(models.Model):
    """Medicine catalog model"""
    name = models.CharField(max_length=200, unique=True)
    generic_name = models.CharField(max_length=200, blank=True)
    manufacturer = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=50, default='piece', help_text="e.g., piece, strip, bottle, box")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['generic_name']),
        ]

    def __str__(self):
        return self.name


class MedicineStock(models.Model):
    """Medicine stock/inventory for each pharmacist"""
    pharmacist = models.ForeignKey(
        Pharmacist,
        on_delete=models.CASCADE,
        related_name='medicine_stocks'
    )
    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.CASCADE,
        related_name='stocks'
    )
    quantity = models.PositiveIntegerField(default=0)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    expiry_date = models.DateField(null=True, blank=True)
    batch_number = models.CharField(max_length=100, blank=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['pharmacist', 'medicine']
        ordering = ['medicine__name']
        indexes = [
            models.Index(fields=['pharmacist', 'is_available']),
            models.Index(fields=['medicine', 'is_available']),
        ]

    def __str__(self):
        return f"{self.pharmacist.store_name} - {self.medicine.name} ({self.quantity} {self.medicine.unit})"

    @property
    def is_in_stock(self):
        """Check if medicine is in stock"""
        return self.is_available and self.quantity > 0


class OrderItem(models.Model):
    """Individual medicine items in an order"""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.CASCADE,
        related_name='order_items'
    )
    medicine_stock = models.ForeignKey(
        MedicineStock,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_items'
    )
    quantity = models.PositiveIntegerField()
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['order', 'medicine__name']

    def __str__(self):
        return f"Order #{self.order.id} - {self.medicine.name} x{self.quantity}"

    def save(self, *args, **kwargs):
        """Calculate total price before saving"""
        self.total_price = self.quantity * self.price_per_unit
        super().save(*args, **kwargs)

