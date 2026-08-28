"""Unit tests for application settings."""

from agent_gateway.config.settings import Settings, get_settings


def test_default_settings_demo_mode() -> None:
    settings = Settings()
    assert settings.app_env == "demo"
    assert settings.demo_mode is True
    assert settings.is_demo is True
    assert settings.database_url.startswith("sqlite")


def test_settings_problem_type_base() -> None:
    settings = Settings()
    assert settings.problem_type_base == "https://agent-gateway.example.com/problems"


def test_get_settings_cached() -> None:
    get_settings.cache_clear()
    first = get_settings()
    second = get_settings()
    assert first is second
