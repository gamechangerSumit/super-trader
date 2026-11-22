# Super Trader

A paper-trading-first market intelligence workspace for Indian equities. It provides educational analysis and simulated trading only; it does not place live orders or guarantee returns.

## MVP scope
- React + TypeScript dashboard
- Spring Boot API foundation
- Python analysis service for deterministic indicators and signal scoring
- Chart-ready OHLCV model and sample data
- Paper-trading-first workflow

## Architecture
- `frontend/`: React/Vite UI
- `backend/`: Java 21 / Spring Boot API
- `analysis/`: Python FastAPI analysis service

## Run locally
See each service README. The first iteration uses clearly labelled demo market data. Connect a licensed market-data provider before treating any quote or signal as live.

## Safety
Signals are research aids, not financial advice. Never use demo data for real-money decisions. Historical backtests do not guarantee future performance.
