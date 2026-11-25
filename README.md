# Super Trader

A read-only Indian market analysis terminal with live Upstox market data, real historical OHLC candles, technical indicators, ATR-based reference levels, and a persistent paper-trading simulator. **The app does not submit broker orders or execute trades.**

## Stack

- Frontend: React, TypeScript, Vite, Lightweight Charts (candlesticks, EMA overlays and volume)
- Backend: Java 21, Spring Boot, PostgreSQL (paper-trade persistence)
- Market data: Python FastAPI adapter for Upstox instrument search, historical candles, full quotes and Market Data Feed V3 WebSocket
- Analysis: Python FastAPI (EMA20/50, RSI14, ATR14, volume ratio, support/resistance context and explainable setup checklist)
- Local orchestration: Docker Compose
- CI: GitHub Actions

## 1. Configure Upstox market data

The market terminal uses Upstox because its official developer platform currently advertises free access to trading and market-data APIs. Market data access still requires an Upstox account, a developer app and a valid API token.

1. Create/sign in to your Upstox account.
2. Create a developer app in the [Upstox Developer Portal](https://developer.upstox.com/).
3. Open the **Analytics** tab in Developer Apps and generate the **Analytics Token**. It is read-only, free, valid for one year, and supports market data plus WebSocket feeds. It cannot place, modify or cancel orders.
4. Copy the example environment file and add the token locally:

PowerShell:

```powershell
Copy-Item .env.example .env
notepad .env
```

Set:

```dotenv
UPSTOX_ACCESS_TOKEN=PASTE_YOUR_OWN_TOKEN_HERE
DB_PASSWORD=choose-a-local-password
```

Never commit `.env`, paste the token into chat, or expose it in frontend code. `.env` is ignored by Git. The Analytics Token is read-only and cannot place, modify or cancel broker orders. The application never asks for your Upstox password.

Official references:
- [Upstox Analytics Token](https://upstox.com/developer/api-documentation/analytics-token/)
- [Market Data Feed V3](https://upstox.com/developer/api-documentation/v3/get-market-data-feed/)
- [Historical Candle Data V3](https://upstox.com/developer/api-documentation/v3/get-historical-candle-data/)
- [Instrument master files](https://upstox.com/developer/api-documentation/instruments/)

## 2. Start the complete stack

Requirements: Docker Desktop with Compose v2.

```powershell
docker compose up --build
```

Services:

| Service | URL |
|---|---|
| Frontend terminal | http://localhost:5173 |
| Backend health | http://localhost:8080/api/health |
| Paper trading summary | http://localhost:8080/api/paper/summary |
| Analysis API docs | http://localhost:8001/docs |
| Market data health | http://localhost:8002/health |
| Market data status | http://localhost:8002/api/market/status |
| Market data API docs | http://localhost:8002/docs |

The first market-data image build installs the Upstox Python SDK and may take a few minutes. If the token is missing or expired, the UI reports the issue and does not fall back to fabricated quotes.

## 3. Live terminal capabilities

- NSE cash-equity symbol search using Upstox's official instrument master.
- Historical OHLCV candles for 1m, 5m, 15m, 1H and 1D timeframes.
- Upstox Market Data Feed V3 WebSocket subscription for the selected instrument.
- Lightweight candlestick chart with volume and EMA20/EMA50 overlays.
- RSI14 and MACD readouts, plus EMA20/50, ATR14 and volume-ratio values.
- Explainable bullish/ bearish / wait checklist and ATR-based entry-reference, stop-reference and target-reference levels.
- Provider status and visible errors when token, feed or candle retrieval is unavailable.

The historical API returns actual provider candles. The WebSocket is used to update the current chart candle from provider feed messages. Market updates are available only when the exchange/provider is streaming data and the token has the required permissions.

## 4. Analysis is an indication, not an order

The Python analysis service calculates:
- EMA20 and EMA50 trend context
- RSI14 momentum
- ATR14 volatility
- Relative volume versus the recent 20-candle average
- Prior 19-candle high/low context
- A 0–100 rule checklist score (not a win probability)

When the rule checklist qualifies, it displays an ATR-based reference entry, stop and two targets. These are chart annotations for study and paper testing, not broker instructions. Wait for candle close and independently validate the setup. No algorithm can guarantee the next price movement.

## 5. Paper trading

- `GET /api/paper/summary`
- `GET /api/paper/trades`
- `POST /api/paper/trades`
- `POST /api/paper/trades/{id}/close`

The simulator starts with ₹1,00,000 virtual capital, limits risk per trade to 1% of initial capital, and prevents open-position notional exposure from exceeding available virtual capital. Paper trades persist in PostgreSQL. Brokerage, taxes, slippage and market execution are not modelled yet.

PostgreSQL data is stored in the named Docker volume `super-trader-postgres`. To intentionally delete all local database data and paper trades, run `docker compose down -v`.

## 6. Current limitations before real-world reliance

- A valid Upstox API token and required market-data permissions are mandatory; this repository does not include credentials.
- The current scanner is symbol search plus selected-symbol analysis. A full-market scheduled scanner and alerts are not implemented yet.
- Only the selected instrument is streamed by the chart terminal.
- Indicator calculations and setup rules are an initial research baseline, not a validated profitable strategy. Backtesting, walk-forward validation, transaction costs, slippage, market holidays and corporate actions must be handled before relying on signals.
- The older overview cards and sample watchlist are explicitly illustrative demo values; the live terminal above is the provider-backed market-data area.
- No broker order endpoints, automatic execution, real-money trading or profit guarantees are included.

This is a development and research tool, not investment advice. Always make your own trading decisions.
