import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createChart, CandlestickSeries, HistogramSeries, LineSeries } from 'lightweight-charts';
import { Activity, AlertTriangle, CandlestickChart, Search, Wifi, WifiOff, RefreshCw } from 'lucide-react';

const MARKET_API = import.meta.env.VITE_MARKET_API_BASE_URL || 'http://localhost:8002';
const ANALYSIS_API = import.meta.env.VITE_ANALYSIS_API_BASE_URL || 'http://localhost:8001';

type Instrument = { symbol: string; name: string; instrumentKey: string; exchange: string };
type Candle = { time: string; open: number; high: number; low: number; close: number; volume: number };
type Analysis = {
  score: number; direction: string; setup: string; entryReference: number | null;
  stopLossReference: number | null; target1Reference: number | null; target2Reference: number | null;
  riskReward: string | null; invalidation: string;
  indicators: { ema20: number; ema50: number; rsi14: number; atr14: number; volumeRatio: number; priorResistance: number; priorSupport: number };
  confirmations: string[]; warnings: string[];
};

const TIMEFRAMES = [
  { label: '1m', unit: 'minutes', interval: 1 },
  { label: '5m', unit: 'minutes', interval: 5 },
  { label: '15m', unit: 'minutes', interval: 15 },
  { label: '1H', unit: 'hours', interval: 1 },
  { label: '1D', unit: 'days', interval: 1 },
] as const;

function epoch(value: string): number {
  const n = Number(value);
  if (Number.isFinite(n) && n > 1000000000000) return Math.floor(n / 1000);
  if (Number.isFinite(n) && n > 1000000000) return Math.floor(n);
  return Math.floor(new Date(value).getTime() / 1000);
}

function chartTime(value: string): any { return epoch(value) as any; }

function ema(values: number[], period: number): number[] {
  if (!values.length) return [];
  const alpha = 2 / (period + 1);
  const out = [values[0]];
  for (let i = 1; i < values.length; i++) out.push(alpha * values[i] + (1 - alpha) * out[i - 1]);
  return out;
}

function calculateRsi(values: number[], period = 14): number | null {
  if (values.length < period + 1) return null;
  const diffs = values.slice(1).map((value, index) => value - values[index]);
  const recent = diffs.slice(-period);
  const gains = recent.reduce((sum, value) => sum + Math.max(value, 0), 0) / period;
  const losses = recent.reduce((sum, value) => sum + Math.max(-value, 0), 0) / period;
  if (!losses) return gains ? 100 : 50;
  return 100 - 100 / (1 + gains / losses);
}

function macd(values: number[]): { macd: number | null; signal: number | null } {
  if (values.length < 35) return { macd: null, signal: null };
  const fast = ema(values, 12);
  const slow = ema(values, 26);
  const line = fast.map((value, index) => value - slow[index]);
  return { macd: line[line.length - 1], signal: ema(line, 9)[line.length - 1] ?? null };
}

export default function LiveMarketTerminal() {
  const [query, setQuery] = useState('RELIANCE');
  const [results, setResults] = useState<Instrument[]>([]);
  const [instrument, setInstrument] = useState<Instrument | null>(null);
  const [timeframe, setTimeframe] = useState<(typeof TIMEFRAMES)[number]>(TIMEFRAMES[0]);
  const [candles, setCandles] = useState<Candle[]>([]);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [marketStatus, setMarketStatus] = useState('Checking provider…');
  const [streamState, setStreamState] = useState('DISCONNECTED');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const chartHost = useRef<HTMLDivElement>(null);
  const candleSeries = useRef<any>(null);
  const volumeSeries = useRef<any>(null);
  const ema20Series = useRef<any>(null);
  const ema50Series = useRef<any>(null);
  const chartRef = useRef<any>(null);
  const priceLines = useRef<any[]>([]);
  const candlesRef = useRef<Candle[]>([]);
  const minuteVolumesRef = useRef<Map<number, number>>(new Map());

  useEffect(() => { candlesRef.current = candles; }, [candles]);

  const search = useCallback(async (term: string) => {
    if (!term.trim()) return;
    try {
      const response = await fetch(MARKET_API + '/api/market/search?q=' + encodeURIComponent(term));
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || 'Instrument search failed');
      setResults(body.results || []);
      if (!instrument && body.results?.length) setInstrument(body.results[0]);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Market service unavailable');
    }
  }, [instrument]);

  useEffect(() => {
    fetch(MARKET_API + '/api/market/status')
      .then(r => r.json())
      .then(data => setMarketStatus(data.configured ? 'UPSTOX TOKEN CONFIGURED' : 'UPSTOX TOKEN REQUIRED'))
      .catch(() => setMarketStatus('MARKET SERVICE OFFLINE'));
    search('RELIANCE');
  }, []);

  useEffect(() => {
    if (!chartHost.current) return;
    const chart = createChart(chartHost.current, {
      autoSize: true,
      layout: { background: { color: '#0b1421' }, textColor: '#8fa1b8', fontFamily: 'DM Sans, sans-serif' },
      grid: { vertLines: { color: '#1b293a' }, horzLines: { color: '#1b293a' } },
      rightPriceScale: { borderColor: '#26364a' },
      timeScale: { borderColor: '#26364a', timeVisible: true, secondsVisible: false },
      crosshair: { mode: 1 },
    });
    chartRef.current = chart;
    candleSeries.current = chart.addSeries(CandlestickSeries, {
      upColor: '#20c58b', downColor: '#f06f7d', borderUpColor: '#20c58b',
      borderDownColor: '#f06f7d', wickUpColor: '#20c58b', wickDownColor: '#f06f7d',
    });
    ema20Series.current = chart.addSeries(LineSeries, { color: '#f0bd59', lineWidth: 1, title: 'EMA 20', priceLineVisible: false });
    ema50Series.current = chart.addSeries(LineSeries, { color: '#7c8cff', lineWidth: 1, title: 'EMA 50', priceLineVisible: false });
    volumeSeries.current = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' }, priceScaleId: '', priceLineVisible: false,
    });
    chart.priceScale('').applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
    const resize = new ResizeObserver(entries => {
      if (entries[0]) chart.applyOptions({ width: entries[0].contentRect.width });
    });
    resize.observe(chartHost.current);
    return () => { resize.disconnect(); chart.remove(); chartRef.current = null; };
  }, []);

  const runAnalysis = useCallback(async (data: Candle[], symbol: string) => {
    if (data.length < 50) { setAnalysis(null); return; }
    try {
      const response = await fetch(ANALYSIS_API + '/api/v1/analyze', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol, candles: data.slice(-500).map(c => ({ ...c, time: new Date(c.time).toISOString() })) }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || 'Analysis service rejected the candle series');
      setAnalysis(body);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Analysis failed');
    }
  }, []);

  const loadCandles = useCallback(async () => {
    if (!instrument) return;
    setLoading(true); setError(''); setAnalysis(null); setCandles([]); candlesRef.current = [];
    try {
      const params = new URLSearchParams({
        instrument_key: instrument.instrumentKey, unit: timeframe.unit,
        interval: String(timeframe.interval),
      });
      const response = await fetch(MARKET_API + '/api/market/candles?' + params.toString());
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || 'Unable to load market candles');
      const rows: Candle[] = (body.candles || []).map((c: any) => ({
        time: c.time, open: c.open, high: c.high, low: c.low, close: c.close, volume: c.volume,
      }));
      setCandles(rows);
      candlesRef.current = rows;
      minuteVolumesRef.current.clear();
      if (rows.length) {
        const closes = rows.map(c => c.close);
        candleSeries.current?.setData(rows.map(c => ({ time: chartTime(c.time), open: c.open, high: c.high, low: c.low, close: c.close })));
        ema20Series.current?.setData(ema(closes, 20).map((value, index) => ({ time: chartTime(rows[index].time), value })));
        ema50Series.current?.setData(ema(closes, 50).map((value, index) => ({ time: epoch(rows[index].time), value })));
        volumeSeries.current?.setData(rows.map(c => ({ time: epoch(c.time), value: c.volume, color: c.close >= c.open ? 'rgba(32,197,139,.35)' : 'rgba(240,111,125,.35)' })));
        chartRef.current?.timeScale().fitContent();
        await runAnalysis(rows, instrument.symbol);
      } else {
        setError('No candles returned for this instrument/timeframe.');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Live market request failed');
    } finally {
      setLoading(false);
    }
  }, [instrument, timeframe, runAnalysis]);

  useEffect(() => { loadCandles(); }, [loadCandles]);

  useEffect(() => {
    if (!instrument) return;
    const url = 'ws://localhost:8002/api/market/stream?instrument_keys=' + encodeURIComponent(instrument.instrumentKey);
    const ws = new WebSocket(url);
    ws.onopen = () => setStreamState('CONNECTED');
    ws.onerror = () => setStreamState('ERROR');
    ws.onclose = () => setStreamState('DISCONNECTED');
    ws.onmessage = event => {
      try {
        const message = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;
        if (message.type === 'error' || message.type === 'stream_error') {
          setStreamState('ERROR');
          setError(message.message || 'Market stream error');
          return;
        }
        if (message.type === 'stream_status') { setStreamState('LIVE'); return; }
        const feed = message.feeds?.[instrument.instrumentKey];
        if (!feed) return;
        const full = feed.fullFeed?.marketFF || feed.fullFeed || {};
        const quote = full.marketOHLC?.ohlc || feed.marketOHLC?.ohlc || [];
        const dayCandle = quote.find((item: any) => item.interval === '1d');
        const minute = quote.find((item: any) => item.interval === 'I1');
        const ltpc = feed.ltpc || full.ltpc;
        let next: Candle | null = null;

        if (timeframe.label === '1D' && dayCandle) {
          const rawTime = Number(dayCandle.ts);
          const timestamp = rawTime > 1e12 ? rawTime : rawTime > 1e9 ? rawTime * 1000 : Date.parse(dayCandle.ts);
          next = {
            time: new Date(timestamp).toISOString(),
            open: Number(dayCandle.open), high: Number(dayCandle.high), low: Number(dayCandle.low),
            close: Number(dayCandle.close), volume: Number(dayCandle.vol || 0),
          };
        } else if (minute) {
          const rawTime = Number(minute.ts);
          const minuteDate = new Date(rawTime > 1e12 ? rawTime : rawTime > 1e9 ? rawTime * 1000 : Date.parse(minute.ts));
          const minuteEpoch = Math.floor(minuteDate.getTime() / 1000);
          const bucketSeconds = timeframe.label === '1m' ? 60 : timeframe.label === '5m' ? 300 : timeframe.label === '15m' ? 900 : timeframe.label === '1H' ? 3600 : 86400;
          const istDate = new Date((minuteEpoch + 19800) * 1000);
          const istMidnight = Date.UTC(istDate.getUTCFullYear(), istDate.getUTCMonth(), istDate.getUTCDate()) / 1000 - 19800;
          const sessionStart = istMidnight + 9 * 3600 + 15 * 60;
          const bucketEpoch = sessionStart + Math.floor((minuteEpoch - sessionStart) / bucketSeconds) * bucketSeconds;
          const current = candlesRef.current[candlesRef.current.length - 1];
          const currentBucket = current ? Math.floor((epoch(current.time) - sessionStart) / bucketSeconds) * bucketSeconds + sessionStart : -1;
          const minuteVolume = Number(minute.vol || 0);
          if (current && currentBucket === bucketEpoch) {
            const previousMinuteVolume = minuteVolumesRef.current.get(minuteEpoch) || 0;
            next = {
              time: new Date(bucketEpoch * 1000).toISOString(), open: current.open,
              high: Math.max(current.high, Number(minute.high)), low: Math.min(current.low, Number(minute.low)),
              close: Number(minute.close), volume: Math.max(0, current.volume + minuteVolume - previousMinuteVolume),
            };
          } else if (!current || bucketEpoch > currentBucket) {
            next = {
              time: new Date(bucketEpoch * 1000).toISOString(), open: Number(minute.open),
              high: Number(minute.high), low: Number(minute.low), close: Number(minute.close), volume: minuteVolume,
            };
          }
          minuteVolumesRef.current.set(minuteEpoch, minuteVolume);
        } else if (ltpc?.ltp && candlesRef.current.length) {
          const current = candlesRef.current[candlesRef.current.length - 1];
          const price = Number(ltpc.ltp);
          next = { ...current, high: Math.max(current.high, price), low: Math.min(current.low, price), close: price };
        }

        if (!next) return;
        setCandles(old => {
          const copy = [...old];
          const timestamp = epoch(next!.time);
          const lastIndex = copy.length - 1;
          if (lastIndex >= 0 && epoch(copy[lastIndex].time) === timestamp) copy[lastIndex] = next!;
          else if (lastIndex >= 0 && timestamp > epoch(copy[lastIndex].time)) copy.push(next!);
          else if (lastIndex < 0) copy.push(next!);
          else return old;
          const visible = copy.slice(-2500);
          candlesRef.current = visible;
          candleSeries.current?.update({ time: timestamp as any, open: next!.open, high: next!.high, low: next!.low, close: next!.close });
          volumeSeries.current?.update({ time: timestamp as any, value: next!.volume, color: next!.close >= next!.open ? 'rgba(32,197,139,.35)' : 'rgba(240,111,125,.35)' });
          const closes = visible.map(c => c.close);
          ema20Series.current?.setData(ema(closes, 20).map((value, index) => ({ time: chartTime(visible[index].time), value })));
          ema50Series.current?.setData(ema(closes, 50).map((value, index) => ({ time: chartTime(visible[index].time), value })));
          return visible;
        });
      } catch { /* Ignore malformed provider messages; never fabricate a quote. */ }
    };
    return () => ws.close();
  }, [instrument, timeframe]);

  useEffect(() => {
    const series = candleSeries.current;
    if (!series) return;
    priceLines.current.forEach(line => { try { series.removePriceLine(line); } catch { /* already removed */ } });
    priceLines.current = [];
    if (!analysis) return;
    const lines = [
      { price: analysis.entryReference, color: '#39d7a5', title: 'ENTRY REF' },
      { price: analysis.stopLossReference, color: '#f07883', title: 'STOP' },
      { price: analysis.target1Reference, color: '#75a7ff', title: 'TARGET 1' },
      { price: analysis.target2Reference, color: '#ad8cff', title: 'TARGET 2' },
    ];
    lines.forEach(line => {
      if (line.price !== null && line.price !== undefined) {
        priceLines.current.push(series.createPriceLine({ price: line.price, color: line.color, lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: line.title }));
      }
    });
  }, [analysis]);

  const last = candles[candles.length - 1];
  const rsiValue = useMemo(() => calculateRsi(candles.map(c => c.close)), [candles]);
  const macdValue = useMemo(() => macd(candles.map(c => c.close)), [candles]);

  return <section className="live-terminal panel">
    <div className="live-terminal-head">
      <div><div className="eyebrow">REAL MARKET DATA · READ ONLY</div><h2><CandlestickChart size={19}/> Live market terminal</h2><p>Upstox feed · NSE cash equities · chart, indicators and reference setup levels</p></div>
      <div className="live-status"><span className={streamState === 'LIVE' || streamState === 'CONNECTED' ? 'live-dot' : 'offline-dot'}/>{streamState === 'LIVE' ? 'LIVE STREAM' : streamState}<small>{marketStatus}</small></div>
    </div>
    <div className="live-toolbar">
      <div className="instrument-search"><Search size={16}/><input value={query} onChange={e => setQuery(e.target.value.toUpperCase())} onKeyDown={e => e.key === 'Enter' && search(query)} placeholder="Search NSE symbol or company"/><button onClick={() => search(query)}>Search</button></div>
      <div className="timeframe-tabs">{TIMEFRAMES.map(tf => <button key={tf.label} className={timeframe.label === tf.label ? 'selected' : ''} onClick={() => setTimeframe(tf)}>{tf.label}</button>)}</div>
      <button className="refresh-market" onClick={loadCandles} disabled={loading}><RefreshCw size={14}/>{loading ? 'Loading' : 'Refresh'}</button>
    </div>
    {results.length > 0 && query.trim() && <div className="instrument-results">{results.slice(0,6).map(item => <button key={item.instrumentKey} className={instrument?.instrumentKey === item.instrumentKey ? 'chosen' : ''} onClick={() => { setInstrument(item); setQuery(item.symbol); setResults([]); }}><b>{item.symbol}</b><span>{item.name}</span></button>)}</div>}
    {error && <div className="market-error"><AlertTriangle size={15}/>{error}</div>}
    <div className="live-symbol-row"><div><b>{instrument?.symbol || 'Select instrument'}</b><span>{instrument?.name || 'Search an NSE equity above'}</span><small>{instrument?.instrumentKey || ''}</small></div><div className="live-last">{last ? <><b>₹{last.close.toLocaleString('en-IN',{maximumFractionDigits:2})}</b><span>Latest candle close · {new Date(last.time).toLocaleTimeString('en-IN')}</span></> : <span>Waiting for authenticated market data</span>}</div></div>
    <div className="live-chart-wrap"><div ref={chartHost} className="live-chart"/></div>
    <div className="chart-legend"><span><i className="legend-candle"/> Candles</span><span><i className="legend-ema20"/> EMA 20</span><span><i className="legend-ema50"/> EMA 50</span><span><i className="legend-volume"/> Volume</span><span>Provider: Upstox</span></div>
    <div className="indicator-strip">
      <div><small>RSI 14</small><b>{rsiValue === null ? '—' : rsiValue.toFixed(2)}</b><span>{rsiValue === null ? 'Need 15+ candles' : rsiValue >= 70 ? 'Overbought zone' : rsiValue <= 30 ? 'Oversold zone' : 'Neutral range'}</span></div>
      <div><small>MACD 12/26</small><b>{macdValue.macd === null ? '—' : macdValue.macd.toFixed(3)}</b><span>{macdValue.macd !== null && macdValue.signal !== null ? macdValue.macd >= macdValue.signal ? 'Above signal' : 'Below signal' : 'Need 35+ candles'}</span></div>
      <div><small>EMA 20</small><b>{analysis?.indicators.ema20?.toFixed(2) ?? '—'}</b><span>Short trend</span></div>
      <div><small>EMA 50</small><b>{analysis?.indicators.ema50?.toFixed(2) ?? '—'}</b><span>Trend filter</span></div>
      <div><small>ATR 14</small><b>{analysis?.indicators.atr14?.toFixed(2) ?? '—'}</b><span>Volatility</span></div>
      <div><small>Volume ratio</small><b>{analysis?.indicators.volumeRatio?.toFixed(2) ?? '—'}x</b><span>vs 20-candle avg</span></div>
    </div>
    <div className="setup-panel">
      <div className="setup-panel-title"><div><Activity size={16}/><b>Technical setup indication</b></div><span className={analysis?.setup === 'LONG_WATCH' ? 'setup-long' : analysis?.setup === 'SHORT_WATCH' ? 'setup-short' : 'setup-wait'}>{analysis?.setup || 'WAIT / NO SETUP'}</span></div>
      {analysis ? <><div className="setup-levels">
        <div><small>ENTRY REFERENCE</small><b>{analysis.entryReference ? '₹' + analysis.entryReference.toFixed(2) : '—'}</b></div>
        <div><small>STOP REFERENCE</small><b className="risk-text">{analysis.stopLossReference ? '₹' + analysis.stopLossReference.toFixed(2) : '—'}</b></div>
        <div><small>TARGET 1</small><b className="target-text">{analysis.target1Reference ? '₹' + analysis.target1Reference.toFixed(2) : '—'}</b></div>
        <div><small>TARGET 2</small><b className="target-text">{analysis.target2Reference ? '₹' + analysis.target2Reference.toFixed(2) : '—'}</b></div>
        <div><small>CHECKLIST SCORE</small><b>{analysis.score}/100</b></div>
        <div><small>RISK / REWARD</small><b>{analysis.riskReward || '—'}</b></div>
      </div><p className="invalidation">{analysis.invalidation}</p><div className="confirmation-list">{analysis.confirmations.map(item => <span key={item}>✓ {item}</span>)}</div><div className="analysis-warnings">{analysis.warnings.map(item => <p key={item}>• {item}</p>)}</div></> : <p className="no-setup">Load at least 50 real historical candles and configure your Upstox token to calculate a setup. No synthetic quotes or signals are shown.</p>}
    </div>
    <div className="live-terminal-footer"><Wifi size={14}/> Live prices are provider-delivered and may be subject to provider/exchange permissions and delays. This is an analysis-only tool; it never places orders.</div>
  </section>;
}
