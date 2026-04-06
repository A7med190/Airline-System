from django.urls import path
from .views import BookingViewSet, PaymentViewSet, PaymentCreateView

urlpatterns = [
    path("", BookingViewSet.as_view({"get": "list", "post": "create"}), name="booking-list"),
    path("<int:pk>/", BookingViewSet.as_view({"get": "retrieve"}), name="booking-detail"),
    path("<int:pk>/cancel/", BookingViewSet.as_view({"post": "cancel"}), name="booking-cancel"),
    path("payments/", PaymentCreateView.as_view(), name="payment-create"),
    path("payments/<int:pk>/", PaymentViewSet.as_view({"get": "retrieve"}), name="payment-detail"),
]
