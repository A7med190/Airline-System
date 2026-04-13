import asyncio
import json
from typing import AsyncGenerator

from channels.generic.websocket import AsyncWebsocketConsumer


class SSEPublisher:
    _subscribers: dict = {}

    @classmethod
    async def subscribe(cls, channel: str, consumer: AsyncWebsocketConsumer):
        if channel not in cls._subscribers:
            cls._subscribers[channel] = []
        cls._subscribers[channel].append(consumer)

    @classmethod
    async def unsubscribe(cls, channel: str, consumer: AsyncWebsocketConsumer):
        if channel in cls._subscribers:
            cls._subscribers[channel].remove(consumer)

    @classmethod
    async def publish(cls, channel: str, event_type: str, data: dict):
        if channel in cls._subscribers:
            message = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
            for consumer in cls._subscribers[channel]:
                try:
                    await consumer.send(message)
                except Exception:
                    pass


class SSEStreamConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.channels = []
        await self.accept()

    async def disconnect(self, close_code):
        for channel in self.channels:
            await SSEPublisher.unsubscribe(channel, self)

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get("action")
        
        if action == "subscribe":
            channel = data.get("channel")
            self.channels.append(channel)
            await SSEPublisher.subscribe(channel, self)
            await self.send(text_data=json.dumps({
                "status": "subscribed",
                "channel": channel,
            }))
        
        elif action == "unsubscribe":
            channel = data.get("channel")
            if channel in self.channels:
                self.channels.remove(channel)
                await SSEPublisher.unsubscribe(channel, self)
                await self.send(text_data=json.dumps({
                    "status": "unsubscribed",
                    "channel": channel,
                }))
