from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.flights.models import Airport, Flight
from apps.bookings.models import Booking, Payment
from apps.loyalty.models import LoyaltyTransaction

User = get_user_model()


class FullBookingFlowIntegrationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.departure = Airport.objects.create(code="JFK", name="JFK", city="New York", country="USA")
        self.arrival = Airport.objects.create(code="LAX", name="LAX", city="Los Angeles", country="USA")
        self.flight = Flight.objects.create(
            flight_number="AA100",
            departure_airport=self.departure,
            arrival_airport=self.arrival,
            departure_time=timezone.now() + timedelta(days=7),
            arrival_time=timezone.now() + timedelta(days=7, hours=5),
            price=300.00,
        )

    def _register(self, email="user@example.com"):
        return self.client.post(reverse("register"), {
            "email": email,
            "password": "testpass123",
            "password_confirm": "testpass123",
            "first_name": "Test",
            "last_name": "User",
        }, format="json")

    def _login(self, email="user@example.com"):
        return self.client.post(reverse("login"), {
            "email": email,
            "password": "testpass123",
        }, format="json")

    def _authenticate(self, email="user@example.com"):
        reg = self._register(email)
        if reg.status_code == status.HTTP_201_CREATED:
            token = reg.data["data"]["access_token"]
        else:
            login = self._login(email)
            token = login.data["data"]["access_token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return User.objects.get(email=email)

    def test_full_booking_flow(self):
        user = self._authenticate()
        self.assertEqual(user.loyalty_points_balance, 0)

        response = self.client.get(reverse("flight-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)

        response = self.client.post(reverse("booking-list"), {"flight": self.flight.pk}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        booking_id = response.data["data"]["id"]
        self.assertEqual(response.data["data"]["seat_number"], "1A")
        self.assertEqual(response.data["data"]["total_price"], "300.00")

        self.flight.refresh_from_db()
        self.assertEqual(self.flight.available_seats, 179)

        response = self.client.post(reverse("payment-create"), {
            "booking": booking_id,
            "amount": "300.00",
            "payment_method": "credit_card",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user.refresh_from_db()
        self.assertEqual(user.loyalty_points_balance, 30)

        tx_count = LoyaltyTransaction.objects.filter(user=user).count()
        self.assertEqual(tx_count, 1)

    def test_booking_with_loyalty_redemption(self):
        user = self._authenticate()
        user.loyalty_points_balance = 500
        user.save()

        response = self.client.post(reverse("booking-list"), {
            "flight": self.flight.pk,
            "use_loyalty_points": 300,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        booking_id = response.data["data"]["id"]
        self.assertEqual(response.data["data"]["loyalty_discount"], "30.00")
        self.assertEqual(response.data["data"]["total_price"], "270.00")

        user.refresh_from_db()
        self.assertEqual(user.loyalty_points_balance, 200)

        response = self.client.post(reverse("payment-create"), {
            "booking": booking_id,
            "amount": "270.00",
            "payment_method": "credit_card",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user.refresh_from_db()
        self.assertEqual(user.loyalty_points_balance, 227)

    def test_booking_and_cancel_full_refund(self):
        user = self._authenticate()

        response = self.client.post(reverse("booking-list"), {"flight": self.flight.pk}, format="json")
        booking_id = response.data["data"]["id"]

        self.client.post(reverse("payment-create"), {
            "booking": booking_id,
            "amount": "300.00",
            "payment_method": "credit_card",
        }, format="json")

        user.refresh_from_db()
        self.assertEqual(user.loyalty_points_balance, 30)

        response = self.client.post(reverse("booking-cancel", kwargs={"pk": booking_id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Refund: $300.00 (100%)", response.data["message"])

        booking = Booking.objects.get(pk=booking_id)
        self.assertEqual(booking.status, Booking.Status.CANCELLED)

        payment = Payment.objects.get(booking=booking)
        self.assertEqual(payment.status, Payment.PaymentStatus.REFUNDED)

        self.flight.refresh_from_db()
        self.assertEqual(self.flight.available_seats, 180)

    def test_second_booking_uses_first_seat(self):
        user1 = self._authenticate("user1@example.com")
        user2 = self._authenticate("user2@example.com")

        self.client.post(reverse("booking-list"), {"flight": self.flight.pk}, format="json")

        self._authenticate("user2@example.com")
        response = self.client.post(reverse("booking-list"), {"flight": self.flight.pk}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["seat_number"], "1B")
