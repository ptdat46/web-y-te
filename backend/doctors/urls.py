from django.urls import path
from rest_framework.routers import DefaultRouter

from .patient_views import PatientViewSet
from .views import ConnectionViewSet, DoctorProfileViewSet

router = DefaultRouter()
router.register('doctors', DoctorProfileViewSet, basename='doctor')
router.register('connections', ConnectionViewSet, basename='connection')
router.register('patients', PatientViewSet, basename='patient')

urlpatterns = router.urls
