from rest_framework import serializers
from .models import Disease, Symptom


class CatalogSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ('id', 'name_en', 'name_vi', 'is_active')


class DiseaseSerializer(CatalogSerializer):
    class Meta(CatalogSerializer.Meta):
        model = Disease


class SymptomSerializer(CatalogSerializer):
    class Meta(CatalogSerializer.Meta):
        model = Symptom
