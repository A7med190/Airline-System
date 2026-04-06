from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AirportViewSet, FlightViewSet

router = DefaultRouter()
router.register(r"airports", AirportViewSet, basename="airport")
router.register(r"", FlightViewSet, basename="flight")

urlpatterns = [
    path("", include(router.urls)),
]
