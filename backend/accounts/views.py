from django.conf import settings
from django.contrib.auth import authenticate
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import (
    AdminUserSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    PatientProfileSerializer,
    RegisterSerializer,
    UserSerializer,
)
from .models import AuthToken, AuthTokenPurpose, PatientProfile, User
from .permissions import IsAdminUser
from care.audit import log_audit
from .email_service import send_password_reset_email, send_verification_email
from .throttles import AuthSensitiveThrottle, VerificationThrottle


def set_refresh_token_cookie(response, refresh_token):
    response.set_cookie(
        key='refresh_token',
        value=refresh_token,
        httponly=True,
        path='/api/v1/auth/',
        samesite=settings.SESSION_COOKIE_SAMESITE,
        secure=settings.SESSION_COOKIE_SECURE,
    )


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    token = AuthToken.issue(user, AuthTokenPurpose.EMAIL_VERIFICATION, settings.AUTH_TOKEN_TTL_MINUTES)
    send_verification_email(user, token)
    return Response({'detail': 'Đăng ký thành công. Vui lòng kiểm tra email để xác thực tài khoản.'}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthSensitiveThrottle])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    username = serializer.validated_data.get('username')
    email = serializer.validated_data.get('email')
    password = serializer.validated_data['password']
    # Keep username login working, but make email the preferred identifier.
    if email:
        user = User.objects.filter(email__iexact=email).first()
        user = user if user and user.check_password(password) else None
    else:
        user = authenticate(username=username, password=password)
    if user is None:
        return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    if not user.is_active:
        return Response({'detail': 'User account is disabled'}, status=status.HTTP_401_UNAUTHORIZED)
    if not user.email_verified:
        return Response({'detail': 'Vui lòng xác thực email trước khi đăng nhập.'}, status=status.HTTP_403_FORBIDDEN)
    tokens = get_tokens_for_user(user)
    response = Response({
        'user': UserSerializer(user).data,
        'access': tokens['access'],
        'must_change_password': user.must_change_password,
    })
    set_refresh_token_cookie(response, tokens['refresh'])
    return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        refresh_token = request.COOKIES.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
    except Exception:
        pass
    response = Response({'detail': 'Logged out'})
    response.delete_cookie('refresh_token', path='/api/v1/auth/')
    return response


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([VerificationThrottle])
def verify_email_view(request):
    user = AuthToken.consume(request.data.get('token'), AuthTokenPurpose.EMAIL_VERIFICATION)
    if user is None:
        return Response({'detail': 'Token xác thực không hợp lệ hoặc đã hết hạn.'}, status=status.HTTP_400_BAD_REQUEST)
    user.email_verified = True
    user.is_active = True
    user.save(update_fields=['email_verified', 'is_active'])
    tokens = get_tokens_for_user(user)
    response = Response({'user': UserSerializer(user).data, 'access': tokens['access']})
    set_refresh_token_cookie(response, tokens['refresh'])
    return response


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([VerificationThrottle])
def resend_verification_view(request):
    email = str(request.data.get('email', '')).strip().lower()
    user = User.objects.filter(email__iexact=email, email_verified=False, is_active=True).first()
    if user:
        token = AuthToken.issue(user, AuthTokenPurpose.EMAIL_VERIFICATION, settings.AUTH_TOKEN_TTL_MINUTES)
        send_verification_email(user, token)
    return Response({'detail': 'Nếu email hợp lệ, hướng dẫn xác thực đã được gửi.'})


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthSensitiveThrottle])
def forgot_password_view(request):
    email = str(request.data.get('email', '')).strip().lower()
    user = User.objects.filter(email__iexact=email, is_active=True, email_verified=True).first()
    if user:
        token = AuthToken.issue(user, AuthTokenPurpose.PASSWORD_RESET, settings.AUTH_TOKEN_TTL_MINUTES)
        send_password_reset_email(user, token)
    return Response({'detail': 'Nếu email hợp lệ, hướng dẫn đặt lại mật khẩu đã được gửi.'})


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthSensitiveThrottle])
def reset_password_view(request):
    password = request.data.get('password', '')
    confirmation = request.data.get('password_confirm', '')
    if len(password) < 8 or password != confirmation:
        return Response({'detail': 'Mật khẩu mới phải có ít nhất 8 ký tự và khớp xác nhận.'}, status=status.HTTP_400_BAD_REQUEST)
    user = AuthToken.consume(request.data.get('token'), AuthTokenPurpose.PASSWORD_RESET)
    if user is None:
        return Response({'detail': 'Token đặt lại mật khẩu không hợp lệ hoặc đã hết hạn.'}, status=status.HTTP_400_BAD_REQUEST)
    user.set_password(password)
    user.save(update_fields=['password'])
    return Response({'detail': 'Đặt lại mật khẩu thành công. Vui lòng đăng nhập lại.'})


@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_view(request):
    refresh_token = request.COOKIES.get('refresh_token')
    if not refresh_token:
        return Response({'detail': 'Refresh token not provided'}, status=status.HTTP_401_UNAUTHORIZED)
    try:
        refresh = RefreshToken(refresh_token)
        # Rotate tokens: blacklist old refresh token and issue new ones bound to the same user
        user_id = refresh.payload.get('user_id')
        if user_id is None:
            return Response({'detail': 'Invalid refresh token'}, status=status.HTTP_401_UNAUTHORIZED)
        refresh.blacklist()
        from accounts.models import User
        user = User.objects.filter(pk=user_id).first()
        if user is None or not user.is_active:
            return Response({'detail': 'Invalid refresh token'}, status=status.HTTP_401_UNAUTHORIZED)
        new_refresh = RefreshToken.for_user(user)
        access = new_refresh.access_token
        response = Response({'access': str(access)})
        set_refresh_token_cookie(response, str(new_refresh))
        return response
    except Exception:
        return Response({'detail': 'Invalid refresh token'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    return Response({'user': UserSerializer(request.user).data})


@api_view(['GET', 'PATCH', 'PUT'])
@permission_classes([IsAuthenticated])
def me_profile_view(request):
    """Get or update the current patient's extended profile."""
    if request.user.role != 'PATIENT':
        return Response({'detail': 'Only patients have patient profiles.'}, status=status.HTTP_403_FORBIDDEN)
    profile, _ = PatientProfile.objects.get_or_create(user=request.user)
    if request.method == 'GET':
        return Response(PatientProfileSerializer(profile).data)
    serializer = PatientProfileSerializer(profile, data=request.data, partial=request.method == 'PATCH')
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    serializer = ChangePasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    if not request.user.check_password(serializer.validated_data['current_password']):
        return Response({'current_password': 'Mật khẩu hiện tại không đúng.'}, status=status.HTTP_400_BAD_REQUEST)
    request.user.set_password(serializer.validated_data['new_password'])
    request.user.must_change_password = False
    request.user.save(update_fields=['password', 'must_change_password'])
    return Response({'user': UserSerializer(request.user).data})

@api_view(['GET', 'POST'])
@permission_classes([IsAdminUser])
def admin_users_view(request):
    if request.method == 'GET':
        users = User.objects.exclude(role='ADMIN').order_by('role', 'username')
        query = str(request.query_params.get('search', request.query_params.get('q', ''))).strip()
        if query:
            users = users.filter(Q(username__icontains=query) | Q(email__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query))
        role = str(request.query_params.get('role', '')).strip().upper()
        if role in ('PATIENT', 'DOCTOR'):
            users = users.filter(role=role)
        active = request.query_params.get('is_active')
        if active in ('true', 'false'):
            users = users.filter(is_active=(active == 'true'))
        return Response(AdminUserSerializer(users, many=True).data)
    serializer = AdminUserSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    return Response(AdminUserSerializer(serializer.save()).data, status=status.HTTP_201_CREATED)

@api_view(['PATCH'])
@permission_classes([IsAdminUser])
def admin_user_lock_view(request, user_id):
    user = User.objects.filter(pk=user_id).exclude(role='ADMIN').first()
    if user is None:
        return Response({'detail': 'Không tìm thấy tài khoản.'}, status=status.HTTP_404_NOT_FOUND)
    if 'is_active' not in request.data:
        return Response({'is_active': 'Trường này là bắt buộc.'}, status=status.HTTP_400_BAD_REQUEST)
    value = request.data.get('is_active')
    if not isinstance(value, bool):
        return Response({'is_active': 'Giá trị phải là true hoặc false.'}, status=status.HTTP_400_BAD_REQUEST)
    user.is_active = value
    user.save(update_fields=['is_active'])
    log_audit(
        request,
        actor=request.user,
        action='UPDATE',
        obj=user,
        summary=f'User {user.username} {"locked" if not value else "unlocked"}',
        details=f'is_active={value}',
    )
    return Response(AdminUserSerializer(user).data)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_dashboard_view(request):
    from care.models import Alert, AlertStatus, MedicalRecord
    from doctors.models import DoctorPatientConnection, DoctorProfile
    users = User.objects.exclude(role='ADMIN')
    return Response({
        'users': {'total': users.count(), 'active': users.filter(is_active=True).count(), 'locked': users.filter(is_active=False).count(), 'patients': users.filter(role='PATIENT').count(), 'doctors': users.filter(role='DOCTOR').count()},
        'doctors': {'total': DoctorProfile.objects.count(), 'verified': DoctorProfile.objects.filter(is_verified=True).count(), 'pending_verification': DoctorProfile.objects.filter(is_verified=False).count()},
        'connections': {'total': DoctorPatientConnection.objects.count(), 'approved': DoctorPatientConnection.objects.filter(status='APPROVED').count(), 'pending': DoctorPatientConnection.objects.filter(status='PENDING').count()},
        'alerts': {'total': Alert.objects.count(), 'open': Alert.objects.filter(status=AlertStatus.OPEN).count()},
        'medical_records': MedicalRecord.objects.count(),
    })


@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def admin_user_delete_view(request, user_id):
    user = User.objects.filter(pk=user_id).exclude(role='ADMIN').first()
    if user is None:
        return Response({'detail': 'Không tìm thấy tài khoản cần xóa.'}, status=status.HTTP_404_NOT_FOUND)
    user.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)