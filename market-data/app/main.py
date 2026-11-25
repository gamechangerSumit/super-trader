import asyncio
import gzip
import json
import os
from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import quote

import httpx
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

UPSTOX_API = "https://api.upstox.com"
INSTRUMENTS_URL = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"
app = FastAPI(title="Super Trader Live Market Data", version="1.0.0",
              description="Read-only Upstox market data adapter. No order endpoints.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

_instruments: list[dict[str, Any]] = []
_instruments_loaded_at: datetime | None = None


def access_token() -> str:
    token = os.getenv("UPSTOX_ACCESS_TOKEN", "").strip()
    if not token:
        raise HTTPException(
            status_code=503,
            detail="Upstox access token is not configured. Add UPSTOX_ACCESS_TOKEN to your local .env file and restart the market-data service.",
        )
    return token


def auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token()}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


async def load_instruments(force: bool = False) -> list[dict[str, Any]]:
    global _instruments, _instruments_loaded_at
    now = datetime.now()
    if _instruments and _instruments_loaded_at and not force:
        if now - _instruments_loaded_at < timedelta(hours=6):
            return _instruments
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(INSTRUMENTS_URL)
        response.raise_for_status()
    try:
        payload = json.loads(gzip.decompress(response.content))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail="Unable to decode Upstox instrument master.") from exc
    _instruments = [
        item for item in payload
        if item.get("segment") == "NSE_EQ" and item.get("instrument_type") == "EQ"
    ]
    _instruments_loaded_at = now
    return _instruments


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "market-data",
        "provider": "UPSTOX",
        "configured": bool(os.getenv("UPSTOX_ACCESS_TOKEN", "").strip()),
        "mode": "READ_ONLY_MARKET_DATA",
    }


@app.get("/api/market/status")
async def market_status():
    configured = bool(os.getenv("UPSTOX_ACCESS_TOKEN", "").strip())
    return {
        "provider": "UPSTOX",
        "configured": configured,
        "connected": False,
        "mode": "READ_ONLY",
        "message": "Credentials configured; live stream connects when a chart is opened." if configured
                   else "Add UPSTOX_ACCESS_TOKEN to .env. No demo quotes are returned.",
        "checkedAt": datetime.now().astimezone().isoformat(),
    }


@app.get("/api/market/search")
async def search_instruments(q: str = Query(min_length=1, max_length=40), limit: int = Query(20, ge=1, le=50)):
    query = q.strip().casefold()
    instruments = await load_instruments()
    matches = [
        item for item in instruments
        if query in str(item.get("trading_symbol", "")).casefold()
        or query in str(item.get("name", "")).casefold()
    ]
    matches.sort(key=lambda item: (
        str(item.get("trading_symbol", "")).casefold() != query,
        not str(item.get("trading_symbol", "")).casefold().startswith(query),
        str(item.get("trading_symbol", "")).casefold(),
    ))
    return {
        "provider": "UPSTOX",
        "count": min(len(matches), limit),
        "results": [{
            "symbol": item.get("trading_symbol"),
            "name": item.get("name"),
            "instrumentKey": item.get("instrument_key"),
            "exchange": item.get("exchange"),
            "segment": item.get("segment"),
        } for item in matches[:limit]],
    }


@app.get("/api/market/candles")
async def historical_candles(
    instrument_key: str = Query(min_length=3, max_length=100),
    unit: str = Query(default="minutes", pattern="^(minutes|hours|days|weeks|months)$"),
    interval: int = Query(default=1, ge=1, le=300),
    to_date: date | None = None,
    from_date: date | None = None,
):
    if unit == "minutes" and interval > 300:
        raise HTTPException(status_code=400, detail="Minute interval must be between 1 and 300.")
    if unit == "hours" and interval > 5:
        raise HTTPException(status_code=400, detail="Hour interval must be between 1 and 5.")
    if unit in {"days", "weeks", "months"} and interval != 1:
        raise HTTPException(status_code=400, detail="Day, week and month intervals must be 1.")
    end = to_date or date.today()
    start = from_date or (end - timedelta(days=30 if unit == "minutes" and interval <= 15 else 90))
    if start > end:
        raise HTTPException(status_code=400, detail="from_date cannot be after to_date.")
    if unit == "minutes" and interval <= 15 and (end - start).days > 31:
        raise HTTPException(status_code=400, detail="Upstox V3 limits 1–15 minute candle history to one month.")
    encoded_key = quote(instrument_key, safe="")
    url = f"{UPSTOX_API}/v3/historical-candle/{encoded_key}/{unit}/{interval}/{end.isoformat()}/{start.isoformat()}"
    async with httpx.AsyncClient(timeout=25) as client:
        response = await client.get(url, headers=auth_headers())
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=f"Upstox historical candle request failed: {response.text[:500]}")
    payload = response.json()
    raw_candles = payload.get("data", {}).get("candles", [])
    candles = [{
        "time": row[0],
        "open": float(row[1]),
        "high": float(row[2]),
        "low": float(row[3]),
        "close": float(row[4]),
        "volume": int(row[5] or 0),
        "openInterest": float(row[6] or 0) if len(row) > 6 else 0,
    } for row in raw_candles]
    candles.sort(key=lambda candle: candle["time"])
    return {
        "provider": "UPSTOX",
        "instrumentKey": instrument_key,
        "unit": unit,
        "interval": interval,
        "count": len(candles),
        "candles": candles,
        "receivedAt": datetime.now().astimezone().isoformat(),
    }


@app.get("/api/market/quote")
async def full_quote(instrument_key: str = Query(min_length=3, max_length=100)):
    url = f"{UPSTOX_API}/v3/market-quote/quotes"
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(url, params={"instrument_key": instrument_key}, headers=auth_headers())
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=f"Upstox quote request failed: {response.text[:500]}")
    payload = response.json()
    return {"provider": "UPSTOX", "instrumentKey": instrument_key,
            "data": payload.get("data", {}), "receivedAt": datetime.now().astimezone().isoformat()}


@app.websocket("/api/market/stream")
async def market_stream(websocket: WebSocket, instrument_keys: str = Query(min_length=3, max_length=1000)):
    await websocket.accept()
    keys = list(dict.fromkeys(key.strip() for key in instrument_keys.split(",") if key.strip()))
    if not keys or len(keys) > 10:
        await websocket.send_json({"type": "error", "message": "Subscribe to between 1 and 10 instruments per chart connection."})
        await websocket.close(code=1008)
        return
    try:
        token = access_token()
        import upstox_client
    except HTTPException as exc:
        await websocket.send_json({"type": "error", "message": exc.detail})
        await websocket.close(code=1011)
        return
    except ImportError:
        await websocket.send_json({"type": "error", "message": "Upstox Python SDK is not installed in this service image."})
        await websocket.close(code=1011)
        return

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=500)
    configuration = upstox_client.Configuration()
    configuration.access_token = token
    streamer = upstox_client.MarketDataStreamerV3(upstox_client.ApiClient(configuration))

    def enqueue(message: Any):
        def put():
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            queue.put_nowait(message)
        loop.call_soon_threadsafe(put)

    def on_open():
        streamer.subscribe(keys, "full")
        enqueue({"type": "stream_status", "status": "subscribed", "provider": "UPSTOX", "instrumentKeys": keys})

    def on_message(message):
        enqueue(message)

    def on_error(error):
        enqueue({"type": "stream_error", "message": str(error)[:300]})

    streamer.on("open", on_open)
    streamer.on("message", on_message)
    streamer.on("error", on_error)
    connect_task = asyncio.create_task(asyncio.to_thread(streamer.connect))
    try:
        while True:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=20)
                await websocket.send_json(message)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "heartbeat", "receivedAt": datetime.now().astimezone().isoformat()})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        try:
            streamer.disconnect()
        except Exception:
            pass
        connect_task.cancel()
