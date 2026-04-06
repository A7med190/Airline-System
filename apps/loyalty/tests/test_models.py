from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.loyalty.models import LoyaltyTransaction

User = get_user_model()


class LoyaltyTransactionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123", first_name="Test", last_name="User"
        )

    def test_create_earned_transaction(self):
        tx = LoyaltyTransaction.objects.create(
            user=self.user, points=50, transaction_type=LoyaltyTransaction.TransactionType.EARNED, reference="Test booking"
        )
        self.assertEqual(tx.points, 50)
        self.assertEqual(tx.transaction_type, LoyaltyTransaction.TransactionType.EARNED)
        self.assertIn("+50", str(tx))

    def test_create_redeemed_transaction(self):
        tx = LoyaltyTransaction.objects.create(
            user=self.user, points=100, transaction_type=LoyaltyTransaction.TransactionType.REDEEMED, reference="Redeemed"
        )
        self.assertEqual(tx.points, 100)
        self.assertEqual(tx.transaction_type, LoyaltyTransaction.TransactionType.REDEEMED)
        self.assertIn("-100", str(tx))

    def test_ordering(self):
        tx1 = LoyaltyTransaction.objects.create(user=self.user, points=10, transaction_type=LoyaltyTransaction.TransactionType.EARNED)
        tx2 = LoyaltyTransaction.objects.create(user=self.user, points=20, transaction_type=LoyaltyTransaction.TransactionType.EARNED)
        transactions = LoyaltyTransaction.objects.all()
        self.assertEqual(transactions[0], tx2)
        self.assertEqual(transactions[1], tx1)
