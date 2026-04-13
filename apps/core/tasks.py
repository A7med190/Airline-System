from celery import shared_task
from django.utils import timezone


@shared_task(bind=True, max_retries=3)
def process_outbox_messages(self):
    from apps.core.webhooks import WebhookService
    
    batch_size = 100
    webhook_service = WebhookService()
    
    from apps.core.webhooks import OutboxMessage, OutboxEventStatus
    
    messages = OutboxMessage.objects.filter(
        status=OutboxEventStatus.PENDING
    ).order_by("created_at")[:batch_size]
    
    for message in messages:
        try:
            webhook_service.process_outbox_message(message)
        except Exception as e:
            message.status = OutboxEventStatus.FAILED
            message.error_message = str(e)
            message.retry_count += 1
            if message.retry_count < message.max_retries:
                message.status = OutboxEventStatus.PENDING
            message.save()


@shared_task
def cleanup_expired_idempotency_keys():
    pass


@shared_task
def health_check_sync():
    pass


@shared_task(bind=True, max_retries=3)
def send_notification(self, channel: str, event_type: str, data: dict):
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    
    channel_layer = get_channel_layer()
    
    try:
        async_to_sync(channel_layer.group_send)(
            f"notifications_{channel}",
            {
                "type": "notification_message",
                "event_type": event_type,
                "data": data,
            }
        )
    except Exception as e:
        raise self.retry(exc=e, countdown=5)


@shared_task(bind=True)
def cleanup_old_webhook_deliveries(self):
    from datetime import timedelta
    from apps.core.webhooks import WebhookDelivery
    
    cutoff_date = timezone.now() - timedelta(days=30)
    deleted_count, _ = WebhookDelivery.objects.filter(created_at__lt=cutoff_date).delete()
    return deleted_count
