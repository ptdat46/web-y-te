import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from catalog.models import Disease, Symptom

# backend/catalog/management/commands/import_catalog.py -> parents:
# [0]=commands, [1]=management, [2]=catalog, [3]=backend, [4]=project root
PROJECT_ROOT = Path(__file__).resolve().parents[4]
BACKEND_DIR = Path(__file__).resolve().parents[3]


class Command(BaseCommand):
    help = 'Import bilingual disease and symptom catalogs from CSV files.'

    def add_arguments(self, parser):
        parser.add_argument('--diseases', default=None)
        parser.add_argument('--symptoms', default=None)

    def resolve_csv(self, name, explicit_path):
        """Return the CSV path to use for `name`, or raise CommandError.

        Priority: explicit CLI path -> project root -> backend/ directory.
        """
        if explicit_path:
            path = Path(explicit_path)
            if not path.exists():
                raise CommandError(f'CSV file not found: {path}')
            return path
        filename = f'{name}_translations.csv'
        for candidate in (PROJECT_ROOT / filename, BACKEND_DIR / filename):
            if candidate.exists():
                return candidate
        raise CommandError(
            'CSV file not found: '
            + ', '.join(str(c) for c in (PROJECT_ROOT / filename, BACKEND_DIR / filename))
        )

    def handle(self, *args, **options):
        diseases = self.resolve_csv('disease', options.get('diseases'))
        symptoms = self.resolve_csv('symptom', options.get('symptoms'))
        self.import_file(diseases, Disease, 'disease_en', 'disease_vi')
        self.import_file(symptoms, Symptom, 'symptom_en', 'symptom_vi')

    def import_file(self, path, model, english_column, vietnamese_column):
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
