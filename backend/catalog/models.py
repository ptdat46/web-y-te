from django.db import models


class CatalogEntry(models.Model):
    name_en = models.CharField(max_length=255, unique=True)
    name_vi = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['name_en']

    def __str__(self):
        return self.name_vi


class Disease(CatalogEntry):
    pass


class Symptom(CatalogEntry):
    pass
