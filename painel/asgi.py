"""
ASGI config for painel project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

# Configurar Django primeiro
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'painel.settings')

from django.core.asgi import get_asgi_application

# Inicializar Django antes de importar routing
django_asgi_app = get_asgi_application()

# Agora podemos importar o routing (que depende dos models do Django)
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import rondonopolis.routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            rondonopolis.routing.websocket_urlpatterns
        )
    ),
})
