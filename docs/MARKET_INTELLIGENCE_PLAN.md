# Super Trader — Market Intelligence Implementation Plan

## Product goal
Build a read-only Indian equities research terminal using Upstox Analytics Token. The app must never place, modify, or cancel broker orders. All displayed market values must be sourced from the provider and carry a provider timestamp; no illustrative values may be presented as live data.

## Navigation and workspaces
1. **Overview** — NIFTY 50, NIFTY Bank, Sensex and India VIX index cards; market breadth (advancers/decliners/unchanged); session status; top momentum and unusual-volume lists.
2. **NIFTY 50** — all 50 current constituents, searchable/sortable table, live LTP, absolute and percentage change, day high/low, volume, sector, last update; click a row to open its chart.
3. **Top Opportunities** — ranked candidates, split into Momentum Up, Momentum Down, Breakout Watch, Volume Expansion and Pullback Watch. Show score components and reasons, not just a buy/sell label.
4. **Market Scanner** — filters for price change, relative volume, RSI, EMA trend, timeframe and sector. Scan only instruments with fresh provider data.
5. **Charts & Analysis** — symbol chart, 1m/5m/15m/1h/1d candles, EMA20/50, VWAP, RSI, MACD, ATR, volume and support/resistance.
6. **Watchlists** — user-managed lists and symbol pinning.
7. **Paper Trading** — simulation only, clearly separated from live brokerage.
8. **Strategy Lab** — configurable rule sets and historical backtests with fees/slippage, out-of-sample results and drawdown.
9. **Learning Hub** — explain indicators and risk controls.

## Data architecture
- Upstox Analytics Token for read-only quotes, historical candles and WebSocket market feed.
- NSE Indices constituent list is the source of truth for NIFTY 50 membership; refresh it on a schedule and retain a last-known-good copy.
- Upstox instrument master maps symbols to instrument keys.
- Batch REST quotes for broad snapshots; WebSocket for selected watchlists and active screens, respecting Upstox subscription limits.
- Cache provider responses, track exchange timestamps and stale-data state, and never substitute demo prices when the provider is unavailable.
- Use explicit market session state and IST timestamps.

## Ranking model (research signal, not a guaranteed prediction)
- Trend: close vs EMA20/EMA50 and EMA slope.
- Momentum: RSI regime, MACD direction/histogram and rate of change.
- Participation: relative volume and volume expansion.
- Structure: breakout/pullback relative to recent swing high/low and VWAP.
- Risk: ATR-based stop distance, reward/risk, liquidity and gap filters.
- Display score breakdown, setup invalidation and reasons. If data is missing/stale or risk/reward is poor, return WAIT / INSUFFICIENT DATA.
- Do not call a score a probability of profit. No auto orders.

## Delivery phases
1. Fix the current browser-to-market-data fetch and provider error reporting; add health/status diagnostics.
2. Replace all hardcoded demo market cards/watchlist/setup cards with provider-backed values or an explicit empty/unconfigured state.
3. Add the NIFTY 50 constituent universe and batch quote endpoint.
4. Build the NIFTY 50 table, market breadth, top movers and opportunity panels.
5. Build configurable scanner filters and multi-symbol streaming with provider limits.
6. Improve chart/indicator analysis and explainable setup scoring.
7. Add watchlists, alert rules and paper-trading integration.
8. Add historical backtesting, fees/slippage and out-of-sample performance reporting.
9. Add tests, CI checks, provider contract tests and operational documentation.

## Acceptance criteria
- Exactly 50 current NIFTY 50 constituents appear when the index constituent source is available.
- Every quote shows source and last-update timestamp; stale or missing quotes are visibly marked.
- Provider outage/token failure shows a useful error and never falls back to fake prices.
- Opportunity ranking is explainable and filters stale/illiquid data.
- App remains read-only: no broker order endpoints or credentials with order permissions.
- Build, backend tests, market-data tests and frontend typecheck pass.
