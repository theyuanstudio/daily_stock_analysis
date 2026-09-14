from pathlib import Path

import pytest

from src.config import Config
from src.core.config_registry import get_field_definition
from src.search_service import (
    SearchService,
    apply_search_provider_priority,
    get_search_service,
    normalize_search_provider_priority,
    reset_search_service,
)


ROOT_DIR = Path(__file__).resolve().parents[1]


def _full_service(**kwargs) -> SearchService:
    defaults = {
        "anspire_keys": ["anspire-key"],
        "bocha_keys": ["bocha-key"],
        "tavily_keys": ["tavily-key"],
        "brave_keys": ["brave-key"],
        "serpapi_keys": ["serpapi-key"],
        "minimax_keys": ["minimax-key"],
        "searxng_base_urls": ["http://searxng.local:8080"],
        "searxng_public_instances_enabled": False,
    }
    defaults.update(kwargs)
    return SearchService(**defaults)


def _names(service: SearchService) -> list[str]:
    return [provider.name for provider in service._providers]


def test_default_assembly_order_is_unchanged() -> None:
    assert _names(_full_service()) == [
        "Anspire",
        "Bocha",
        "Tavily",
        "Brave",
        "SerpAPI",
        "MiniMax",
        "SearXNG",
    ]


@pytest.mark.parametrize("priority", [None, [], ["", "  "]])
def test_empty_priority_keeps_default_order(priority) -> None:
    assert _names(_full_service(provider_priority=priority)) == _names(_full_service())


def test_searxng_can_be_moved_first() -> None:
    assert _names(_full_service(provider_priority=["searxng"])) == [
        "SearXNG",
        "Anspire",
        "Bocha",
        "Tavily",
        "Brave",
        "SerpAPI",
        "MiniMax",
    ]


def test_priority_tokens_are_case_insensitive() -> None:
    assert _names(_full_service(provider_priority=["SEARXNG", "AnSpIrE"])) == [
        "SearXNG",
        "Anspire",
        "Bocha",
        "Tavily",
        "Brave",
        "SerpAPI",
        "MiniMax",
    ]


def test_unknown_tokens_are_ignored() -> None:
    assert normalize_search_provider_priority(["searxng", "unknown", "tavily"]) == [
        "SearXNG",
        "Tavily",
    ]
    assert _names(_full_service(provider_priority=["nope", "searxng", "also-nope"])) == [
        "SearXNG",
        "Anspire",
        "Bocha",
        "Tavily",
        "Brave",
        "SerpAPI",
        "MiniMax",
    ]


def test_unlisted_providers_keep_relative_order() -> None:
    assert _names(_full_service(provider_priority=["tavily", "searxng"])) == [
        "Tavily",
        "SearXNG",
        "Anspire",
        "Bocha",
        "Brave",
        "SerpAPI",
        "MiniMax",
    ]


def test_disabled_provider_token_is_skipped() -> None:
    service = SearchService(
        anspire_keys=["anspire-key"],
        tavily_keys=["tavily-key"],
        searxng_public_instances_enabled=False,
        provider_priority=["searxng", "tavily"],
    )
    assert _names(service) == ["Tavily", "Anspire"]


def test_constructor_kwargs_rebuild_preserves_priority() -> None:
    service = _full_service(provider_priority=["searxng", "tavily"])
    assert service._constructor_kwargs["provider_priority"] == ["searxng", "tavily"]
    rebuilt = SearchService(**service._constructor_kwargs)
    assert _names(rebuilt) == _names(service)


def test_config_property_parses_tokens() -> None:
    config = Config(search_provider_priority=" searxng, Anspire , ")
    assert config.search_provider_priority_list == ["searxng", "Anspire"]
    assert Config().search_provider_priority_list == []


def test_config_loads_search_provider_priority_from_env(monkeypatch) -> None:
    Config.reset_instance()
    monkeypatch.setenv("SEARCH_PROVIDER_PRIORITY", "searxng,tavily")
    config = Config._load_from_env()
    assert config.search_provider_priority == "searxng,tavily"
    assert config.search_provider_priority_list == ["searxng", "tavily"]
    Config.reset_instance()


def test_get_search_service_uses_config_priority(monkeypatch) -> None:
    reset_search_service()
    config = Config(
        anspire_api_keys=["anspire-key"],
        tavily_api_keys=["tavily-key"],
        searxng_base_urls=["http://searxng.local:8080"],
        search_provider_priority="searxng",
    )
    monkeypatch.setattr("src.config.get_config", lambda: config)
    service = get_search_service()
    try:
        assert _names(service) == ["SearXNG", "Anspire", "Tavily"]
    finally:
        reset_search_service()


def test_apply_helper_is_stable_for_empty_input() -> None:
    class _P:
        def __init__(self, name: str) -> None:
            self.name = name

    providers = [_P("Anspire"), _P("Tavily")]
    assert [p.name for p in apply_search_provider_priority(providers, None)] == [
        "Anspire",
        "Tavily",
    ]


def test_registry_field_has_web_help_metadata() -> None:
    field = get_field_definition("SEARCH_PROVIDER_PRIORITY")
    assert field["default_value"] == ""
    assert field["help_key"] == "settings.data_source.SEARCH_PROVIDER_PRIORITY"
    assert field["examples"]
    assert field["docs"]


def test_docs_and_workflow_document_search_provider_priority() -> None:
    env_example = (ROOT_DIR / ".env.example").read_text(encoding="utf-8")
    changelog = (ROOT_DIR / "docs" / "CHANGELOG.md").read_text(encoding="utf-8")
    workflow = (
        ROOT_DIR / ".github" / "workflows" / "00-daily-analysis.yml"
    ).read_text(encoding="utf-8")
    chinese_guide = (ROOT_DIR / "docs" / "full-guide.md").read_text(encoding="utf-8")
    english_guide = (ROOT_DIR / "docs" / "full-guide_EN.md").read_text(encoding="utf-8")

    assert "# SEARCH_PROVIDER_PRIORITY=searxng" in env_example
    assert "SEARCH_PROVIDER_PRIORITY=searxng" in changelog
    assert (
        "SEARCH_PROVIDER_PRIORITY: ${{ vars.SEARCH_PROVIDER_PRIORITY || secrets.SEARCH_PROVIDER_PRIORITY }}"
        in workflow
    )
    assert "`SEARCH_PROVIDER_PRIORITY`" in chinese_guide
    assert "`SEARCH_PROVIDER_PRIORITY`" in english_guide
