from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.accounts.models import CustomUser
from apps.flights.models import Airport, Flight
from apps.bookings.models import Booking
from faker import Faker
import random
from datetime import datetime, timedelta

User = get_user_model()
fake = Faker()


class Command(BaseCommand):
    help = 'Seed database with sample data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding Airline database...')

        # Create admin
        if not User.objects.filter(email='admin@airline.com').exists():
            User.objects.create_superuser(
                email='admin@airline.com',
                password='admin123',
                first_name='Admin',
                last_name='User'
            )

        # Create test users
        for i in range(5):
            email = f'user{i+1}@example.com'
            if not User.objects.filter(email=email).exists():
                User.objects.create_user(
                    email=email,
                    password='password123',
                    first_name=fake.first_name(),
                    last_name=fake.last_name()
                )

        # Create airports
        airports_data = [
            ('JFK', 'New York', 'USA'),
            ('LAX', 'Los Angeles', 'USA'),
            ('LHR', 'London', 'UK'),
            ('CDG', 'Paris', 'France'),
            ('DXB', 'Dubai', 'UAE'),
            ('SIN', 'Singapore', 'Singapore'),
            ('HND', 'Tokyo', 'Japan'),
            ('SYD', 'Sydney', 'Australia'),
        ]

        for code, city, country in airports_data:
            Airport.objects.get_or_create(
                code=code,
                defaults={
                    'name': f'{city} International Airport',
                    'city': city,
                    'country': country
                }
            )

        # Create flights
        airports = Airport.objects.all()
        for i in range(10):
            origin = random.choice(airports)
            destination = random.choice([a for a in airports if a != origin])
            departure = datetime.now() + timedelta(days=random.randint(1, 30))
            
            Flight.objects.get_or_create(
                flight_number=f'FL{random.randint(100, 999)}',
                defaults={
                    'origin': origin,
                    'destination': destination,
                    'departure_time': departure,
                    'arrival_time': departure + timedelta(hours=random.randint(2, 15)),
                    'price': round(random.uniform(100, 1000), 2),
                    'available_seats': random.randint(50, 200)
                }
            )

        self.stdout.write(self.style.SUCCESS('Successfully seeded Airline database!'))