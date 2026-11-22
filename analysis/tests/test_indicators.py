from app.main import ema, rsi

def test_ema_returns_latest_value_for_flat_series():
    assert ema([100.0] * 60, 20) == 100.0

def test_rsi_flat_series_is_neutral():
    assert rsi([100.0] * 30) == 50.0

def test_rsi_rising_series_is_100():
    assert rsi([float(i) for i in range(1, 31)]) == 100.0
