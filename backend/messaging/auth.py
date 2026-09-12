from urllib.parse import parse_qs

from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from django.db import close_old_connections
from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


@database_sync_to_async
def get_user_from_token(token_str):
    try:
        UntypedToken(token_str)
    except (InvalidToken, TokenError):
        return None
    from rest_framework_simplejwt.tokens import AccessToken
    try:
        access = AccessToken(token_str)
        user_id = access.get('user_id')
        if user_id is None:
            return None
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
    except Exception:
        return None


class JWTAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope.get('type') != 'websocket':
            if self.inner is None:
                return None
            return await self.inner(scope, receive, send)

        close_old_connections()

        query_string = scope.get('query_string', b'').decode()
        qs = parse_qs(query_string)
        token_list = qs.get('token') or qs.get('Token') or []
        token = token_list[0] if token_list else None

        if token:
            user = await get_user_from_token(token)
            if user is None:
                await send({'type': 'websocket.close', 'code': 4401})
                return
            scope['user'] = user
            return await self.inner(scope, receive, send)
        else:
            # Fall back to Django session/cookie auth.
            if self.inner is None:
                scope['user'] = AnonymousUser()
                return None
            return await AuthMiddlewareStack(self.inner)(scope, receive, send)
