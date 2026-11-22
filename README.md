# Super Trader

A paper-trading-first market intelligence platform for Indian equities. No live order execution is implemented.

## Current foundation
- React + TypeScript + Vite dashboard with responsive dark UI, symbol search, watchlist, chart and setup watch.
- Java 21 / Spring Boot API with health and in-memory paper-trade endpoints.
- Python FastAPI analysis service with EMA20/50, RSI14, volume ratio and breakout confirmation scoring.
- Docker Compose for local services.

## Run locally
Requires Docker Desktop:
```bash
docker compose up --build
```
- Frontend: http://localhost:5173
- Backend health: http://localhost:8080/api/health
- Paper trading API: http://localhost:8080/api/paper/summary
- Analysis API docs: http://localhost:8001/docs

Or run separately:
- Frontend: `cd frontend && npm install && npm run dev`
- Backend: `cd backend && mvn spring-boot:run` (Java 21, Maven)
- Analysis: `cd analysis && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8001`

## Important data status
The initial dashboard uses clearly labelled illustrative demo values. It is NOT connected to live NSE/BSE market feeds. Before using live quotes or evaluating signals, integrate a licensed provider and validate timestamps, symbol mapping, corporate actions, missing candles and market holidays.

## Paper trading API
- `GET /api/paper/summary`
- `GET /api/paper/trades`
- `POST /api/paper/trades` body: `{"symbol":"RELIANCE","entryPrice":1000,"quantity":1,"stopLoss":990,"target":1020}`
- `POST /api/paper/trades/{id}/close` body: `{"exitPrice":1010}`

Paper trades are currently in-memory and reset when backend restarts. This is a development MVP, not production persistence.

## Risk and limitations
A setup score is not a win probability. No system can guarantee exact future market movement or profits. Use paper trading, realistic costs/slippage, out-of-sample backtests and independent verification before considering real capital.