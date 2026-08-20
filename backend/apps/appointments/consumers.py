"""
Live queue WebSocket (TRD §4.4; Solution Spec Flow 5.2). Authenticated via
apps.core.channels_auth.JWTAuthMiddleware; a connection is rejected unless
the user is active, belongs to the requested facility, and holds
appointments.queue.view — the same module.resource.action engine as every
REST endpoint, not a separate ad-hoc check.
"""

import json

from channels.generic.websocket import AsyncWebsocketConsumer

from apps.appointments.realtime import queue_group_name


class QueueConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.facility_id = self.scope["url_route"]["kwargs"]["facility_id"]
        self.department_id = self.scope["url_route"]["kwargs"]["department_id"]
        self.group_name = queue_group_name(self.facility_id, self.department_id)

        if not await self._is_authorized():
            await self.close(code=4401)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def queue_update(self, event):
        await self.send(text_data=json.dumps(event))

    async def _is_authorized(self):
        from channels.db import database_sync_to_async

        user = self.scope.get("user")
        if user is None or not user.is_authenticated or not user.is_active:
            return False
        if str(user.facility_id) != str(self.facility_id):
            return False
        return await database_sync_to_async(self._has_queue_view_permission)(user)

    @staticmethod
    def _has_queue_view_permission(user):
        from apps.accounts.services import user_has_permission

        return user_has_permission(user, "appointments.queue.view", facility=user.facility)
