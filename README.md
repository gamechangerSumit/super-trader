# Super Trader

A paper-trading-first market research platform for Indian equities. The application does not connect to a broker and does not place real orders.

## Stack

- Frontend: React, TypeScript, Vite, Recharts
- API: Java 21, Spring Boot 3.4
- Persistence: PostgreSQL 16, Spring Data JPA
- Technical analysis: Python 3.12, FastAPI
- Local orchestration: Docker Compose
- CI: GitHub Actions (frontend build, backend tests, analysis tests)

## Run locally with Docker

Requirements: Docker Desktop with Compose v2.

```bash
docker compose up --build
```

Services:

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend health | http://localhost:8080/api/health |
| Paper trading summary | http://localhost:8080/api/paper/summary |
| Analysis health | http://localhost:8001/health |
| Analysis API docs | http://localhost:8001/docs |
| PostgreSQL | localhost:5432 |

PostgreSQL data is stored in the named Docker volume `super-trader-postgres` and survives container restarts. To remove the database and all saved paper trades intentionally, run `docker compose down -v`.

## Paper trading API

- `GET /api/paper/summary`
- `GET /api/paper/trades`
- `POST /api/paper/trades`

Example request:

```json
{
  "symbol": "RELIANCE",
  "entryPrice": 1000,
  "quantity": 1,
  "stopLoss": 990,
  "target": 1020
}
```

- `POST /api/paper/trades/{id}/close` with `{"exitPrice":1010}`

The simulator starts with ₹1,00,000 virtual capital, limits risk per trade to 1% of initial capital, and prevents open-position notional exposure from exceeding available virtual capital. It supports long-only trades in this MVP. Realized P&L excludes brokerage, taxes, slippage and other execution costs.

## Analysis API

`POST /api/v1/analyze` accepts at least 50 timestamped OHLCV candles and returns EMA20, EMA50, RSI14, volume ratio, a transparent rule-based setup score, direction and warnings. The score is not a win probability or a recommendation.

## Configuration

For local development, Docker Compose supplies the database connection. You can override the development database password with the `DB_PASSWORD` environment variable before running Compose.

## Current limitations — read before use

- Dashboard index and stock values are illustrative demo values. No licensed live NSE/BSE market-data provider is connected.
- The AI/technical-analysis service is ready to analyze supplied OHLCV candles, but no automated exchange scanner or scheduled ingestion pipeline is connected yet.
- Paper trades persist in PostgreSQL, but there is no broker integration, live order execution, real-money functionality, or guarantee of profit.
- The strategy score is an indicator checklist, not a probability forecast. Any future strategy should be backtested out of sample with transaction costs and slippage before practical use.

This repository is a development MVP, not a production trading system or investment advice.
