from rest_framework import serializers
from django.utils import timezone
from .models import Booking, Payment


class BookingCreateSerializer(serializers.ModelSerializer):
    use_loyalty_points = serializers.IntegerField(write_only=True, required=False, default=0)
    booking_reference = serializers.ReadOnlyField()

    class Meta:
        model = Booking
        fields = ("id", "flight", "seat_number", "booking_date", "status", "total_price", "loyalty_discount", "use_loyalty_points", "booking_reference")
        read_only_fields = ("id", "seat_number", "booking_date", "status", "total_price", "loyalty_discount", "booking_reference")

    def validate(self, data):
        flight = data["flight"]
        if flight.available_seats < 1:
            raise serializers.ValidationError({"flight": "No available seats on this flight."})
        if flight.departure_time <= timezone.now():
            raise serializers.ValidationError({"flight": "Cannot book a flight that has already departed."})
        return data

    def create(self, validated_data):
        from apps.loyalty.services import calculate_discount, redeem_points

        user = self.context["request"].user
        flight = validated_data["flight"]
        use_points = validated_data.pop("use_loyalty_points", 0)

        seat_number = self._assign_seat(flight)
        base_price = flight.price
        loyalty_discount = 0

        if use_points > 0:
            loyalty_discount = calculate_discount(use_points)
            max_discount = base_price * 0.5
            if loyalty_discount > max_discount:
                loyalty_discount = max_discount
            redeem_points(user, use_points)

        total_price = base_price - loyalty_discount
        if total_price < 0:
            total_price = 0

        flight.available_seats -= 1
        flight.save()

        booking = Booking.objects.create(
            user=user,
            flight=flight,
            seat_number=seat_number,
            total_price=total_price,
            loyalty_discount=loyalty_discount,
        )
        return booking

    def _assign_seat(self, flight):
        booked_seats = set(
            Booking.objects.filter(flight=flight, status=Booking.Status.CONFIRMED)
            .values_list("seat_number", flat=True)
        )
        rows = range(1, 31)
        cols = ["A", "B", "C", "D", "E", "F"]
        for row in rows:
            for col in cols:
                seat = f"{row}{col}"
                if seat not in booked_seats:
                    return seat
        raise serializers.ValidationError({"flight": "No seats available."})


class BookingSerializer(serializers.ModelSerializer):
    flight_info = serializers.SerializerMethodField()
    booking_reference = serializers.ReadOnlyField()

    class Meta:
        model = Booking
        fields = (
            "id", "booking_reference", "flight", "flight_info", "seat_number",
            "booking_date", "status", "total_price", "loyalty_discount",
        )
        read_only_fields = fields

    def get_flight_info(self, obj):
        return {
            "flight_number": obj.flight.flight_number,
            "departure": obj.flight.departure_airport.code,
            "arrival": obj.flight.arrival_airport.code,
            "departure_time": obj.flight.departure_time,
            "arrival_time": obj.flight.arrival_time,
        }


class PaymentSerializer(serializers.ModelSerializer):
    booking_reference = serializers.CharField(source="booking.booking_reference", read_only=True)

    class Meta:
        model = Payment
        fields = ("id", "booking", "booking_reference", "amount", "payment_method", "status", "transaction_id", "transaction_date")
        read_only_fields = ("id", "status", "transaction_id", "transaction_date")

    def validate(self, data):
        booking = data["booking"]
        user = self.context["request"].user
        if booking.user != user:
            raise serializers.ValidationError({"booking": "You can only pay for your own bookings."})
        if booking.status != Booking.Status.CONFIRMED:
            raise serializers.ValidationError({"booking": "Can only pay for confirmed bookings."})
        if hasattr(booking, "payment") and booking.payment.status == Payment.PaymentStatus.COMPLETED:
            raise serializers.ValidationError({"booking": "This booking has already been paid."})
        if data["amount"] != booking.total_price:
            raise serializers.ValidationError({"amount": f"Payment amount must be {booking.total_price}."})
        return data

    def create(self, validated_data):
        import uuid
        booking = validated_data["booking"]
        transaction_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"

        payment = Payment.objects.create(
            booking=booking,
            amount=validated_data["amount"],
            payment_method=validated_data["payment_method"],
            status=Payment.PaymentStatus.COMPLETED,
            transaction_id=transaction_id,
        )

        booking.status = Booking.Status.COMPLETED
        booking.save()

        base_price = booking.flight.price
        from apps.loyalty.services import earn_points
        earn_points(booking.user, float(base_price))

        return payment
