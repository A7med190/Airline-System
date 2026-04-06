from django_filters import rest_framework as filters
from .models import Flight


class FlightFilter(filters.FilterSet):
    origin = filters.CharFilter(field_name="departure_airport__code", lookup_expr="iexact")
    destination = filters.CharFilter(field_name="arrival_airport__code", lookup_expr="iexact")
    date = filters.DateFilter(field_name="departure_time", lookup_expr="date")
    date_from = filters.DateFilter(field_name="departure_time", lookup_expr="date__gte", label="date_from")
    date_to = filters.DateFilter(field_name="departure_time", lookup_expr="date__lte", label="date_to")
    min_price = filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = filters.NumberFilter(field_name="price", lookup_expr="lte")

    class Meta:
        model = Flight
        fields = ["origin", "destination", "date", "date_from", "date_to", "min_price", "max_price"]
