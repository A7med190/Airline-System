from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.loyalty.models import LoyaltyTransaction

User = get_user_model()


class LoyaltyViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="user@example.com", password="userpass123", first_name="Test", last_name="User", loyalty_points_balance=500
        )
        self.balance_url = reverse("loyalty-balance")
        self.transactions_url = reverse("loyalty-transactions")
        self.redeem_url = reverse("loyalty-redeem")

    def test_get_balance(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.balance_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["balance"], 500)

    def test_get_balance_unauthenticated(self):
        response = self.client.get(self.balance_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_transactions(self):
        LoyaltyTransaction.objects.create(user=self.user, points=500, transaction_type=LoyaltyTransaction.TransactionType.EARNED, reference="Initial")
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.transactions_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)

    def test_redeem_points_success(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.redeem_url, {"points": 200}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.user.refresh_from_db()
        self.assertEqual(self.user.loyalty_points_balance, 300)

    def test_redeem_insufficient_points(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.redeem_url, {"points": 600}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_redeem_below_minimum(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.redeem_url, {"points": 50}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_redeem_not_multiple_of_100(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.redeem_url, {"points": 150}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_redeem_unauthenticated(self):
        response = self.client.post(self.redeem_url, {"points": 100}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
