from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer


def set_refresh_token_cookie(response, refresh_token):
    response.set_cookie(
        key='refresh_token',
        value=refresh_token,
        httponly=True,
        path='/api/v1/auth/',
        samesite='Lax',  # Adjust in production if needed
        secure=False,    # Set to True in production with HTTPS
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
    return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    username = serializer.validated_data['username']
    password = serializer.validated_data['password']
    user = authenticate(username=username, password=password)
    if user is None:
        return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    if not user.is_active:
        return Response({'detail': 'User account is disabled'}, status=status.HTTP_401_UNAUTHORIZED)
    tokens = get_tokens_for_user(user)
    response = Response({
        'user': UserSerializer(user).data,
        'access': tokens['access'],
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