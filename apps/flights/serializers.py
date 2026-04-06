from rest_framework import serializers
from .models import Airport, Flight


class AirportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Airport
        fields = ("id", "code", "name", "city", "country")
        read_only_fields = ("id",)


class FlightSerializer(serializers.ModelSerializer):
    departure_airport_info = AirportSerializer(source="departure_airport", read_only=True)
    arrival_airport_info = AirportSerializer(source="arrival_airport", read_only=True)
    departure_airport = serializers.PrimaryKeyRelatedField(queryset=Airport.objects.all(), write_only=True)
    arrival_airport = serializers.PrimaryKeyRelatedField(queryset=Airport.objects.all(), write_only=True)
    flight_duration = serializers.ReadOnlyField()

    class Meta:
        model = Flight
        fields = (
            "id", "flight_number", "departure_airport", "arrival_airport",
            "departure_airport_info", "arrival_airport_info",
            "departure_time", "arrival_time", "price",
            "total_seats", "available_seats", "flight_duration",
        )
        read_only_fields = ("id", "available_seats")

    def validate(self, data):
        if data["arrival_time"] <= data["departure_time"]:
            raise serializers.ValidationError({"arrival_time": "Arrival time must be after departure time."})
        return data
