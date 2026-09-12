from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from core.views import health
from rest_framework.routers import DefaultRouter
from catalog.views import DiseaseViewSet, SymptomViewSet

router = DefaultRouter()
router.register('catalog/diseases', DiseaseViewSet, basename='disease')
router.register('catalog/symptoms', SymptomViewSet, basename='symptom')

urlpatterns = [
    path('api/v1/health/', health),
    path('api/v1/auth/', include('accounts.urls')),
    path('api/v1/', include('doctors.urls')),
    path('api/v1/', include('care.urls')),
    path('api/v1/', include('chatbot.urls')),
    path('api/v1/', include('messaging.urls')),
    path('api/v1/', include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
