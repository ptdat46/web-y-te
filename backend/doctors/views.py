from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsDoctorOrAdmin, IsPatientOrDoctor
from .models import ConnectionStatus, DoctorPatientConnection, DoctorProfile
from .serializers import (
    ConnectionCreateSerializer,
    ConnectionSerializer,
    DoctorProfileSerializer,
    PublicDoctorSerializer,
)


class IsProfileOwnerOrAdmin(IsDoctorOrAdmin):
    """Allow editing only by the profile owner (doctor) or an admin."""

    def has_object_permission(self, request, view, obj):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return request.user.role == 'ADMIN' or obj.user_id == request.user.id


class DoctorProfileViewSet(viewsets.ModelViewSet):
    """
    Doctor profiles.

    * GET    /doctors/            -> public directory (filterable, searchable)
    * GET    /doctors/{id}/       -> public detail
    * GET    /doctors/me/         -> full profile of the authenticated doctor
    * POST   /doctors/            -> create profile (DOCTOR only)
    * PUT/PATCH /doctors/{id}/    -> update own profile or admin
    """
    queryset = DoctorProfile.objects.select_related('user').all()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        'user__username',
        'user__first_name',
        'user__last_name',
        'specialty',
        'hospital',
        'bio',
    ]
    ordering_fields = ['years_of_experience', 'created_at', 'is_verified']
    ordering = ['-is_verified', 'user__last_name']

    def get_permissions(self):
        if self.action == 'list' or self.action == 'retrieve':
            return [AllowAny()]
        if self.action == 'me':
            return [IsAuthenticated()]
        if self.action in ('update', 'partial_update', 'destroy'):
            return [IsProfileOwnerOrAdmin()]
        return [IsDoctorOrAdmin()]

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return PublicDoctorSerializer
        return DoctorProfileSerializer

    @action(detail=False, methods=['get', 'post'], permission_classes=[IsAuthenticated])
    def me(self, request):
        profile = DoctorProfile.objects.select_related('user').filter(user=request.user).first()
        if request.method == 'GET':
            if profile is None:
                return Response({'detail': 'Doctor profile not found.'}, status=status.HTTP_404_NOT_FOUND)
            serializer = DoctorProfileSerializer(profile)
            return Response(serializer.data)
        # POST: create or fully update own profile
        serializer = DoctorProfileSerializer(profile, data=request.data, partial=(profile is not None and request.query_params.get('partial') is not None))
        serializer.is_valid(raise_exception=True)
        if profile is None:
            serializer.save(user=request.user)
        else:
            serializer.save()
        return Response(serializer.data)


class ConnectionViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Doctor-patient connections.

    * POST   /connections/            -> patient grants access
    * GET    /connections/            -> list my connections (doctor sees patients,
                                         patient sees doctors) filtered by ?status=
    * GET    /connections/{id}/       -> detail
    * DELETE /connections/{id}/       -> patient revokes access
    """
    serializer_class = ConnectionSerializer
    permission_classes = [IsAuthenticated, IsPatientOrDoctor]

    def get_queryset(self):
        qs = DoctorPatientConnection.objects.select_related('doctor', 'doctor__user', 'patient').all()
        user = self.request.user
        if user.role == 'DOCTOR':
            qs = qs.filter(doctor__user=user, status=ConnectionStatus.APPROVED)
        elif user.role == 'PATIENT':
            qs = qs.filter(patient=user)
        else:
            qs = qs.none()
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param.upper())
        return qs

    def create(self, request, *args, **kwargs):
        serializer = ConnectionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Only the patient can grant access.
        doctor = serializer.validated_data['doctor']
        patient = serializer.validated_data['patient']
        user = request.user
        is_patient = user.role == 'PATIENT' and patient.id == user.id
        if not is_patient:
            return Response(
                {'detail': 'You can only create a connection involving yourself.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        conn, created = DoctorPatientConnection.objects.get_or_create(
            doctor=doctor,
            patient=patient,
            defaults={'status': ConnectionStatus.APPROVED},
        )
        if not created:
            return Response(
                {'detail': 'A connection already exists for this doctor-patient pair.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(ConnectionSerializer(conn).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if self.request.user.role != 'PATIENT' or instance.patient_id != self.request.user.id:
            return Response({'detail': 'Chỉ bệnh nhân mới được hủy kết nối.'}, status=status.HTTP_403_FORBIDDEN)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)