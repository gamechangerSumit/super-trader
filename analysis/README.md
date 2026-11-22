# Analysis service

Python FastAPI service for deterministic indicators and transparent rule-based setup scoring.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

- Health: `GET /health`
- Analysis: `POST /api/v1/analyze`

Input requires at least 30 timestamped OHLCV candles. Use authorized data. Score is not win probability and response is not investment advice.
