from app.main import ema, rsi


def test_ema_returns_last_weighted_value():
    assert round(ema([1.0, 2.0, 3.0], 2), 4) == 2.5556


def test_rsi_is_100_for_only_gains():
    assert rsi([float(i) for i in range(1, 20)]) == 100.0


def test_rsi_is_50_for_flat_prices():
    assert rsi([100.0] * 20) == 50.0


def test_rsi_is_zero_for_only_losses():
    assert rsi([float(20 - i) for i in range(20)]) == 0.0
