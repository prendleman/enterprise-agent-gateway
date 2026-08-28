"""FastAPI dependencies."""

from __future__ import annotations

from functools import lru_cache

from fastapi import Header, Request

from agent_gateway.agent.loop import AgentLoop
from agent_gateway.api.errors import UnauthorizedError
from agent_gateway.auth.context import AuthContext
from agent_gateway.auth.service import AuthService
from agent_gateway.config.settings import Settings, get_settings
from agent_gateway.providers.registry import ProviderRegistry, build_registry
from agent_gateway.providers.router import ProviderRouter


@lru_cache
def get_auth_service() -> AuthService:
    return AuthService(get_settings())


@lru_cache
def get_provider_registry() -> ProviderRegistry:
    return build_registry(get_settings())


@lru_cache
def get_provider_router() -> ProviderRouter:
    return ProviderRouter(get_provider_registry())


@lru_cache
def get_agent_loop() -> AgentLoop:
    return AgentLoop(router=get_provider_router())


def reset_cached_dependencies() -> None:
    """Clear cached singletons (used in tests)."""
    get_auth_service.cache_clear()
    get_provider_registry.cache_clear()
    get_provider_router.cache_clear()
    get_agent_loop.cache_clear()


async def get_auth_context(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> AuthContext:
    """Resolve authenticated caller from API key header."""
    settings = get_settings()
    header_name = settings.api_key_header
    raw_key = x_api_key or request.headers.get(header_name)
    auth = get_auth_service().authenticate(raw_key)
    if auth is None:
        raise UnauthorizedError("Invalid or missing API key")
    return auth


def override_dependencies(app, settings: Settings) -> None:
    """Replace cached dependencies for tests."""
    reset_cached_dependencies()
    auth_service = AuthService(settings)
    registry = build_registry(settings)
    router = ProviderRouter(registry)
    loop = AgentLoop(router=router)

    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_provider_registry] = lambda: registry
    app.dependency_overrides[get_provider_router] = lambda: router
    app.dependency_overrides[get_agent_loop] = lambda: loop
