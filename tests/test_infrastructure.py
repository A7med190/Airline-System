import pytest
from django.test import Client, TestCase
from django.contrib.auth import get_user_model
from apps.core.soft_delete import BaseSoftDeleteModel, IsDeletedManager
from apps.core.circuit_breaker import CircuitBreaker, CircuitBreakerRegistry, circuit_breaker
from apps.core.idempotency import IdempotencyService
from apps.core.webhooks import OutboxMessage, WebhookSubscription, WebhookService
from apps.core.services import BookingService, PaymentService, ServiceResult
from unittest.mock import Mock, patch


User = get_user_model()


class TestSoftDeleteModel(TestCase):
    def setUp(self):
        from django.db import models
        
        class TestModel(BaseSoftDeleteModel):
            name = models.CharField(max_length=100)
            
            class Meta:
                app_label = 'core'

        self.TestModel = TestModel

    def test_soft_delete(self):
        obj = self.TestModel(name="test")
        obj.save()
        
        self.assertFalse(obj.is_deleted)
        obj.soft_delete()
        
        self.assertTrue(obj.is_deleted)
        self.assertIsNotNone(obj.deleted_at)
        
        self.assertEqual(self.TestModel.objects.count(), 0)
        self.assertEqual(self.TestModel.all_objects.count(), 1)

    def test_restore(self):
        obj = self.TestModel(name="test")
        obj.save()
        obj.soft_delete()
        
        obj.restore()
        
        self.assertFalse(obj.is_deleted)
        self.assertIsNone(obj.deleted_at)
        self.assertEqual(self.TestModel.objects.count(), 1)


class TestCircuitBreaker(TestCase):
    def test_closed_state_initially(self):
        breaker = CircuitBreaker(failure_threshold=3)
        self.assertEqual(breaker.state, CircuitBreaker.CLOSED)

    def test_opens_after_threshold(self):
        breaker = CircuitBreaker(failure_threshold=2)
        
        for _ in range(2):
            with self.assertRaises(Exception):
                breaker.call(lambda: (_ for _ in ()).throw(Exception("fail")))
        
        self.assertEqual(breaker.state, CircuitBreaker.OPEN)

    def test_successful_call_resets(self):
        breaker = CircuitBreaker(failure_threshold=2)
        breaker.call(lambda: "success")
        
        breaker.record_failure()
        breaker.record_failure()
        
        breaker.call(lambda: "success")
        self.assertEqual(breaker.failure_count, 0)

    def test_circuit_breaker_decorator(self):
        @circuit_breaker(name="test_decorator")
        def failing_function():
            raise Exception("fail")

        with patch.object(CircuitBreakerRegistry, 'get') as mock_get:
            mock_breaker = CircuitBreaker()
            mock_get.return_value = mock_breaker
            
            failing_function()
            
            self.assertTrue(mock_get.called)


class TestIdempotencyService(TestCase):
    def setUp(self):
        self.service = IdempotencyService()

    def test_set_and_get(self):
        self.service.set("test-key", {"status": "completed"})
        result = self.service.get("test-key")
        
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "completed")

    def test_processing_status(self):
        self.service.set_processing("test-key")
        self.assertTrue(self.service.is_processing("test-key"))

    def test_completed_status(self):
        self.service.set_completed("test-key", {"data": "value"})
        self.assertTrue(self.service.is_completed("test-key"))

    def test_delete(self):
        self.service.set("test-key", {"data": "value"})
        self.service.delete("test-key")
        self.assertIsNone(self.service.get("test-key"))


class TestWebhookService(TestCase):
    def test_publish_event_creates_outbox_message(self):
        service = WebhookService()
        service.publish_event("test.event", {"key": "value"})
        
        message = OutboxMessage.objects.filter(event_type="test.event").first()
        self.assertIsNotNone(message)
        self.assertEqual(message.payload["event_type"], "test.event")

    def test_create_payload(self):
        service = WebhookService()
        payload = service.create_payload("test.event", {"key": "value"})
        
        self.assertEqual(payload.event_type, "test.event")
        self.assertIsNotNone(payload.event_id)
        self.assertIsNotNone(payload.timestamp)


class TestServiceResult(TestCase):
    def test_success_result(self):
        result = ServiceResult(data={"key": "value"})
        
        self.assertTrue(result.is_success)
        self.assertFalse(result.is_failure)
        self.assertEqual(result.data, {"key": "value"})

    def test_failure_result(self):
        result = ServiceResult(error="Something went wrong")
        
        self.assertFalse(result.is_success)
        self.assertTrue(result.is_failure)
        self.assertEqual(result.error, "Something went wrong")


class TestBookingService(TestCase):
    def setUp(self):
        from apps.flights.models import Airport, Flight
        from django.utils import timezone
        from datetime import timedelta
        
        self.departure = Airport.objects.create(code="JFK", name="JFK", city="New York", country="USA")
        self.arrival = Airport.objects.create(code="LAX", name="LAX", city="Los Angeles", country="USA")
        self.flight = Flight.objects.create(
            flight_number="TEST001",
            departure_airport=self.departure,
            arrival_airport=self.arrival,
            departure_time=timezone.now() + timedelta(days=7),
            arrival_time=timezone.now() + timedelta(days=7, hours=5),
            price=300.00,
            total_seats=100,
            available_seats=50,
        )
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )

    def test_create_booking_success(self):
        service = BookingService()
        result = service.create_booking(self.user, self.flight)
        
        self.assertTrue(result.is_success)
        self.flight.refresh_from_db()
        self.assertEqual(self.flight.available_seats, 49)

    def test_create_booking_no_seats(self):
        self.flight.available_seats = 0
        self.flight.save()
        
        service = BookingService()
        result = service.create_booking(self.user, self.flight)
        
        self.assertTrue(result.is_failure)


@pytest.mark.django_db
class TestHealthCheckEndpoints:
    def test_health_check_endpoint(self):
        client = Client()
        response = client.get("/health/")
        assert response.status_code == 200

    def test_database_health_check(self):
        client = Client()
        response = client.get("/health/db/")
        assert response.status_code == 200
