# Mini Airline Booking System with Loyalty Points

A REST API built with Django REST Framework for managing airline bookings with an integrated loyalty points system.

## Features

- User registration and JWT authentication
- Flight search with filters (origin, destination, date, price range)
- Booking management with automatic seat assignment
- Loyalty points earning and redemption
- Payment processing simulation
- Booking cancellation with refund logic
- Role-based access control (admin vs user)
- Swagger/OpenAPI documentation

## Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL

### Setup

```powershell
# 1. Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create PostgreSQL database
#    psql -U postgres
#    CREATE DATABASE airline_db;

# 4. Configure environment variables (edit .env with your DB credentials)

# 5. Run migrations
python manage.py makemigrations
python manage.py migrate

# 6. Seed sample data
python manage.py seed_data

# 7. Run server
python manage.py runserver
```

## API Documentation

After starting the server:
- **Swagger UI:** http://localhost:8000/api/schema/swagger-ui/
- **ReDoc:** http://localhost:8000/api/schema/redoc/

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register/` | Register new user |
| POST | `/api/auth/login/` | Login (returns JWT tokens) |
| POST | `/api/auth/logout/` | Logout (blacklist refresh token) |
| GET | `/api/auth/me/` | Get current user profile |

### Flights
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/flights/airports/` | No | List all airports |
| GET | `/api/flights/airports/{id}/` | No | Airport detail |
| GET | `/api/flights/` | No | List flights (filterable) |
| GET | `/api/flights/{id}/` | No | Flight detail |
| POST | `/api/flights/` | Admin | Create flight |
| PUT | `/api/flights/{id}/` | Admin | Update flight |
| DELETE | `/api/flights/{id}/` | Admin | Delete flight |

### Bookings
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/bookings/` | Yes | List user's bookings |
| POST | `/api/bookings/` | Yes | Create booking |
| GET | `/api/bookings/{id}/` | Yes | Booking detail |
| POST | `/api/bookings/{id}/cancel/` | Yes | Cancel booking |

### Payments
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/bookings/payments/` | Yes | Process payment |
| GET | `/api/bookings/payments/{id}/` | Yes | Payment detail |

### Loyalty
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/loyalty/balance/` | Yes | Current points balance |
| GET | `/api/loyalty/transactions/` | Yes | Points history |
| POST | `/api/loyalty/redeem/` | Yes | Redeem points |

## Business Rules

### Loyalty Points
- **Earning:** 1 point per $10 spent on bookings
- **Redemption:** 100 points = $10 discount
- **Minimum redemption:** 100 points (in multiples of 100)
- **Maximum discount:** 50% of booking price

### Cancellation Refunds
- **>24 hours before departure:** 100% refund
- **<24 hours before departure:** 50% refund
- Loyalty points used are refunded on cancellation

### Seat Assignment
- Automatic seat assignment on booking (format: 1A, 1B, 1C...)
- 30 rows x 6 seats per row (180 total)

## Testing

```powershell
python manage.py test
```

## Default Credentials (after seeding)

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@airline.com | admin123 |
| User | john@example.com | user123 |
| User | jane@example.com | user123 |

## Project Structure

```
airline_system/
├── config/              # Django settings, URLs
├── apps/
│   ├── core/            # Shared utilities (permissions, pagination, exceptions)
│   ├── accounts/        # Custom user model, auth endpoints
│   ├── flights/         # Airport, Flight models and endpoints
│   ├── bookings/        # Booking, Payment models and endpoints
│   └── loyalty/         # Loyalty points system
└── tests/               # Integration tests
```
