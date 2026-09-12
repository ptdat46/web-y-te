"""Read-only doctor endpoints that aggregate connected-patient data."""
from django.db.models import Count, Max, Q
from django.http import HttpResponse
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.serializers import PublicUserSerializer
from care.models import Alert, AlertStatus, MedicalRecord, VitalSign
from care.serializers import AlertSerializer, MedicalRecordSerializer, VitalSignSerializer
from care.pdf import build_patient_health_report_pdf

from .models import ConnectionStatus, DoctorPatientConnection
from .serializers import ConnectedPatientSerializer, PatientSummarySerializer


def _connected_patient_ids(user):
    """Return the list of patient ids connected (APPROVED) to this doctor."""
    return list(
        DoctorPatientConnection.objects.filter(
            doctor__user=user,
            status=ConnectionStatus.APPROVED,
        ).values_list('patient_id', flat=True)
    )


class PatientViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Read-only endpoints that let a doctor browse the patients connected to
    them and drill into a single patient's aggregated record.

    * GET /patients/          -> list with summary statistics
    * GET /patients/{id}/     -> detail with vitals/alerts/records
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ConnectedPatientSerializer

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.user.role != 'DOCTOR':
            raise PermissionDenied('Only doctors can access patient records.')

    def get_queryset(self):
        from accounts.models import User  # local import to avoid circulars

        user = self.request.user
        patient_ids = _connected_patient_ids(user)
        if not patient_ids:
            return User.objects.none()
        # Annotate with simple counts for the list view. Search is restricted
        # to the already-authorized patient set, so it cannot disclose whether
        # an unrelated patient exists.
        queryset = User.objects.filter(id__in=patient_ids, role='PATIENT')
        query = str(self.request.query_params.get('search', self.request.query_params.get('q', ''))).strip()
        if query:
            queryset = queryset.filter(
                Q(username__icontains=query) | Q(first_name__icontains=query) |
                Q(last_name__icontains=query) | Q(email__icontains=query)
            )
        return (
            queryset
            .annotate(
                vitals_count=Count('vitals', distinct=True),
                records_count=Count('medical_records', distinct=True),
                open_alerts_count=Count(
                    'alerts', filter=Q(alerts__status=AlertStatus.OPEN), distinct=True,
                ),
                latest_vital_at=Max('vitals__recorded_at'),
            )
            .order_by('last_name', 'first_name', 'username')
        )

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        data = PatientSummarySerializer(qs, many=True).data
        return Response(data)

    def retrieve(self, request, *args, **kwargs):
        from accounts.models import User

        user = request.user
        try:
            patient = (
                User.objects
                .annotate(
                    vitals_count=Count('vitals', distinct=True),
                    records_count=Count('medical_records', distinct=True),
                    open_alerts_count=Count(
                        'alerts', filter=Q(alerts__status=AlertStatus.OPEN), distinct=True,
                    ),
                    latest_vital_at=Max('vitals__recorded_at'),
                )
                .get(pk=kwargs['pk'])
            )
        except User.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if patient.id not in _connected_patient_ids(user):
            raise PermissionDenied('You are not connected to this patient.')
        latest_vital = (
            VitalSign.objects.filter(patient=patient)
            .select_related('patient')
            .order_by('-recorded_at')
            .first()
        )
        recent_alerts = (
            Alert.objects.filter(
                patient=patient,
                status__in=[AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED],
            )
            .select_related('patient', 'created_by', 'related_vital')
            .order_by('-created_at')[:20]
        )
        recent_records = (
            MedicalRecord.objects.filter(patient=patient)
            .select_related('patient', 'doctor', 'disease')
            .order_by('-created_at')[:20]
        )
        return Response({
            'patient': PublicUserSerializer(patient).data,
            'summary': {
                'vitals_count': patient.vitals_count,
                'records_count': patient.records_count,
                'open_alerts_count': patient.open_alerts_count,
                'latest_vital_at': patient.latest_vital_at.isoformat() if patient.latest_vital_at else None,
            },
            'latest_vital': VitalSignSerializer(latest_vital).data if latest_vital else None,
            'recent_alerts': AlertSerializer(recent_alerts, many=True).data,
            'recent_records': MedicalRecordSerializer(recent_records, many=True).data,
        })

    @action(detail=True, methods=['get'], url_path='health-report')
    def health_report(self, request, pk=None):
        """Download a comprehensive PDF report for an approved patient."""
        from accounts.models import User
        try:
            patient = User.objects.get(pk=pk, role='PATIENT')
        except User.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if patient.id not in _connected_patient_ids(request.user):
            raise PermissionDenied('You are not connected to this patient.')
        pdf_bytes = build_patient_health_report_pdf(patient)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="patient-health-report-{patient.pk}.pdf"'
        return response
