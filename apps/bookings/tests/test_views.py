from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.flights.models import Airport, Flight
from apps.bookings.models import Booking, Payment

User = get_user_model()


class BookingViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="user@example.com", password="userpass123", first_name="Test", last_name="User"
        )
        self.other_user = User.objects.create_user(
            email="other@example.com", password="otherpass123", first_name="Other", last_name="User"
        )
        self.departure = Airport.objects.create(code="JFK", name="JFK", city="New York", country="USA")
        self.arrival = Airport.objects.create(code="LAX", name="LAX", city="Los Angeles", country="USA")
        self.flight = Flight.objects.create(
            flight_number="AA100",
            departure_airport=self.departure,
            arrival_airport=self.arrival,
            departure_time=timezone.now() + timedelta(days=7),
            arrival_time=timezone.now() + timedelta(days=7, hours=5),
            price=299.99,
        )
        self.list_url = reverse("booking-list")

    def test_create_booking(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.list_url, {"flight": self.flight.pk}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["seat_number"], "1A")
        self.flight.refresh_from_db()
        self.assertEqual(self.flight.available_seats, 179)

    def test_create_booking_unauthenticated(self):
        response = self.client.post(self.list_url, {"flight": self.flight.pk}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_booking_no_seats(self):
        self.flight.available_seats = 0
        self.flight.save()
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.list_url, {"flight": self.flight.pk}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_own_bookings(self):
        Booking.objects.create(user=self.user, flight=self.flight, seat_number="1A", total_price=299.99)
        Booking.objects.create(user=self.other_user, flight=self.flight, seat_number="1B", total_price=299.99)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)

    def test_retrieve_own_booking(self):
        booking = Booking.objects.create(user=self.user, flight=self.flight, seat_number="1A", total_price=299.99)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("booking-detail", kwargs={"pk": booking.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["seat_number"], "1A")

    def test_cannot_retrieve_other_booking(self):
        booking = Booking.objects.create(user=self.other_user, flight=self.flight, seat_number="1B", total_price=299.99)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("booking-detail", kwargs={"pk": booking.pk}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cancel_booking_full_refund(self):
        booking = Booking.objects.create(user=self.user, flight=self.flight, seat_number="1A", total_price=299.99)
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse("booking-cancel", kwargs={"pk": booking.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CANCELLED)
        self.flight.refresh_from_db()
        self.assertEqual(self.flight.available_seats, 180)

    def test_cancel_already_cancelled(self):
        booking = Booking.objects.create(
            user=self.user, flight=self.flight, seat_number="1A", total_price=299.99, status=Booking.Status.CANCELLED
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse("booking-cancel", kwargs={"pk": booking.pk}))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancel_completed_booking(self):
        booking = Booking.objects.create(
            user=self.user, flight=self.flight, seat_number="1A", total_price=299.99, status=Booking.Status.COMPLETED
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse("booking-cancel", kwargs={"pk": booking.pk}))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class PaymentViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="user@example.com", password="userpass123", first_name="Test", last_name="User"
        )
        self.departure = Airport.objects.create(code="JFK", name="JFK", city="New York", country="USA")
        self.arrival = Airport.objects.create(code="LAX", name="LAX", city="Los Angeles", country="USA")
        self.flight = Flight.objects.create(
            flight_number="AA100",
            departure_airport=self.departure,
            arrival_airport=self.arrival,
            departure_time=timezone.now() + timedelta(days=7),
            arrival_time=timezone.now() + timedelta(days=7, hours=5),
            price=299.99,
        )
        self.booking = Booking.objects.create(
            user=self.user, flight=self.flight, seat_number="1A", total_price=299.99
        )
        self.create_url = reverse("payment-create")

    def test_create_payment(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.create_url, {
            "booking": self.booking.pk,
            "amount": "299.99",
            "payment_method": "credit_card",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.COMPLETED)

    def test_cannot_pay_for_other_user_booking(self):
        other_user = User.objects.create_user(email="other@example.com", password="other123", first_name="Other", last_name="User")
        other_booking = Booking.objects.create(user=other_user, flight=self.flight, seat_number="1B", total_price=299.99)
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.create_url, {
            "booking": other_booking.pk,
            "amount": "299.99",
            "payment_method": "credit_card",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_pay_wrong_amount(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.create_url, {
            "booking": self.booking.pk,
            "amount": "100.00",
            "payment_method": "credit_card",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_pay_already_paid(self):
        Payment.objects.create(
            booking=self.booking, amount=299.99, payment_method=Payment.PaymentMethod.CREDIT_CARD,
            status=Payment.PaymentStatus.COMPLETED, transaction_id="TXN-TEST1"
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.create_url, {
            "booking": self.booking.pk,
            "amount": "299.99",
            "payment_method": "credit_card",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_earns_loyalty_points_after_payment(self):
        self.client.force_authenticate(user=self.user)
        self.client.post(self.create_url, {
            "booking": self.booking.pk,
            "amount": "299.99",
            "payment_method": "credit_card",
        }, format="json")
        self.user.refresh_from_db()
        self.assertEqual(self.user.loyalty_points_balance, 29)
