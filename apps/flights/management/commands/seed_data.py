from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from apps.flights.models import Airport, Flight
from apps.bookings.models import Booking, Payment
from apps.loyalty.models import LoyaltyTransaction

User = get_user_model()


class Command(BaseCommand):
    help = "Seed the database with sample data for development"

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("Seeding database..."))

        if User.objects.filter(email="admin@airline.com").exists():
            self.stdout.write(self.style.WARNING("Data already seeded. Skipping."))
            return

        admin = User.objects.create_superuser(
            email="admin@airline.com",
            password="admin123",
            first_name="Admin",
            last_name="User",
        )
        self.stdout.write(f"Created admin: {admin.email}")

        user1 = User.objects.create_user(
            email="john@example.com",
            password="user123",
            first_name="John",
            last_name="Doe",
            phone="+1234567890",
            loyalty_points_balance=250,
        )
        user2 = User.objects.create_user(
            email="jane@example.com",
            password="user123",
            first_name="Jane",
            last_name="Smith",
            phone="+0987654321",
            loyalty_points_balance=100,
        )
        self.stdout.write(f"Created users: {user1.email}, {user2.email}")

        airports_data = [
            ("JFK", "John F. Kennedy International Airport", "New York", "USA"),
            ("LAX", "Los Angeles International Airport", "Los Angeles", "USA"),
            ("ORD", "O'Hare International Airport", "Chicago", "USA"),
            ("DFW", "Dallas/Fort Worth International Airport", "Dallas", "USA"),
            ("DEN", "Denver International Airport", "Denver", "USA"),
            ("SFO", "San Francisco International Airport", "San Francisco", "USA"),
            ("SEA", "Seattle-Tacoma International Airport", "Seattle", "USA"),
            ("LAS", "Harry Reid International Airport", "Las Vegas", "USA"),
            ("MIA", "Miami International Airport", "Miami", "USA"),
            ("ATL", "Hartsfield-Jackson Atlanta International Airport", "Atlanta", "USA"),
        ]

        airports = {}
        for code, name, city, country in airports_data:
            airport = Airport.objects.create(code=code, name=name, city=city, country=country)
            airports[code] = airport
        self.stdout.write(f"Created {len(airports)} airports")

        routes = [
            ("JFK", "LAX", 299.99, 5, 30),
            ("LAX", "JFK", 319.99, 5, 30),
            ("JFK", "ORD", 199.99, 2, 45),
            ("ORD", "JFK", 209.99, 2, 45),
            ("DFW", "DEN", 149.99, 2, 0),
            ("DEN", "DFW", 159.99, 2, 0),
            ("SFO", "SEA", 129.99, 2, 15),
            ("SEA", "SFO", 139.99, 2, 15),
            ("LAS", "MIA", 249.99, 4, 30),
            ("MIA", "LAS", 259.99, 4, 30),
            ("ATL", "LAX", 279.99, 4, 45),
            ("LAX", "ATL", 289.99, 4, 45),
            ("JFK", "SFO", 349.99, 6, 0),
            ("SFO", "JFK", 359.99, 6, 0),
            ("ORD", "DEN", 169.99, 2, 30),
            ("DEN", "ORD", 179.99, 2, 30),
            ("DFW", "MIA", 189.99, 2, 45),
            ("MIA", "DFW", 199.99, 2, 45),
            ("SEA", "LAS", 159.99, 2, 30),
            ("LAS", "SEA", 169.99, 2, 30),
        ]

        flights = []
        for i, (dep, arr, price, hours, minutes) in enumerate(routes):
            dep_time = timezone.now() + timedelta(days=3 + (i % 14), hours=i % 12)
            arr_time = dep_time + timedelta(hours=hours, minutes=minutes)
            flight = Flight.objects.create(
                flight_number=f"AA{1000 + i}",
                departure_airport=airports[dep],
                arrival_airport=airports[arr],
                departure_time=dep_time,
                arrival_time=arr_time,
                price=price,
                total_seats=180,
            )
            flights.append(flight)
        self.stdout.write(f"Created {len(flights)} flights")

        booking1 = Booking.objects.create(
            user=user1, flight=flights[0], seat_number="1A", total_price=299.99
        )
        Payment.objects.create(
            booking=booking1, amount=299.99, payment_method=Payment.PaymentMethod.CREDIT_CARD,
            status=Payment.PaymentStatus.COMPLETED, transaction_id="TXN-SEED001"
        )
        LoyaltyTransaction.objects.create(
            user=user1, points=250, transaction_type=LoyaltyTransaction.TransactionType.EARNED,
            reference="Initial bonus points"
        )

        booking2 = Booking.objects.create(
            user=user2, flight=flights[2], seat_number="2C", total_price=199.99
        )
        Payment.objects.create(
            booking=booking2, amount=199.99, payment_method=Payment.PaymentMethod.PAYPAL,
            status=Payment.PaymentStatus.COMPLETED, transaction_id="TXN-SEED002"
        )
        LoyaltyTransaction.objects.create(
            user=user2, points=100, transaction_type=LoyaltyTransaction.TransactionType.EARNED,
            reference="Initial bonus points"
        )

        self.stdout.write(self.style.SUCCESS("Seeding complete!"))
        self.stdout.write(self.style.SUCCESS("\nCredentials:"))
        self.stdout.write(f"  Admin: {admin.email} / admin123")
        self.stdout.write(f"  User1: {user1.email} / user123")
        self.stdout.write(f"  User2: {user2.email} / user123")
        self.stdout.write(self.style.SUCCESS(f"\nSwagger UI: http://localhost:8000/api/schema/swagger-ui/"))
