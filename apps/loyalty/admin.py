from django.contrib import admin
from .models import LoyaltyTransaction


@admin.register(LoyaltyTransaction)
class LoyaltyTransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "points", "transaction_type", "created_at")
    list_filter = ("transaction_type",)
    search_fields = ("user__email", "reference")
    readonly_fields = ("created_at",)
