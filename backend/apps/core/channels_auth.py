"""
JWT-over-WebSocket auth (TRD §4.3): our API authenticates with JWT bearer
tokens, not session cookies, so Channels' stock AuthMiddlewareStack (which
reads the session cookie) doesn't apply — every real-time consumer in this
project (queue, and future bed-map/critical-alert channels) needs this
instead. Token is passed as a query param: wss://.../ws/...?token=<access>.
"""

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def _get_user_from_token(token):
    from apps.accounts.models import User

    try:
        validated = AccessToken(token)
        user = User.objects.get(pk=validated["user_id"])
    except (TokenError, InvalidToken, User.DoesNotExist, KeyError):
        return AnonymousUser()
    return user if user.is_active else AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        token = parse_qs(query_string).get("token", [None])[0]
        scope["user"] = await _get_user_from_token(token) if token else AnonymousUser()
        return await super().__call__(scope, receive, send)
