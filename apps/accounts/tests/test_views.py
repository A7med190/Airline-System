from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()


class AuthViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse("register")
        self.login_url = reverse("login")
        self.logout_url = reverse("logout")
        self.me_url = reverse("me")
        self.user_data = {
            "email": "test@example.com",
            "password": "testpass123",
            "password_confirm": "testpass123",
            "first_name": "Test",
            "last_name": "User",
        }

    def test_register_success(self):
        response = self.client.post(self.register_url, self.user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertIn("access_token", response.data["data"])
        self.assertIn("refresh_token", response.data["data"])
        self.assertEqual(User.objects.count(), 1)

    def test_register_password_mismatch(self):
        data = self.user_data.copy()
        data["password_confirm"] = "differentpass"
        response = self.client.post(self.register_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_email(self):
        self.client.post(self.register_url, self.user_data, format="json")
        response = self.client.post(self.register_url, self.user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_short_password(self):
        data = self.user_data.copy()
        data["password"] = "short"
        data["password_confirm"] = "short"
        response = self.client.post(self.register_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_success(self):
        self.client.post(self.register_url, self.user_data, format="json")
        response = self.client.post(self.login_url, {
            "email": self.user_data["email"],
            "password": self.user_data["password"],
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIn("access_token", response.data["data"])

    def test_login_invalid_credentials(self):
        response = self.client.post(self.login_url, {
            "email": "wrong@example.com",
            "password": "wrongpass",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_missing_fields(self):
        response = self.client.post(self.login_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_me_authenticated(self):
        register_response = self.client.post(self.register_url, self.user_data, format="json")
        token = register_response.data["data"]["access_token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["email"], self.user_data["email"])

    def test_me_unauthenticated(self):
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_success(self):
        register_response = self.client.post(self.register_url, self.user_data, format="json")
        refresh_token = register_response.data["data"]["refresh_token"]
        response = self.client.post(self.logout_url, {"refresh_token": refresh_token}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_logout_missing_token(self):
        self.client.post(self.register_url, self.user_data, format="json")
        login_response = self.client.post(self.login_url, {
            "email": self.user_data["email"],
            "password": self.user_data["password"],
        }, format="json")
        token = login_response.data["data"]["access_token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.post(self.logout_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
