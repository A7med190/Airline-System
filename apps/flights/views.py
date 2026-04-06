from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from apps.core.permissions import IsAdminOrReadOnly
from .models import Airport, Flight
from .serializers import AirportSerializer, FlightSerializer
from .filters import FlightFilter


class AirportViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Airport.objects.all()
    serializer_class = AirportSerializer
    permission_classes = [AllowAny]
    search_fields = ["code", "name", "city", "country"]


class FlightViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]
    serializer_class = FlightSerializer
    filterset_class = FlightFilter
    search_fields = ["flight_number"]
    ordering_fields = ["departure_time", "price", "available_seats"]

    def get_queryset(self):
        return Flight.objects.filter(available_seats__gt=0).select_related(
            "departure_airport", "arrival_airport"
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"success": True, "data": serializer.data})

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"success": True, "data": serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response({"success": True, "message": "Flight created", "data": FlightSerializer(instance).data}, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"success": True, "message": "Flight updated", "data": serializer.data})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"success": True, "message": "Flight deleted"})
