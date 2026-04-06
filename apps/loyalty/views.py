from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from .models import LoyaltyTransaction
from .serializers import LoyaltyTransactionSerializer, RedeemSerializer
from .services import redeem_points, calculate_discount


class LoyaltyBalanceView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "success": True,
            "data": {
                "balance": user.loyalty_points_balance,
                "equivalent_discount": f"${calculate_discount(user.loyalty_points_balance):.2f}",
            }
        })


class LoyaltyTransactionsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LoyaltyTransactionSerializer

    def get_queryset(self):
        return LoyaltyTransaction.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"success": True, "data": serializer.data})


class RedeemPointsView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RedeemSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        points = serializer.validated_data["points"]
        discount = calculate_discount(points)

        with transaction.atomic():
            redeem_points(request.user, points)

        return Response({
            "success": True,
            "message": f"{points} points redeemed for ${discount:.2f} discount",
            "data": {
                "points_redeemed": points,
                "discount_value": discount,
                "new_balance": request.user.loyalty_points_balance,
            }
        }, status=status.HTTP_200_OK)
