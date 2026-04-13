from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/notifications/$", consumers.NotificationConsumer.as_asgi()),
    re_path(r"ws/bookings/$", consumers.BookingConsumer.as_asgi()),
    re_path(r"ws/flights/$", consumers.FlightConsumer.as_asgi()),
]
