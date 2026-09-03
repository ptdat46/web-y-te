from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ConnectionViewSet, DoctorProfileViewSet

router = DefaultRouter()
router.register('doctors', DoctorProfileViewSet, basename='doctor')
router.register('connections', ConnectionViewSet, basename='connection')

urlpatterns = router.urls