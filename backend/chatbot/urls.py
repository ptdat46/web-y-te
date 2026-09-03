from rest_framework.routers import DefaultRouter

from .views import ConversationViewSet

router = DefaultRouter()
router.register('chat/conversations', ConversationViewSet, basename='conversation')

urlpatterns = router.urls