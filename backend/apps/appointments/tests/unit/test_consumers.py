"""
QueueConsumer real-time behavior (TRD §4.4; Solution Spec Flow 5.2). Runs
against the actual configured channel layer (Redis, same as local dev/prod)
— not a mocked one — since the whole point is proving the pub/sub wiring
genuinely works, not that the code compiles. Negative cases first per
CLAUDE.md §4.3.
"""

import pytest
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.factories import RoleFactory, RolePermissionFactory, UserFactory, UserRoleFactory
from apps.accounts.models import Permission
from apps.appointments.routing import websocket_urlpatterns
from apps.core.channels_auth import JWTAuthMiddleware
from apps.core.factories import DepartmentFactory, FacilityFactory


def _make_token(user):
    return str(AccessToken.for_user(user))


def _grant_queue_view(user):
    role = RoleFactory()
    permission, _ = Permission.objects.get_or_create(code="appointments.queue.view")
    RolePermissionFactory(role=role, permission=permission)
    UserRoleFactory(user=user, role=role, facility=None)


def _application():
    return JWTAuthMiddleware(URLRouter(websocket_urlpatterns))


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
class TestQueueConsumerDenies:
    async def test_connection_without_a_token_is_rejected(self):
        facility = await database_sync_to_async(FacilityFactory)()
        department = await database_sync_to_async(DepartmentFactory)(facility=facility)

        communicator = WebsocketCommunicator(
            _application(), f"/ws/appointments/queue/{facility.id}/{department.id}/"
        )
        connected, _ = await communicator.connect()
        assert connected is False
        await communicator.disconnect()

    async def test_authenticated_user_without_queue_permission_is_rejected(self):
        facility = await database_sync_to_async(FacilityFactory)()
        department = await database_sync_to_async(DepartmentFactory)(facility=facility)
        user = await database_sync_to_async(UserFactory)(facility=facility)
        token = await database_sync_to_async(_make_token)(user)

        communicator = WebsocketCommunicator(
            _application(),
            f"/ws/appointments/queue/{facility.id}/{department.id}/?token={token}",
        )
        connected, _ = await communicator.connect()
        assert connected is False
        await communicator.disconnect()

    async def test_user_from_a_different_facility_is_rejected(self):
        facility = await database_sync_to_async(FacilityFactory)()
        other_facility = await database_sync_to_async(FacilityFactory)()
        department = await database_sync_to_async(DepartmentFactory)(facility=facility)
        user = await database_sync_to_async(UserFactory)(facility=other_facility)
        await database_sync_to_async(_grant_queue_view)(user)
        token = await database_sync_to_async(_make_token)(user)

        communicator = WebsocketCommunicator(
            _application(),
            f"/ws/appointments/queue/{facility.id}/{department.id}/?token={token}",
        )
        connected, _ = await communicator.connect()
        assert connected is False
        await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
class TestQueueConsumerAllows:
    async def test_authenticated_user_with_permission_can_connect(self):
        facility = await database_sync_to_async(FacilityFactory)()
        department = await database_sync_to_async(DepartmentFactory)(facility=facility)
        user = await database_sync_to_async(UserFactory)(facility=facility)
        await database_sync_to_async(_grant_queue_view)(user)
        token = await database_sync_to_async(_make_token)(user)

        communicator = WebsocketCommunicator(
            _application(),
            f"/ws/appointments/queue/{facility.id}/{department.id}/?token={token}",
        )
        connected, _ = await communicator.connect()
        assert connected is True
        await communicator.disconnect()

    @pytest.mark.smoke
    async def test_connected_client_receives_a_published_queue_update(self):
        facility = await database_sync_to_async(FacilityFactory)()
        department = await database_sync_to_async(DepartmentFactory)(facility=facility)
        user = await database_sync_to_async(UserFactory)(facility=facility)
        await database_sync_to_async(_grant_queue_view)(user)
        token = await database_sync_to_async(_make_token)(user)

        communicator = WebsocketCommunicator(
            _application(),
            f"/ws/appointments/queue/{facility.id}/{department.id}/?token={token}",
        )
        connected, _ = await communicator.connect()
        assert connected is True

        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            f"queue-{facility.id}-{department.id}",
            {"type": "queue.update", "queue_number": 1, "status": "checked_in"},
        )

        message = await communicator.receive_json_from()
        assert message["queue_number"] == 1
        assert message["status"] == "checked_in"

        await communicator.disconnect()
