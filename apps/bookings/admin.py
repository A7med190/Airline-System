from django.contrib import admin
from .models import Booking, Payment


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "booking_reference", "user", "flight", "seat_number", "status", "total_price", "booking_date")
    list_filter = ("status",)
    search_fields = ("user__email", "flight__flight_number")
    readonly_fields = ("booking_reference", "booking_date")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("transaction_id", "booking", "amount", "payment_method", "status", "transaction_date")
    list_filter = ("status", "payment_method")
    search_fields = ("transaction_id", "booking__user__email")
