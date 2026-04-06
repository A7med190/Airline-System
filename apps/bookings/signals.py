from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from apps.bookings.models import Booking
from apps.loyalty.models import LoyaltyAccount, LoyaltyTransaction


@receiver(post_save, sender=Booking)
def booking_created(sender, instance, created, **kwargs):
    if created and instance.status == 'confirmed':
        user = instance.user
        points_earned = int(instance.total_price / 10)
        
        loyalty_account, _ = LoyaltyAccount.objects.get_or_create(
            user=user,
            defaults={'points_balance': 0}
        )
        
        loyalty_account.points_balance += points_earned
        loyalty_account.save()
        
        LoyaltyTransaction.objects.create(
            account=loyalty_account,
            transaction_type='EARN',
            points=points_earned,
            description=f'Points earned from booking {instance.booking_code}'
        )


@receiver(pre_save, sender=Booking)
def booking_status_changed(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_booking = Booking.objects.get(pk=instance.pk)
            if old_booking.status != instance.status:
                if instance.status == 'cancelled':
                    points_to_refund = int(old_booking.total_price / 10)
                    if points_to_refund > 0:
                        loyalty_account = LoyaltyAccount.objects.filter(user=instance.user).first()
                        if loyalty_account:
                            loyalty_account.points_balance = max(0, loyalty_account.points_balance - points_to_refund)
                            loyalty_account.save()
                            
                            LoyaltyTransaction.objects.create(
                                account=loyalty_account,
                                transaction_type='REFUND',
                                points=-points_to_refund,
                                description=f'Points refunded for cancelled booking {instance.booking_code}'
                            )
        except Booking.DoesNotExist:
            pass