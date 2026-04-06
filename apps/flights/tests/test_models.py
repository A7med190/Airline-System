from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from apps.flights.models import Airport, Flight


class AirportModelTest(TestCase):
    def test_create_airport(self):
        airport = Airport.objects.create(
            code="JFK",
            name="John F. Kennedy International Airport",
            city="New York",
            country="USA",
        )
        self.assertEqual(airport.code, "JFK")
        self.assertEqual(str(airport), "JFK - John F. Kennedy International Airport, New York")

    def test_code_uppercase(self):
        airport = Airport.objects.create(
            code="jfk",
            name="JFK Airport",
            city="New York",
            country="USA",
        )
        self.assertEqual(airport.code, "JFK")

    def test_unique_code(self):
        Airport.objects.create(code="LAX", name="LAX", city="Los Angeles", country="USA")
        with self.assertRaises(Exception):
            Airport.objects.create(code="LAX", name="Another LAX", city="LA", country="USA")


class FlightModelTest(TestCase):
    def setUp(self):
        self.departure = Airport.objects.create(code="JFK", name="JFK", city="New York", country="USA")
        self.arrival = Airport.objects.create(code="LAX", name="LAX", city="Los Angeles", country="USA")
        self.departure_time = timezone.now() + timedelta(days=7)
        self.arrival_time = self.departure_time + timedelta(hours=5, minutes=30)

    def test_create_flight(self):
        flight = Flight.objects.create(
            flight_number="AA100",
            departure_airport=self.departure,
            arrival_airport=self.arrival,
            departure_time=self.departure_time,
            arrival_time=self.arrival_time,
            price=299.99,
            total_seats=180,
        )
        self.assertEqual(flight.available_seats, 180)
        self.assertEqual(flight.flight_duration, "5h 30m")

    def test_flight_auto_available_seats(self):
        flight = Flight.objects.create(
            flight_number="AA101",
            departure_airport=self.departure,
            arrival_airport=self.arrival,
            departure_time=self.departure_time,
            arrival_time=self.arrival_time,
            price=199.99,
        )
        self.assertEqual(flight.available_seats, 180)

    def test_flight_custom_seats(self):
        flight = Flight.objects.create(
            flight_number="AA102",
            departure_airport=self.departure,
            arrival_airport=self.arrival,
            departure_time=self.departure_time,
            arrival_time=self.arrival_time,
            price=399.99,
            total_seats=250,
            available_seats=200,
        )
        self.assertEqual(flight.available_seats, 200)

    def test_str_representation(self):
        flight = Flight.objects.create(
            flight_number="AA100",
            departure_airport=self.departure,
            arrival_airport=self.arrival,
            departure_time=self.departure_time,
            arrival_time=self.arrival_time,
            price=299.99,
        )
        self.assertEqual(str(flight), "AA100: JFK -> LAX")
