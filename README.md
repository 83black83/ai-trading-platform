# AI Trading Platform

> Piattaforma multi-agent per paper trading su azioni USA large cap.
> Stack: Python · Docker · FastAPI · LangGraph · Alpaca · PostgreSQL · Redis · Telegram · React

---

## Architettura

```
ai-trading-platform/
├── apps/
│   ├── api/                    # FastAPI backend
│   ├── dashboard/              # React frontend
│   ├── worker-signals/         # Workflow agenti AI
│   ├── worker-execution/       # Esecuzione ordini Alpaca
│   └── worker-notify/          # Telegram bot
├── services/
│   ├── market_data/            # Acquisizione dati mercato
│   ├── feature_engine/         # Indicatori tecnici
│   ├── risk_engine/            # Controllo rischio
│   ├── portfolio_manager/      # Decisione finale trade
│   └── broker_adapters/        # Adapter Alpaca / IBKR
├── agents/
│   ├── technical/              # Analisi tecnica
│   ├── sentiment/              # Sentiment analysis
│   ├── news/                   # Analisi notizie
│   ├── bull_researcher/        # Tesi rialzista
│   ├── bear_researcher/        # Tesi ribassista
│   └── supervisor/             # Orchestratore workflow
├── backtests/                  # Backtest engine
├── configs/                    # YAML configurazioni
├── infra/
│   ├── sql/                    # Schema PostgreSQL
│   └── docker/                 # Dockerfile servizi
├── tests/                      # Test unitari e integrazione
├── docker-compose.yml
├── .env.example
└── Makefile
```

---

## Stack tecnico

| Area | Tecnologia |
|---|---|
| Linguaggio | Python 3.11 |
| Orchestrazione agenti | LangGraph |
| LLM | OpenAI GPT-4o |
| Backend API | FastAPI |
| Database | PostgreSQL 15 |
| Cache / Queue | Redis 7 |
| Broker MVP | Alpaca (paper trading) |
| Broker live | Interactive Brokers |
| Containerizzazione | Docker + Docker Compose |
| Alerting | Telegram Bot |
| Frontend | React + TailwindCSS |
| Backtest | VectorBT |

---

## Agenti

| Agente | Funzione |
|---|---|
| Technical Analyst | Analisi OHLCV, RSI, MACD, BB, EMA, ATR |
| News Analyst | Analisi notizie ultime 24h |
| Sentiment Analyst | Sentiment da news e social |
| Bull Researcher | Costruisce la tesi rialzista |
| Bear Researcher | Costruisce la tesi ribassista |
| Risk Agent | Controlla limiti posizione e drawdown |
| Portfolio Manager | Decisione finale e sizing |

---

## Asset monitorati

- **AAPL** - Apple Inc.
- **MSFT** - Microsoft Corporation
- **NVDA** - NVIDIA Corporation
- **SPY** - SPDR S&P 500 ETF

---

## Flusso operativo giornaliero

```
1. Acquisizione dati mercato + news
2. Calcolo feature e indicatori tecnici
3. Esecuzione agenti di analisi (paralleli)
4. Dibattito bull vs bear
5. Valutazione Risk Engine
6. Approvazione Portfolio Manager
7. Esecuzione ordine su Alpaca paper
8. Log decisionale + alert Telegram
9. Aggiornamento dashboard
```

---

## Configurazione rapida

```bash
# 1. Clona il repository
git clone https://github.com/83black83/ai-trading-platform.git
cd ai-trading-platform

# 2. Configura le variabili d'ambiente
cp .env.example .env
# Modifica .env con le tue API key

# 3. Avvia i container
docker-compose up -d

# 4. Verifica i servizi
docker-compose ps

# 5. Apri la dashboard
open http://localhost:3000

# 6. API docs
open http://localhost:8000/docs
```

---

## Comandi Telegram

| Comando | Funzione |
|---|---|
| `/status` | Stato servizi e mercato |
| `/positions` | Posizioni aperte |
| `/signals` | Ultimi segnali |
| `/risk` | Riepilogo rischio |
| `/pause` | Sospendi nuove esecuzioni |
| `/resume` | Riattiva workflow |
| `/kill` | Emergency stop |
| `/approve <id>` | Approva trade manualmente |

---

## Policy di rischio (default)

- Max posizioni aperte: **3**
- Max size per trade: **10% portafoglio**
- Stop loss per trade: **3%**
- Max perdita giornaliera: **2%**
- Max drawdown totale: **8%**
- Short selling: **disabilitato**
- Leva: **disabilitata**

---

## Roadmap

- [x] Fase 1: Repository, Docker, DB, Telegram base
- [ ] Fase 2: Market Data, Feature Engine, Execution
- [ ] Fase 3: Agenti AI multi-agent con LangGraph
- [ ] Fase 4: Backtest e walk-forward
- [ ] Fase 5: Dashboard React completa
- [ ] Fase 6: Adapter Interactive Brokers + live

---

## Disclaimer

Questo progetto e' destinato esclusivamente a scopi di ricerca e simulazione (paper trading).
Non costituisce consulenza finanziaria. I risultati passati non garantiscono risultati futuri.
Usare sempre con capitale che ci si puo' permettere di perdere e con limiti di rischio rigidi.
