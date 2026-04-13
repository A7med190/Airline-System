from django.db import models
from django.utils import timezone
from apps.core.soft_delete import BaseSoftDeleteModel


class Airport(BaseSoftDeleteModel):
    code = models.CharField(max_length=3, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)

    class Meta:
        ordering = ["code"]
        indexes = [
            models.Index(fields=["city", "country"]),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}, {self.city}"

    def save(self, *args, **kwargs):
        self.code = self.code.upper()
        super().save(*args, **kwargs)


class Flight(BaseSoftDeleteModel):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        DELAYED = "delayed", "Delayed"
        BOARDING = "boarding", "Boarding"
        DEPARTED = "departed", "Departed"
        ARRIVED = "arrived", "Arrived"
        CANCELLED = "cancelled", "Cancelled"

    flight_number = models.CharField(max_length=10, unique=True, db_index=True)
    departure_airport = models.ForeignKey(Airport, on_delete=models.PROTECT, related_name="departures")
    arrival_airport = models.ForeignKey(Airport, on_delete=models.PROTECT, related_name="arrivals")
    departure_time = models.DateTimeField(db_index=True)
    arrival_time = models.DateTimeField(db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total_seats = models.IntegerField(default=180)
    available_seats = models.IntegerField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED,
        db_index=True,
    )
    delay_minutes = models.IntegerField(default=0)

    class Meta:
        ordering = ["departure_time"]
        indexes = [
            models.Index(fields=["departure_airport", "departure_time"]),
            models.Index(fields=["arrival_airport", "arrival_time"]),
            models.Index(fields=["status", "departure_time"]),
            models.Index(fields=["price"]),
        ]

    def __str__(self):
        return f"{self.flight_number}: {self.departure_airport.code} -> {self.arrival_airport.code}"

    def save(self, *args, **kwargs):
        if not self.available_seats:
            self.available_seats = self.total_seats
        super().save(*args, **kwargs)

    @property
    def flight_duration(self):
        delta = self.arrival_time - self.departure_time
        total_minutes = int(delta.total_seconds() / 60)
        hours = total_minutes // 60
        minutes = total_minutes % 60
        return f"{hours}h {minutes}m"

    def delay(self, minutes: int):
        self.delay_minutes += minutes
        self.departure_time += timezone.timedelta(minutes=minutes)
        self.arrival_time += timezone.timedelta(minutes=minutes)
        if self.delay_minutes > 15:
            self.status = self.Status.DELAYED
        self.save(update_fields=["delay_minutes", "departure_time", "arrival_time", "status"])
        
        from apps.core.webhooks import publish_webhook
        publish_webhook(
            event_type="flight.delayed",
            data={
                "flight_id": self.id,
                "flight_number": self.flight_number,
                "delay_minutes": minutes,
            }
        )
