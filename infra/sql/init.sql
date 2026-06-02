-- ============================================================
-- AI Trading Platform - Database Schema
-- PostgreSQL 15
-- ============================================================

-- Assets
CREATE TABLE IF NOT EXISTS assets (
    id          SERIAL PRIMARY KEY,
    symbol      VARCHAR(10) UNIQUE NOT NULL,
    name        TEXT,
    sector      TEXT,
    active      BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO assets (symbol, name, sector) VALUES
  ('AAPL', 'Apple Inc.', 'Technology'),
  ('MSFT', 'Microsoft Corporation', 'Technology'),
  ('NVDA', 'NVIDIA Corporation', 'Technology'),
  ('SPY',  'SPDR S&P 500 ETF', 'ETF')
ON CONFLICT DO NOTHING;

-- Market snapshots OHLCV
CREATE TABLE IF NOT EXISTS market_snapshots (
    id          BIGSERIAL PRIMARY KEY,
    symbol      VARCHAR(10) NOT NULL,
    ts          TIMESTAMPTZ NOT NULL,
    open        NUMERIC(12,4),
    high        NUMERIC(12,4),
    low         NUMERIC(12,4),
    close       NUMERIC(12,4),
    volume      BIGINT,
    vwap        NUMERIC(12,4),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (symbol, ts)
);

CREATE INDEX IF NOT EXISTS idx_snapshots_symbol_ts
    ON market_snapshots (symbol, ts DESC);

-- Signals generati da ogni agente
CREATE TABLE IF NOT EXISTS signals (
    id              BIGSERIAL PRIMARY KEY,
    signal_batch_id UUID NOT NULL,
    symbol          VARCHAR(10) NOT NULL,
    agent           VARCHAR(50) NOT NULL,
    signal          VARCHAR(10) NOT NULL,
    confidence      NUMERIC(5,4),
    rationale       TEXT,
    raw_output      JSONB,
    ts              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signals_symbol_ts
    ON signals (symbol, ts DESC);

-- Valutazioni Risk Engine
CREATE TABLE IF NOT EXISTS risk_evaluations (
    id              BIGSERIAL PRIMARY KEY,
    signal_batch_id UUID NOT NULL,
    symbol          VARCHAR(10) NOT NULL,
    approved        BOOLEAN NOT NULL,
    rejection_reason TEXT,
    checks          JSONB,
    ts              TIMESTAMPTZ DEFAULT NOW()
);

-- Decisioni di trade
CREATE TABLE IF NOT EXISTS trade_decisions (
    id              BIGSERIAL PRIMARY KEY,
    decision_id     UUID UNIQUE NOT NULL,
    signal_batch_id UUID,
    symbol          VARCHAR(10) NOT NULL,
    action          VARCHAR(10) NOT NULL,
    quantity        NUMERIC(12,4),
    rationale       TEXT,
    agent_votes     JSONB,
    conviction_score NUMERIC(5,4),
    risk_approved   BOOLEAN DEFAULT FALSE,
    pm_approved     BOOLEAN DEFAULT FALSE,
    status          VARCHAR(20) DEFAULT 'PENDING',
    ts              TIMESTAMPTZ DEFAULT NOW()
);

-- Ordini inviati al broker
CREATE TABLE IF NOT EXISTS orders (
    id              BIGSERIAL PRIMARY KEY,
    decision_id     UUID,
    broker_order_id TEXT,
    symbol          VARCHAR(10) NOT NULL,
    side            VARCHAR(10),
    qty             NUMERIC(12,4),
    order_type      VARCHAR(20),
    status          VARCHAR(20),
    filled_qty      NUMERIC(12,4),
    filled_avg_price NUMERIC(12,4),
    submitted_at    TIMESTAMPTZ,
    filled_at       TIMESTAMPTZ,
    error_msg       TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Posizioni aperte
CREATE TABLE IF NOT EXISTS positions (
    id              BIGSERIAL PRIMARY KEY,
    symbol          VARCHAR(10) UNIQUE NOT NULL,
    qty             NUMERIC(12,4) DEFAULT 0,
    avg_entry_price NUMERIC(12,4),
    current_price   NUMERIC(12,4),
    unrealized_pnl  NUMERIC(12,4),
    realized_pnl    NUMERIC(12,4) DEFAULT 0,
    opened_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Audit log eventi sistema
CREATE TABLE IF NOT EXISTS audit_log (
    id              BIGSERIAL PRIMARY KEY,
    event_type      VARCHAR(50),
    severity        VARCHAR(10) DEFAULT 'INFO',
    source          VARCHAR(50),
    message         TEXT,
    payload         JSONB,
    ts              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_ts
    ON audit_log (ts DESC);

-- Stato sistema (chiave-valore)
CREATE TABLE IF NOT EXISTS system_state (
    key             VARCHAR(50) PRIMARY KEY,
    value           TEXT,
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO system_state (key, value) VALUES
  ('trading_enabled', 'true'),
  ('kill_switch', 'false'),
  ('daily_pnl', '0'),
  ('total_drawdown', '0'),
  ('current_positions', '0'),
  ('last_signal_run', ''),
  ('platform_version', '1.0.0')
ON CONFLICT DO NOTHING;

-- Metriche performance trading
CREATE TABLE IF NOT EXISTS performance_metrics (
    id              BIGSERIAL PRIMARY KEY,
    date            DATE UNIQUE NOT NULL,
    daily_pnl       NUMERIC(12,4) DEFAULT 0,
    cumulative_pnl  NUMERIC(12,4) DEFAULT 0,
    drawdown        NUMERIC(8,4) DEFAULT 0,
    win_count       INTEGER DEFAULT 0,
    loss_count      INTEGER DEFAULT 0,
    total_trades    INTEGER DEFAULT 0,
    win_rate        NUMERIC(5,4),
    sharpe_daily    NUMERIC(8,4),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
