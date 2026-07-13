"""Database wiring tests — no live Postgres."""

from types import SimpleNamespace

import pytest


def test_connect_without_database_url_says_so(monkeypatch):
    """A missing DATABASE_URL used to surface as a bare 500 from every DB-backed
    route while /health and auth kept working — easy to misread as a code fault."""
    import jim.db as db_mod

    monkeypatch.setattr(db_mod, "settings",
                        lambda: SimpleNamespace(database_url=""))
    with pytest.raises(RuntimeError, match="DATABASE_URL is not set"):
        db_mod.connect()
