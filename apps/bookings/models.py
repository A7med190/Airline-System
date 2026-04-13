from django.db import models
from apps.core.soft_delete import BaseSoftDeleteModel


class Booking(BaseSoftDeleteModel):
    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    user = models.ForeignKey("accounts.CustomUser", on_delete=models.CASCADE, related_name="bookings", db_index=True)
    flight = models.ForeignKey("flights.Flight", on_delete=models.PROTECT, related_name="bookings", db_index=True)
    seat_number = models.CharField(max_length=5, db_index=True)
    booking_date = models.DateTimeField(auto_now_add=True, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CONFIRMED, db_index=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    loyalty_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    use_loyalty_points = models.IntegerField(default=0)

    class Meta:
        ordering = ["-booking_date"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["flight", "status"]),
            models.Index(fields=["booking_date", "status"]),
        ]

    def __str__(self):
        return f"Booking {self.id} - {self.flight.flight_number} - {self.user.email}"

    @property
    def booking_reference(self):
        return f"BKG-{self.id:06d}"

    def cancel(self):
        self.status = self.Status.CANCELLED
        self.save(update_fields=["status"])
        
        self.flight.available_seats += 1
        self.flight.save(update_fields=["available_seats"])
        
        from apps.core.webhooks import publish_webhook
        publish_webhook(
            event_type="booking.cancelled",
            data={
                "booking_id": self.id,
                "user_id": self.user_id,
                "flight_id": self.flight_id,
            }
        )


class Payment(BaseSoftDeleteModel):
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
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, db_index=True)
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING, db_index=True)
    transaction_date = models.DateTimeField(auto_now_add=True, db_index=True)
    transaction_id = models.CharField(max_length=50, unique=True, db_index=True)

    class Meta:
        ordering = ["-transaction_date"]
        indexes = [
            models.Index(fields=["status", "transaction_date"]),
        ]

    def __str__(self):
        return f"Payment {self.transaction_id} - {self.booking.booking_reference}"

    def refund(self):
        self.status = self.PaymentStatus.REFUNDED
        self.save(update_fields=["status"])
        
        from apps.core.webhooks import publish_webhook
        publish_webhook(
            event_type="payment.refunded",
            data={
                "payment_id": self.id,
                "booking_id": self.booking_id,
                "amount": str(self.amount),
            }
        )
