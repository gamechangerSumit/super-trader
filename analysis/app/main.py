from datetime import datetime, timezone
from typing import Literal
from fastapi import FastAPI
from pydantic import BaseModel, Field, model_validator

app = FastAPI(
    title="Super Trader Analysis",
    version="1.0.0",
    description="Explainable technical indicators and reference trade levels. Not financial advice.",
)


class Candle(BaseModel):
    time: datetime
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0)

    @model_validator(mode="after")
    def valid_ohlc(self):
        if self.high < max(self.open, self.close, self.low) or self.low > min(self.open, self.close, self.high):
            raise ValueError("Invalid OHLC candle range")
        return self


class AnalyzeRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=30)
    candles: list[Candle] = Field(min_length=50, max_length=5000)


def ema_series(values: list[float], period: int) -> list[float]:
    alpha = 2 / (period + 1)
    result = [values[0]]
    for value in values[1:]:
        result.append(alpha * value + (1 - alpha) * result[-1])
    return result


def rsi(values: list[float], period: int = 14) -> float:
    changes = [values[i] - values[i - 1] for i in range(1, len(values))]
    recent = changes[-period:]
    gains = sum(max(x, 0) for x in recent) / period
    losses = sum(max(-x, 0) for x in recent) / period
    if losses == 0:
        return 100.0 if gains else 50.0
    return 100 - (100 / (1 + gains / losses))


def atr(candles: list[Candle], period: int = 14) -> float:
    ranges = []
    for index in range(1, len(candles)):
        current = candles[index]
        previous_close = candles[index - 1].close
        ranges.append(max(
            current.high - current.low,
            abs(current.high - previous_close),
            abs(current.low - previous_close),
        ))
    return sum(ranges[-period:]) / min(period, len(ranges))


@app.get("/health")
def health():
    return {"status": "ok", "service": "analysis", "mode": "analysis-only"}


@app.post("/api/v1/analyze")
def analyze(request: AnalyzeRequest):
    candles = request.candles
    closes = [c.close for c in candles]
    volumes = [c.volume for c in candles]
    last = candles[-1]
    ema20_values = ema_series(closes, 20)
    ema50_values = ema_series(closes, 50)
    ema20, ema50 = ema20_values[-1], ema50_values[-1]
    current_rsi = rsi(closes)
    current_atr = atr(candles)
    avg_volume = sum(volumes[-20:]) / min(20, len(volumes))
    volume_ratio = volumes[-1] / avg_volume if avg_volume else 0
    prior_high = max(c.high for c in candles[-20:-1])
    prior_low = min(c.low for c in candles[-20:-1])

    score = 0
    confirmations = []
    checks = [
        (last.close > ema20, "Close above EMA20"),
        (ema20 > ema50, "EMA20 above EMA50"),
        (50 <= current_rsi <= 70, "RSI momentum in bullish range"),
        (volume_ratio >= 1.5, "Volume at least 1.5x 20-candle average"),
        (last.close > prior_high, "Close above prior 19-candle high"),
    ]
    for passed, label in checks:
        if passed:
            score += 20
            confirmations.append(label)

    bullish = score >= 60
    bearish = last.close < ema20 and ema20 < ema50 and current_rsi < 45
    direction: Literal["BULLISH", "BEARISH", "NEUTRAL"] = (
        "BULLISH" if bullish else "BEARISH" if bearish else "NEUTRAL"
    )

    setup = "WAIT"
    entry = stop_loss = target1 = target2 = risk_reward = None
    invalidation = "No actionable setup. Wait for a clearer trend and confirmation."
    if current_atr > 0 and bullish:
        risk = current_atr * 1.5
        setup = "LONG_WATCH"
        entry = last.close
        stop_loss = round(entry - risk, 2)
        target1 = round(entry + risk * 2, 2)
        target2 = round(entry + risk * 3, 2)
        risk_reward = "1:2 / 1:3"
        invalidation = "Long thesis weakens below the reference stop-loss level."
    elif current_atr > 0 and bearish:
        risk = current_atr * 1.5
        setup = "SHORT_WATCH"
        entry = last.close
        stop_loss = round(entry + risk, 2)
        target1 = round(entry - risk * 2, 2)
        target2 = round(entry - risk * 3, 2)
        risk_reward = "1:2 / 1:3"
        invalidation = "Short thesis weakens above the reference stop-loss level."

    return {
        "symbol": request.symbol.upper(),
        "asOf": datetime.now(timezone.utc).isoformat(),
        "dataPoints": len(candles),
        "lastClose": last.close,
        "indicators": {
            "ema20": round(ema20, 4),
            "ema50": round(ema50, 4),
            "rsi14": round(current_rsi, 2),
            "atr14": round(current_atr, 4),
            "volumeRatio": round(volume_ratio, 2),
            "priorResistance": round(prior_high, 2),
            "priorSupport": round(prior_low, 2),
        },
        "score": score,
        "direction": direction,
        "setup": setup,
        "entryReference": round(entry, 2) if entry is not None else None,
        "stopLossReference": stop_loss,
        "target1Reference": target1,
        "target2Reference": target2,
        "riskReward": risk_reward,
        "invalidation": invalidation,
        "confirmations": confirmations,
        "warnings": [
            "Setup score is a rule-based checklist, not a probability of profit.",
            "Entry, stop and targets are ATR-based reference levels, not order instructions.",
            "Wait for candle close and independently confirm the setup before considering a trade.",
            "Backtest with brokerage, taxes, slippage and out-of-sample data before relying on any strategy.",
        ],
    }
