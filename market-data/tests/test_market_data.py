import asyncio

from app import main


def test_health_reports_read_only_mode(monkeypatch):
    monkeypatch.delenv("UPSTOX_ACCESS_TOKEN", raising=False)
    result = asyncio.run(main.health())
    assert result["status"] == "ok"
    assert result["provider"] == "UPSTOX"
    assert result["configured"] is False
    assert result["mode"] == "READ_ONLY_MARKET_DATA"


def test_search_returns_only_nse_cash_equities(monkeypatch):
    sample = [
        {"segment": "NSE_EQ", "instrument_type": "EQ", "trading_symbol": "RELIANCE",
         "name": "RELIANCE INDUSTRIES LTD", "instrument_key": "NSE_EQ|INE002A01018", "exchange": "NSE"},
        {"segment": "NSE_FO", "instrument_type": "FUT", "trading_symbol": "RELIANCE FUT",
         "name": "RELIANCE FUT", "instrument_key": "NSE_FO|123", "exchange": "NSE"},
    ]

    async def fake_load_instruments(force=False):
        return sample

    monkeypatch.setattr(main, "load_instruments", fake_load_instruments)
    result = asyncio.run(main.search_instruments("RELIANCE", 10))
    assert result["count"] == 1
    assert result["results"][0]["instrumentKey"] == "NSE_EQ|INE002A01018"


def test_missing_token_is_not_silently_replaced_with_demo_data(monkeypatch):
    monkeypatch.delenv("UPSTOX_ACCESS_TOKEN", raising=False)
    try:
        main.access_token()
        assert False, "Expected an explicit configuration error"
    except Exception as exc:
        assert "UPSTOX_ACCESS_TOKEN" in str(exc.detail)
