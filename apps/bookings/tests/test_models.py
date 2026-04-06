from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from apps.flights.models import Airport, Flight
from apps.bookings.models import Booking, Payment

User = get_user_model()


class BookingModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123", first_name="Test", last_name="User"
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

    def test_create_booking(self):
        booking = Booking.objects.create(
            user=self.user,
            flight=self.flight,
            seat_number="1A",
            total_price=299.99,
        )
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)
        self.assertEqual(booking.booking_reference, f"BKG-{booking.id:06d}")
        self.assertEqual(booking.loyalty_discount, 0)

    def test_booking_str(self):
        booking = Booking.objects.create(
            user=self.user, flight=self.flight, seat_number="1A", total_price=299.99
        )
        self.assertIn("AA100", str(booking))
        self.assertIn("test@example.com", str(booking))

    def test_booking_with_loyalty_discount(self):
        booking = Booking.objects.create(
            user=self.user, flight=self.flight, seat_number="1B", total_price=249.99, loyalty_discount=50.00
        )
        self.assertEqual(booking.loyalty_discount, 50.00)
        self.assertEqual(booking.total_price, 249.99)


class PaymentModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123", first_name="Test", last_name="User"
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

    def test_create_payment(self):
        payment = Payment.objects.create(
            booking=self.booking,
            amount=299.99,
            payment_method=Payment.PaymentMethod.CREDIT_CARD,
            status=Payment.PaymentStatus.COMPLETED,
            transaction_id="TXN-TEST123",
        )
        self.assertEqual(payment.status, Payment.PaymentStatus.COMPLETED)
        self.assertEqual(payment.amount, 299.99)

    def test_payment_str(self):
        payment = Payment.objects.create(
            booking=self.booking, amount=299.99, payment_method=Payment.PaymentMethod.CREDIT_CARD, transaction_id="TXN-TEST123"
        )
        self.assertIn("TXN-TEST123", str(payment))

    def test_unique_transaction_id(self):
        Payment.objects.create(
            booking=self.booking, amount=299.99, payment_method=Payment.PaymentMethod.CREDIT_CARD, transaction_id="TXN-UNIQUE"
        )
        booking2 = Booking.objects.create(
            user=self.user, flight=self.flight, seat_number="1B", total_price=299.99
        )
        with self.assertRaises(Exception):
            Payment.objects.create(
                booking=booking2, amount=299.99, payment_method=Payment.PaymentMethod.CREDIT_CARD, transaction_id="TXN-UNIQUE"
            )
