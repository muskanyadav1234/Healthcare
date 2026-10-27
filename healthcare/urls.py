from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    DoctorViewSet,
    LoginView,
    MappingDetailView,
    MappingListCreateView,
    PatientViewSet,
    RegisterView,
)

router = DefaultRouter()
router.register("patients", PatientViewSet, basename="patient")
router.register("doctors", DoctorViewSet, basename="doctor")

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("mappings/", MappingListCreateView.as_view(), name="mapping-list"),
    path("mappings/<int:pk>/", MappingDetailView.as_view(), name="mapping-detail"),
] + router.urls
