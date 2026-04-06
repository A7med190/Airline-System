from django.urls import path
from .views import LoyaltyBalanceView, LoyaltyTransactionsView, RedeemPointsView

urlpatterns = [
    path("balance/", LoyaltyBalanceView.as_view(), name="loyalty-balance"),
    path("transactions/", LoyaltyTransactionsView.as_view(), name="loyalty-transactions"),
    path("redeem/", RedeemPointsView.as_view(), name="loyalty-redeem"),
]
