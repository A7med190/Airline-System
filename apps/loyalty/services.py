from django.db import transaction
from .models import LoyaltyTransaction


def earn_points(user, amount_spent):
    points = int(amount_spent / 10)
    if points <= 0:
        return 0
    with transaction.atomic():
        user.loyalty_points_balance += points
        user.save()
        LoyaltyTransaction.objects.create(
            user=user,
            points=points,
            transaction_type=LoyaltyTransaction.TransactionType.EARNED,
            reference=f"Booking purchase - ${amount_spent:.2f}",
        )
    return points


def redeem_points(user, points):
    if points > user.loyalty_points_balance:
        raise ValueError("Insufficient loyalty points")
    if points < 100:
        raise ValueError("Minimum redemption is 100 points")
    with transaction.atomic():
        user.loyalty_points_balance -= points
        user.save()
        LoyaltyTransaction.objects.create(
            user=user,
            points=points,
            transaction_type=LoyaltyTransaction.TransactionType.REDEEMED,
            reference="Points redeemed for discount",
        )
    return points


def calculate_discount(points):
    return (points / 100) * 10


def refund_loyalty_points(user, points, booking_reference):
    if points <= 0:
        return
    with transaction.atomic():
        user.loyalty_points_balance += points
        user.save()
        LoyaltyTransaction.objects.create(
            user=user,
            points=points,
            transaction_type=LoyaltyTransaction.TransactionType.EARNED,
            reference=f"Refund from cancelled booking {booking_reference}",
        )
