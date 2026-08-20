import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

# Django's ASGI app is set up first so django.setup() runs before any
# channels routing imports touch app-labeled models (Django Channels
# requirement).
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter  # noqa: E402

# WebSocket routing (live queue, bed map, critical alerts — Solution Spec
# §5.2/5.4/5.5) is added starting with the Appointments milestone (M2).
application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
    }
)
