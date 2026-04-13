import asyncio
import json
from typing import Any, Dict, List, Optional

from asgiref.sync import async_to_sync, sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer
from django.conf import settings
from django.http import StreamingHttpResponse
from django.utils import timezone
from django.views import View
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView


class SSEView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        channels = request.query_params.getlist("channels", ["default"])
        
        async def event_stream():
            channel_layer = get_channel_layer()
            
            async def receive(message):
                return message
            
            groups = [f"sse_{channel}" for channel in channels]
            
            for group in groups:
                await channel_layer.group_add(group, "sse_client")
            
            try:
                while True:
                    message = await channel_layer.receive("sse_client")
                    event_type = message.get("type", "message")
                    data = message.get("data", {})
                    yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                for group in groups:
                    await channel_layer.group_discard(group, "sse_client")

        response = StreamingHttpResponse(
            event_stream(),
            content_type="text/event-stream"
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class WebhookSubscriptionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.core.webhooks import WebhookSubscription
        subscriptions = WebhookSubscription.objects.all()
        data = [{
            "id": str(sub.id),
            "url": sub.url,
            "event_types": sub.event_types,
            "is_active": sub.is_active,
            "created_at": sub.created_at.isoformat(),
        } for sub in subscriptions]
        return Response(data)


class WebhookSubscriptionCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.core.webhooks import WebhookSubscription
        import secrets
        
        url = request.data.get("url")
        event_types = request.data.get("event_types", [])
        secret = secrets.token_hex(32)
        
        subscription = WebhookSubscription.objects.create(
            url=url,
            event_types=event_types,
            secret=secret,
        )
        
        return Response({
            "id": str(subscription.id),
            "url": subscription.url,
            "event_types": subscription.event_types,
            "secret": secret,
        }, status=status.HTTP_201_CREATED)


class WebhookSubscriptionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from apps.core.webhooks import WebhookSubscription
        try:
            subscription = WebhookSubscription.objects.get(pk=pk)
            return Response({
                "id": str(subscription.id),
                "url": subscription.url,
                "event_types": subscription.event_types,
                "is_active": subscription.is_active,
                "created_at": subscription.created_at.isoformat(),
            })
        except WebhookSubscription.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        from apps.core.webhooks import WebhookSubscription
        try:
            subscription = WebhookSubscription.objects.get(pk=pk)
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except WebhookSubscription.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)


class WebhookDeliveryListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from apps.core.webhooks import WebhookDelivery
        deliveries = WebhookDelivery.objects.filter(webhook_id=pk).order_by("-created_at")[:50]
        data = [{
            "id": str(d.id),
            "event_id": str(d.event_id),
            "event_type": d.event_type,
            "status_code": d.status_code,
            "is_success": d.is_success,
            "created_at": d.created_at.isoformat(),
            "delivered_at": d.delivered_at.isoformat() if d.delivered_at else None,
        } for d in deliveries]
        return Response(data)


def publish_sse_event(channel: str, event_type: str, data: dict):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"sse_{channel}",
        {
            "type": "sse.message",
            "event_type": event_type,
            "data": data,
        }
    )


async def publish_sse_event_async(channel: str, event_type: str, data: dict):
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        f"sse_{channel}",
        {
            "type": "sse.message",
            "event_type": event_type,
            "data": data,
        }
    )
