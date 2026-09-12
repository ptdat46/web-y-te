from rest_framework.routers import DefaultRouter

from .views import (
    AlertViewSet, AppointmentViewSet, AuditLogViewSet, MedicationLogViewSet,
    MedicationScheduleViewSet, MedicalRecordViewSet, NotificationViewSet,
    VitalSignViewSet,
)

router = DefaultRouter()
router.register('records', MedicalRecordViewSet, basename='record')
router.register('vitals', VitalSignViewSet, basename='vital')
router.register('alerts', AlertViewSet, basename='alert')
router.register('audit-logs', AuditLogViewSet, basename='audit-log')
router.register('notifications', NotificationViewSet, basename='notification')
router.register('medications', MedicationScheduleViewSet, basename='medication-schedule')
router.register('medication-schedules', MedicationScheduleViewSet, basename='medication-schedules')
router.register('medication-logs', MedicationLogViewSet, basename='medication-log')
router.register('appointments', AppointmentViewSet, basename='appointment')

urlpatterns = router.urls