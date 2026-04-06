from django.db import models


class Booking(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    user = models.ForeignKey("accounts.CustomUser", on_delete=models.CASCADE, related_name="bookings")
    flight = models.ForeignKey("flights.Flight", on_delete=models.PROTECT, related_name="bookings")
    seat_number = models.CharField(max_length=5)
    booking_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CONFIRMED)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    loyalty_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ["-booking_date"]

    def __str__(self):
        return f"Booking {self.id} - {self.flight.flight_number} - {self.user.email}"

    @property
    def booking_reference(self):
        return f"BKG-{self.id:06d}"


class Payment(models.Model):
    class PaymentMethod(models.TextChoices):
        CREDIT_CARD = "credit_card", "Credit Card"
        DEBIT_CARD = "debit_card", "Debit Card"
        PAYPAL = "paypal", "PayPal"

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="payment")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    transaction_date = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ["-transaction_date"]

    def __str__(self):
        return f"Payment {self.transaction_id} - {self.booking.booking_reference}"
