"""
Regression tests for shared_init service caching behavior.
"""


def test_get_openai_client_recovers_after_api_key_appears(monkeypatch):
    from src import shared_init

    called = {"count": 0}

    def _fake_build(api_key, org_id):
        called["count"] += 1
        return {"api_key": api_key, "org_id": org_id}

    monkeypatch.setattr(shared_init, "_build_openai_client", _fake_build)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_ORG_ID", raising=False)

    first = shared_init.get_openai_client()
    assert first is None
    assert called["count"] == 0

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_ORG_ID", "org-1")
    second = shared_init.get_openai_client()
    assert second == {"api_key": "test-key", "org_id": "org-1"}
    assert called["count"] == 1


def test_get_curriculum_service_recovers_after_key_is_set(monkeypatch):
    from src import shared_init

    # No key case: should return None and avoid builder call.
    monkeypatch.setattr(shared_init, "load_config", lambda: {"defaults": {}})
    monkeypatch.setattr(shared_init, "get_openai_client", lambda: None)

    called = {"count": 0}

    def _fake_build(client, config):
        called["count"] += 1
        return {"client": client, "config": config}

    monkeypatch.setattr(shared_init, "_build_curriculum_service", _fake_build)

    first = shared_init.get_curriculum_service()
    assert first is None
    assert called["count"] == 0

    # Key becomes available later in the same process.
    monkeypatch.setattr(shared_init, "get_openai_client", lambda: "client-ok")
    second = shared_init.get_curriculum_service()
    assert second == {"client": "client-ok", "config": {"defaults": {}}}
    assert called["count"] == 1
