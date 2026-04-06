from django.db import models


class LoyaltyTransaction(models.Model):
    class TransactionType(models.TextChoices):
        EARNED = "earned", "Earned"
        REDEEMED = "redeemed", "Redeemed"

    user = models.ForeignKey("accounts.CustomUser", on_delete=models.CASCADE, related_name="loyalty_transactions")
    points = models.IntegerField()
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    reference = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        sign = "+" if self.transaction_type == self.TransactionType.EARNED else "-"
        return f"{self.user.email}: {sign}{abs(self.points)} points ({self.transaction_type})"
