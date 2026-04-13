from django.urls import path

from .views import (
    SSEView,
    WebhookSubscriptionListView,
    WebhookSubscriptionCreateView,
    WebhookSubscriptionDetailView,
    WebhookDeliveryListView,
)

sse_urls = [
    path("sse/", SSEView.as_view(), name="sse-stream"),
]

webhook_urls = [
    path("subscriptions/", WebhookSubscriptionListView.as_view(), name="webhook-subscription-list"),
    path("subscriptions/create/", WebhookSubscriptionCreateView.as_view(), name="webhook-subscription-create"),
    path("subscriptions/<uuid:pk>/", WebhookSubscriptionDetailView.as_view(), name="webhook-subscription-detail"),
    path("subscriptions/<uuid:pk>/deliveries/", WebhookDeliveryListView.as_view(), name="webhook-deliveries"),
    path("test/", WebhookSubscriptionCreateView.as_view(), name="webhook-test"),
]

urlpatterns = webhook_urls