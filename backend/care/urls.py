from rest_framework.routers import DefaultRouter

from .views import AlertViewSet, AuditLogViewSet, MedicalRecordViewSet, VitalSignViewSet

router = DefaultRouter()
router.register('records', MedicalRecordViewSet, basename='record')
router.register('vitals', VitalSignViewSet, basename='vital')
router.register('alerts', AlertViewSet, basename='alert')
router.register('audit-logs', AuditLogViewSet, basename='audit-log')

urlpatterns = router.urls