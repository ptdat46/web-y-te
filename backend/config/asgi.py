import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# http app is needed for ProtocolTypeRouter
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from messaging.auth import JWTAuthMiddleware


def get_websocket_urlpatterns():
    # Lazy import to avoid circular init.
    from messaging.routing import websocket_urlpatterns
    return websocket_urlpatterns


application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': JWTAuthMiddleware(URLRouter(get_websocket_urlpatterns())),
})
