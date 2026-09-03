import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from catalog.models import Disease, Symptom


class Command(BaseCommand):
    help = 'Import bilingual disease and symptom catalogs from CSV files.'

    def add_arguments(self, parser):
        parser.add_argument('--diseases', default='/data/catalog/disease_translations.csv')
        parser.add_argument('--symptoms', default='/data/catalog/symptom_translations.csv')

    def handle(self, *args, **options):
        self.import_file(Path(options['diseases']), Disease, 'disease_en', 'disease_vi')
        self.import_file(Path(options['symptoms']), Symptom, 'symptom_en', 'symptom_vi')

    def import_file(self, path, model, english_column, vietnamese_column):
        if not path.exists():
            raise CommandError(f'CSV file not found: {path}')
        with path.open(newline='', encoding='utf-8-sig') as source:
            reader = csv.DictReader(source)
            if reader.fieldnames != [english_column, vietnamese_column]:
                raise CommandError(f'Invalid header in {path.name}')
            count = 0
            for row in reader:
                name_en = row[english_column].strip()
                name_vi = row[vietnamese_column].strip()
                if name_en and name_vi:
                    model.objects.update_or_create(name_en=name_en, defaults={'name_vi': name_vi, 'is_active': True})
                    count += 1
        self.stdout.write(self.style.SUCCESS(f'{model.__name__}: {count} rows imported'))
