from django.contrib import admin
from .models import Airport, Flight


@admin.register(Airport)
class AirportAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "city", "country")
    search_fields = ("code", "name", "city", "country")


@admin.register(Flight)
class FlightAdmin(admin.ModelAdmin):
    list_display = ("flight_number", "departure_airport", "arrival_airport", "departure_time", "price", "available_seats", "total_seats")
    list_filter = ("departure_airport", "arrival_airport")
    search_fields = ("flight_number",)
    date_hierarchy = "departure_time"
