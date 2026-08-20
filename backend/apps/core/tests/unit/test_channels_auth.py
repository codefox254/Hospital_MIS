"""
JWT-over-WebSocket auth (TRD §4.3). Negative cases first per CLAUDE.md §4.3
— missing/invalid/inactive-user tokens must all resolve to AnonymousUser,
never raise and never resolve a real user.
"""

import pytest
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.factories import UserFactory
from apps.core.channels_auth import JWTAuthMiddleware


async def _dummy_inner(scope, receive, send):
    return scope


def _make_token(user):
    return str(AccessToken.for_user(user))


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
class TestJWTAuthMiddlewareDenies:
    async def test_missing_token_resolves_anonymous(self):
        middleware = JWTAuthMiddleware(_dummy_inner)
        scope = await middleware({"query_string": b""}, None, None)
        assert isinstance(scope["user"], AnonymousUser)

    async def test_garbage_token_resolves_anonymous(self):
        middleware = JWTAuthMiddleware(_dummy_inner)
        scope = await middleware({"query_string": b"token=not-a-real-jwt"}, None, None)
        assert isinstance(scope["user"], AnonymousUser)

    async def test_inactive_user_resolves_anonymous(self):
        user = await database_sync_to_async(UserFactory)(is_active=False)
        token = await database_sync_to_async(_make_token)(user)

        middleware = JWTAuthMiddleware(_dummy_inner)
        scope = await middleware({"query_string": f"token={token}".encode()}, None, None)
        assert isinstance(scope["user"], AnonymousUser)


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
class TestJWTAuthMiddlewareAllows:
    async def test_valid_token_resolves_the_correct_user(self):
        user = await database_sync_to_async(UserFactory)()
        token = await database_sync_to_async(_make_token)(user)

        middleware = JWTAuthMiddleware(_dummy_inner)
        scope = await middleware({"query_string": f"token={token}".encode()}, None, None)

        assert scope["user"].id == user.id
        assert scope["user"].is_authenticated
