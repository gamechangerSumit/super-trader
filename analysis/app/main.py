from datetime import datetime, timezone
from typing import Literal
from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="Super Trader Analysis", version="0.1.0",
              description="Deterministic educational technical analysis. Not financial advice.")

class Candle(BaseModel):
    time: datetime
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0)

class AnalyzeRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=30)
    candles: list[Candle] = Field(min_length=30, max_length=5000)

def ema(values: list[float], period: int) -> float:
    alpha = 2 / (period + 1)
    result = values[0]
    for value in values[1:]:
        result = alpha * value + (1 - alpha) * result
    return result

def rsi(values: list[float], period: int = 14) -> float:
    changes = [values[i] - values[i - 1] for i in range(1, len(values))]
    recent = changes[-period:]
    gains = sum(max(x, 0) for x in recent) / period
    losses = sum(max(-x, 0) for x in recent) / period
    if losses == 0:
        return 100.0 if gains > 0 else 50.0
    return 100 - (100 / (1 + gains / losses))

@app.get("/health")
def health():
    return {"status": "ok", "service": "analysis", "mode": "analysis-only"}

@app.post("/api/v1/analyze")
def analyze(request: AnalyzeRequest):
    candles = request.candles
    closes = [c.close for c in candles]
    volumes = [c.volume for c in candles]
    last = candles[-1]
    ema20, ema50 = ema(closes, 20), ema(closes, 50) if len(closes) >= 50 else ema(closes, 20)
    current_rsi = rsi(closes)
    average_volume = sum(volumes[-20:]) / min(20, len(volumes))
    volume_ratio = volumes[-1] / average_volume if average_volume else 0
    score = 0
    confirmations = []
    if last.close > ema20:
        score += 20; confirmations.append("Close above EMA20")
    if ema20 > ema50:
        score += 20; confirmations.append("EMA20 above EMA50")
    if 50 <= current_rsi <= 70:
        score += 20; confirmations.append("RSI momentum in bullish range")
    if volume_ratio >= 1.5:
        score += 20; confirmations.append("Volume at least 1.5x recent average")
    if last.close > max(c.high for c in candles[-20:-1]):
        score += 20; confirmations.append("Close above prior 19-candle high")
    direction: Literal["BULLISH", "BEARISH", "NEUTRAL"] = "BULLISH" if score >= 60 else ("BEARISH" if last.close < ema20 and current_rsi < 45 else "NEUTRAL")
    action = "WATCH_FOR_CONFIRMATION" if score >= 60 else "WAIT"
    return {
        "symbol": request.symbol.upper(),
        "asOf": datetime.now(timezone.utc).isoformat(),
        "dataPoints": len(candles),
        "lastClose": last.close,
        "indicators": {"ema20": round(ema20, 4), "ema50": round(ema50, 4), "rsi14": round(current_rsi, 2), "volumeRatio": round(volume_ratio, 2)},
        "score": score,
        "direction": direction,
        "action": action,
        "confirmations": confirmations,
        "warnings": ["Score is a rule-based setup score, not probability of profit.", "This endpoint does not forecast exact future price movement.", "Use verified market data; demo or stale candles are not tradable signals."]
    }
