from datetime import datetime, timezone
from typing import Literal
from fastapi import FastAPI
from pydantic import BaseModel, Field, model_validator

app = FastAPI(title="Super Trader Analysis", version="0.1.0",
 description="Transparent rule-based technical analysis. Not financial advice.")

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
        return 100.0 if gains else 50.0
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
    ema20, ema50 = ema(closes, 20), ema(closes, 50)
    current_rsi = rsi(closes)
    avg_volume = sum(volumes[-20:]) / 20
    volume_ratio = volumes[-1] / avg_volume if avg_volume else 0
    prior_high = max(c.high for c in candles[-20:-1])
    score, confirmations = 0, []
    checks = [
      (last.close > ema20, "Close above EMA20"),
      (ema20 > ema50, "EMA20 above EMA50"),
      (50 <= current_rsi <= 70, "RSI momentum in bullish range"),
      (volume_ratio >= 1.5, "Volume at least 1.5x 20-candle average"),
      (last.close > prior_high, "Close above prior 19-candle high")
    ]
    for passed, label in checks:
        if passed:
            score += 20
            confirmations.append(label)
    direction: Literal["BULLISH", "BEARISH", "NEUTRAL"] = "BULLISH" if score >= 60 else ("BEARISH" if last.close < ema20 and current_rsi < 45 else "NEUTRAL")
    return {"symbol": request.symbol.upper(), "asOf": datetime.now(timezone.utc).isoformat(),
      "dataPoints": len(candles), "lastClose": last.close,
      "indicators": {"ema20": round(ema20, 4), "ema50": round(ema50, 4), "rsi14": round(current_rsi, 2), "volumeRatio": round(volume_ratio, 2)},
      "score": score, "direction": direction,
      "action": "WATCH_FOR_CONFIRMATION" if score >= 60 else "WAIT",
      "confirmations": confirmations,
      "warnings": ["Score is a rule-based setup score, not probability of profit.", "No algorithm can guarantee the next price movement.", "Only analyze verified, timestamped market data."]}