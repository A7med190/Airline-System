from django.db import models
from apps.core.soft_delete import BaseSoftDeleteModel


class LoyaltyAccount(BaseSoftDeleteModel):
    user = models.OneToOneField("accounts.CustomUser", on_delete=models.CASCADE, related_name="loyalty_account", db_index=True)
    points_balance = models.IntegerField(default=0)
    tier = models.CharField(max_length=20, default="bronze", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Loyalty Accounts"
        indexes = [
            models.Index(fields=["tier", "points_balance"]),
        ]

    def __str__(self):
        return f"{self.user.email}: {self.points_balance} points"

    def add_points(self, points: int, description: str = ""):
        from apps.loyalty.models import LoyaltyTransaction
        self.points_balance += points
        self.save(update_fields=["points_balance", "updated_at"])
        
        LoyaltyTransaction.objects.create(
            user=self.user,
            points=points,
            transaction_type=LoyaltyTransaction.TransactionType.CREDIT,
            description=description,
        )
        
        self._update_tier()
        
        from apps.core.webhooks import publish_webhook
        publish_webhook(
            event_type="loyalty.points_updated",
            data={
                "user_id": self.user_id,
                "points_balance": self.points_balance,
                "points_added": points,
            }
        )

    def deduct_points(self, points: int, description: str = ""):
        if self.points_balance < points:
            raise ValueError("Insufficient points")
        
        from apps.loyalty.models import LoyaltyTransaction
        self.points_balance -= points
        self.save(update_fields=["points_balance", "updated_at"])
        
        LoyaltyTransaction.objects.create(
            user=self.user,
            points=points,
            transaction_type=LoyaltyTransaction.TransactionType.DEBIT,
            description=description,
        )
        
        self._update_tier()

    def _update_tier(self):
        tiers = {
            "bronze": 0,
            "silver": 1000,
            "gold": 5000,
            "platinum": 15000,
        }
        
        for tier_name, threshold in sorted(tiers.items(), key=lambda x: x[1], reverse=True):
            if self.points_balance >= threshold:
                if self.tier != tier_name:
                    self.tier = tier_name
                    self.save(update_fields=["tier", "updated_at"])
                break


class LoyaltyTransaction(BaseSoftDeleteModel):
    class TransactionType(models.TextChoices):
        CREDIT = "credit", "Credit"
        DEBIT = "debit", "Debit"
        EARNED = "earned", "Earned"
        REDEEMED = "redeemed", "Redeemed"
        REFUND = "refund", "Refund"

    user = models.ForeignKey("accounts.CustomUser", on_delete=models.CASCADE, related_name="loyalty_transactions", db_index=True)
    points = models.IntegerField()
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices, db_index=True)
    description = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "transaction_type"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        sign = "+" if self.transaction_type in [self.TransactionType.CREDIT, self.TransactionType.EARNED] else "-"
        return f"{self.user.email}: {sign}{abs(self.points)} points ({self.transaction_type})"
