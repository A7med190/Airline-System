import asyncio
import json
from typing import Optional

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = "notifications"
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        event_type = data.get("event_type", "ping")
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "notification_message",
                "event_type": event_type,
                "data": data.get("data", {}),
            }
        )

    async def notification_message(self, event):
        await self.send(text_data=json.dumps({
            "event_type": event["event_type"],
            "data": event["data"],
        }))


class BookingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")
        self.room_group_name = "bookings"
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        await self.send(text_data=json.dumps({
            "type": "connection_established",
            "message": "Connected to booking notifications",
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get("type")
        
        if message_type == "ping":
            await self.send(text_data=json.dumps({"type": "pong"}))

    async def booking_created(self, event):
        if self.user and str(self.user.id) == str(event.get("user_id")):
            await self.send(text_data=json.dumps({
                "type": "booking_created",
                "booking_id": event.get("booking_id"),
                "data": event.get("data"),
            }))

    async def booking_updated(self, event):
        if self.user and str(self.user.id) == str(event.get("user_id")):
            await self.send(text_data=json.dumps({
                "type": "booking_updated",
                "booking_id": event.get("booking_id"),
                "data": event.get("data"),
            }))

    async def booking_cancelled(self, event):
        if self.user and str(self.user.id) == str(event.get("user_id")):
            await self.send(text_data=json.dumps({
                "type": "booking_cancelled",
                "booking_id": event.get("booking_id"),
                "data": event.get("data"),
            }))


class FlightConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.flight_id = self.scope["url_route"]["kwargs"].get("flight_id")
        self.room_group_name = f"flights_{self.flight_id}" if self.flight_id else "flights"
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def flight_delay(self, event):
        await self.send(text_data=json.dumps({
            "type": "flight_delay",
            "flight_id": event.get("flight_id"),
            "delay_minutes": event.get("delay_minutes"),
            "new_departure_time": event.get("new_departure_time"),
        }))

    async def flight_status_change(self, event):
        await self.send(text_data=json.dumps({
            "type": "flight_status_change",
            "flight_id": event.get("flight_id"),
            "status": event.get("status"),
        }))


class SSEConsumer:
    pass
