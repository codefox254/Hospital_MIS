from django.urls import re_path

from apps.appointments.consumers import QueueConsumer

websocket_urlpatterns = [
    re_path(
        r"^ws/appointments/queue/(?P<facility_id>[0-9a-f-]+)/(?P<department_id>[0-9a-f-]+)/$",
        QueueConsumer.as_asgi(),
    ),
]
