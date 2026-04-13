from django.urls import path

from .views import SSEView

sse_urls = [
    path("", SSEView.as_view(), name="sse-stream"),
]

urlpatterns = sse_urls