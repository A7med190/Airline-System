from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.flights.models import Airport, Flight

User = get_user_model()


class FlightViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email="admin@example.com", password="adminpass123", first_name="Admin", last_name="User"
        )
        self.user = User.objects.create_user(
            email="user@example.com", password="userpass123", first_name="Regular", last_name="User"
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
        self.list_url = reverse("flight-list")

    def test_list_flights_unauthenticated(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_flights_with_available_seats(self):
        Flight.objects.create(
            flight_number="AA101",
            departure_airport=self.departure,
            arrival_airport=self.arrival,
            departure_time=timezone.now() + timedelta(days=8),
            arrival_time=timezone.now() + timedelta(days=8, hours=6),
            price=399.99,
            available_seats=0,
        )
        response = self.client.get(self.list_url)
        self.assertEqual(len(response.data["data"]), 1)

    def test_retrieve_flight(self):
        response = self.client.get(reverse("flight-detail", kwargs={"pk": self.flight.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["flight_number"], "AA100")

    def test_admin_create_flight(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(self.list_url, {
            "flight_number": "AA200",
            "departure_airport": self.departure.pk,
            "arrival_airport": self.arrival.pk,
            "departure_time": (timezone.now() + timedelta(days=10)).isoformat(),
            "arrival_time": (timezone.now() + timedelta(days=10, hours=4)).isoformat(),
            "price": "499.99",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_user_cannot_create_flight(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.list_url, {
            "flight_number": "AA201",
            "departure_airport": self.departure.pk,
            "arrival_airport": self.arrival.pk,
            "departure_time": (timezone.now() + timedelta(days=10)).isoformat(),
            "arrival_time": (timezone.now() + timedelta(days=10, hours=4)).isoformat(),
            "price": "499.99",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_by_origin(self):
        response = self.client.get(self.list_url, {"origin": "JFK"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)

    def test_filter_by_destination(self):
        response = self.client.get(self.list_url, {"destination": "LAX"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_by_date(self):
        target_date = (timezone.now() + timedelta(days=7)).date().isoformat()
        response = self.client.get(self.list_url, {"date": target_date})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_cannot_delete(self):
        response = self.client.delete(reverse("flight-detail", kwargs={"pk": self.flight.pk}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AirportViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        Airport.objects.create(code="JFK", name="JFK", city="New York", country="USA")
        Airport.objects.create(code="LAX", name="LAX", city="Los Angeles", country="USA")
        self.list_url = reverse("airport-list")

    def test_list_airports_unauthenticated(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_search_airports(self):
        response = self.client.get(self.list_url, {"search": "New York"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
