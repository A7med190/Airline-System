from django.db import models


class Airport(models.Model):
    code = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}, {self.city}"

    def save(self, *args, **kwargs):
        self.code = self.code.upper()
        super().save(*args, **kwargs)


class Flight(models.Model):
    flight_number = models.CharField(max_length=10, unique=True)
    departure_airport = models.ForeignKey(Airport, on_delete=models.PROTECT, related_name="departures")
    arrival_airport = models.ForeignKey(Airport, on_delete=models.PROTECT, related_name="arrivals")
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total_seats = models.IntegerField(default=180)
    available_seats = models.IntegerField()

    class Meta:
        ordering = ["departure_time"]

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
