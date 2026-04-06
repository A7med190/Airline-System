from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class CustomUserModelTest(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )
        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.loyalty_points_balance, 0)

    def test_create_superuser(self):
        user = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass123",
            first_name="Admin",
            last_name="User",
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_email_required(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="testpass123", first_name="Test", last_name="User")

    def test_get_full_name(self):
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="John",
            last_name="Doe",
        )
        self.assertEqual(user.get_full_name(), "John Doe")

    def test_str_representation(self):
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="John",
            last_name="Doe",
        )
        self.assertEqual(str(user), "John Doe (test@example.com)")

    def test_unique_email(self):
        User.objects.create_user(
            email="unique@example.com",
            password="testpass123",
            first_name="First",
            last_name="User",
        )
        with self.assertRaises(Exception):
            User.objects.create_user(
                email="unique@example.com",
                password="testpass123",
                first_name="Second",
                last_name="User",
            )
