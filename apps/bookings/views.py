from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from apps.core.permissions import IsOwnerOrReadOnly
from .models import Booking, Payment
from .serializers import BookingCreateSerializer, BookingSerializer, PaymentSerializer
from apps.loyalty.services import refund_loyalty_points


class BookingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    serializer_class = BookingSerializer

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user).select_related("flight").order_by("-booking_date")

    def get_serializer_class(self):
        if self.action == "create":
            return BookingCreateSerializer
        return BookingSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"success": True, "data": serializer.data})

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"success": True, "data": serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()
        return Response({
            "success": True,
            "message": "Booking created successfully",
            "data": BookingSerializer(booking).data,
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        booking = self.get_object()

        if booking.status == Booking.Status.CANCELLED:
            return Response({"success": False, "error": "Booking is already cancelled."}, status=status.HTTP_400_BAD_REQUEST)

        if booking.status == Booking.Status.COMPLETED:
            return Response({"success": False, "error": "Cannot cancel a completed booking."}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        time_until_departure = booking.flight.departure_time - now
        hours_left = time_until_departure.total_seconds() / 3600

        refund_percentage = 1.0 if hours_left > 24 else 0.5
        refund_amount = booking.total_price * refund_percentage

        if hasattr(booking, "payment") and booking.payment.status == Payment.PaymentStatus.COMPLETED:
            booking.payment.status = Payment.PaymentStatus.REFUNDED
            booking.payment.save()

        if booking.loyalty_discount > 0:
            points_to_refund = int(booking.loyalty_discount / 10) * 100
            refund_loyalty_points(booking.user, points_to_refund, booking.booking_reference)

        booking.status = Booking.Status.CANCELLED
        booking.save()

        booking.flight.available_seats += 1
        booking.flight.save()

        return Response({
            "success": True,
            "message": f"Booking cancelled. Refund: ${refund_amount:.2f} ({refund_percentage*100:.0f}%)",
            "data": {
                "booking_reference": booking.booking_reference,
                "refund_amount": refund_amount,
                "refund_percentage": refund_percentage * 100,
            }
        })


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer

    def get_queryset(self):
        return Payment.objects.filter(booking__user=self.request.user).select_related("booking").order_by("-transaction_date")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"success": True, "data": serializer.data})


class PaymentCreateView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()
        return Response({
            "success": True,
            "message": "Payment processed successfully",
            "data": PaymentSerializer(payment).data,
        }, status=status.HTTP_201_CREATED)
