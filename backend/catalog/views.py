from django.db.models import Q
from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from .models import Disease, Symptom
from .serializers import DiseaseSerializer, SymptomSerializer


class CatalogViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset().filter(is_active=True)
        search = self.request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(Q(name_en__icontains=search) | Q(name_vi__icontains=search))
        return queryset


class DiseaseViewSet(CatalogViewSet):
    queryset = Disease.objects.all()
    serializer_class = DiseaseSerializer


class SymptomViewSet(CatalogViewSet):
    queryset = Symptom.objects.all()
    serializer_class = SymptomSerializer
