def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("SECRET_KEY", "a" * 32)
    from importlib import reload
    import app.core.config as cfg
    reload(cfg)
    s = cfg.Settings()
    assert s.DATABASE_URL.startswith("postgresql+asyncpg://")
    assert len(s.SECRET_KEY) >= 32
