import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import requests
from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.db import models


class OutboxEventStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"


class WebhookEventType(models.TextChoices):
    BOOKING_CREATED = "booking.created", "Booking Created"
    BOOKING_CANCELLED = "booking.cancelled", "Booking Cancelled"
    BOOKING_UPDATED = "booking.updated", "Booking Updated"
    FLIGHT_DELAYED = "flight.delayed", "Flight Delayed"
    FLIGHT_CANCELLED = "flight.cancelled", "Flight Cancelled"
    PAYMENT_COMPLETED = "payment.completed", "Payment Completed"
    PAYMENT_FAILED = "payment.failed", "Payment Failed"
    LOYALTY_POINTS_UPDATED = "loyalty.points_updated", "Loyalty Points Updated"


@dataclass
class WebhookPayload:
    event_type: str
    data: Dict[str, Any]
    timestamp: str
    event_id: str
    metadata: Optional[Dict[str, Any]] = None


class OutboxMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=100, db_index=True)
    payload = models.JSONField()
    status = models.CharField(
        max_length=20,
        choices=OutboxEventStatus.choices,
        default=OutboxEventStatus.PENDING,
        db_index=True,
    )
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.event_type} - {self.status}"


class WebhookSubscription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    url = models.URLField(max_length=2048)
    event_types = models.JSONField(default=list)
    secret = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.url} - {self.event_types}"

    def sign_payload(self, payload: str) -> str:
        return hmac.new(
            self.secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()


class WebhookDelivery(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    webhook = models.ForeignKey(WebhookSubscription, on_delete=models.CASCADE, related_name="deliveries")
    event_id = models.UUIDField(db_index=True)
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    status_code = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True, null=True)
    is_success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_id", "webhook"]),
        ]


class WebhookService:
    def __init__(self):
        self.config = getattr(settings, "WEBHOOKS", {})
        self.default_timeout = self.config.get("DEFAULT_TIMEOUT", 30)
        self.max_retries = self.config.get("MAX_RETRIES", 3)
        self.retry_delay = self.config.get("RETRY_DELAY", 5)

    def create_payload(self, event_type: str, data: Dict[str, Any], metadata: Dict[str, Any] = None) -> WebhookPayload:
        return WebhookPayload(
            event_type=event_type,
            data=data,
            timestamp=datetime.utcnow().isoformat(),
            event_id=str(uuid.uuid4()),
            metadata=metadata or {},
        )

    def publish_event(self, event_type: str, data: Dict[str, Any], metadata: Dict[str, Any] = None):
        OutboxMessage.objects.create(
            event_type=event_type,
            payload=self.create_payload(event_type, data, metadata).__dict__,
        )

    def send_webhook(self, subscription: WebhookSubscription, event_id: str, event_type: str, payload: WebhookPayload) -> WebhookDelivery:
        delivery = WebhookDelivery.objects.create(
            webhook=subscription,
            event_id=event_id,
            event_type=event_type,
            payload=payload.__dict__,
        )

        try:
            payload_str = json.dumps(payload.__dict__, default=str)
            headers = {
                "Content-Type": "application/json",
                "X-Webhook-Event": event_type,
                "X-Webhook-Event-ID": str(event_id),
                "X-Webhook-Timestamp": payload.timestamp,
            }
            
            if subscription.secret:
                signature = subscription.sign_payload(payload_str)
                headers["X-Webhook-Signature"] = signature

            response = requests.post(
                subscription.url,
                data=payload_str,
                headers=headers,
                timeout=self.default_timeout,
            )

            delivery.status_code = response.status_code
            delivery.response_body = response.text[:5000]
            delivery.is_success = 200 <= response.status_code < 300
            delivery.delivered_at = timezone.now()

            if not delivery.is_success:
                delivery.error_message = f"HTTP {response.status_code}: {response.reason}"

        except requests.Timeout:
            delivery.error_message = "Request timed out"
            delivery.is_success = False
        except requests.RequestException as e:
            delivery.error_message = str(e)
            delivery.is_success = False
        except Exception as e:
            delivery.error_message = f"Unexpected error: {str(e)}"
            delivery.is_success = False
        finally:
            delivery.save()

        return delivery

    def process_outbox_message(self, message: OutboxMessage):
        if message.status != OutboxEventStatus.PENDING:
            return

        message.status = OutboxEventStatus.PROCESSING
        message.save(update_fields=["status"])

        subscriptions = WebhookSubscription.objects.filter(
            is_active=True,
            event_types__contains=[message.event_type],
        )

        payload_data = message.payload
        event_id = payload_data.get("event_id", str(message.id))
        event_type = payload_data.get("event_type", message.event_type)

        for subscription in subscriptions:
            self.send_webhook(subscription, event_id, event_type, WebhookPayload(**payload_data))

        message.status = OutboxEventStatus.SENT
        message.processed_at = timezone.now()
        message.save(update_fields=["status", "processed_at"])

    def get_subscriptions_for_event(self, event_type: str) -> List[WebhookSubscription]:
        return WebhookSubscription.objects.filter(
            is_active=True,
            event_types__contains=[event_type],
        )


def publish_webhook(event_type: str, data: Dict[str, Any], metadata: Dict[str, Any] = None):
    webhook_service = WebhookService()
    webhook_service.publish_event(event_type, data, metadata)


@shared_task(bind=True, max_retries=3)
def process_outbox_messages(self):
    from django.utils import timezone
    
    batch_size = getattr(settings, "OUTBOX_PROCESSING_BATCH_SIZE", 100)
    
    messages = OutboxMessage.objects.filter(
        status=OutboxEventStatus.PENDING
    ).order_by("created_at")[:batch_size]
    
    webhook_service = WebhookService()
    
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
def send_webhook_notification(webhook_id: str, event_id: str, event_type: str, payload: dict):
    webhook_service = WebhookService()
    try:
        subscription = WebhookSubscription.objects.get(id=webhook_id)
        webhook_service.send_webhook(
            subscription,
            event_id,
            event_type,
            WebhookPayload(**payload),
        )
    except WebhookSubscription.DoesNotExist:
        pass
