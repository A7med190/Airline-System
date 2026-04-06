from rest_framework import serializers
from .models import LoyaltyTransaction


class LoyaltyTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoyaltyTransaction
        fields = ("id", "points", "transaction_type", "reference", "created_at")
        read_only_fields = fields


class RedeemSerializer(serializers.Serializer):
    points = serializers.IntegerField(min_value=100)

    def validate_points(self, value):
        user = self.context["request"].user
        if value > user.loyalty_points_balance:
            raise serializers.ValidationError(f"Insufficient points. Balance: {user.loyalty_points_balance}")
        if value % 100 != 0:
            raise serializers.ValidationError("Points must be redeemed in multiples of 100.")
        return value
