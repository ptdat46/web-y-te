from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ChatRoomViewSet, PatientFileViewSet

router = DefaultRouter()
router.register('chat/rooms', ChatRoomViewSet, basename='chat-room')
router.register('patient-files', PatientFileViewSet, basename='patient-file')
urlpatterns = router.urls
