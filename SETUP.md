# 🚀 Setup e Deployment - AI Trading Platform

## 📋 Prerequisiti

Prima di iniziare, assicurati di avere installato:

- **Docker** (versione 20.10+)
- **Docker Compose** (versione 2.0+)
- **Make** (opzionale, ma consigliato)
- **Git**

### Verifica installazione

```bash
docker --version
docker-compose --version
make --version
```

## 🔑 Credenziali Necessarie

### 1. Alpaca (Paper Trading)

Registrati su [Alpaca Markets](https://alpaca.markets/) e ottieni:
- API Key
- API Secret
- Modalità: Paper Trading

### 2. Telegram Bot (Notifiche)

1. Crea un bot tramite [@BotFather](https://t.me/BotFather)
2. Salva il **Bot Token**
3. Ottieni il tuo **Chat ID** usando [@userinfobot](https://t.me/userinfobot)

### 3. Interactive Brokers (Opzionale - Live Trading Futuro)

Per ora non necessario (MVP usa solo Alpaca paper trading).

## ⚙️ Installazione Rapida

### Opzione 1: Con Make (Consigliato)

```bash
# 1. Clona il repository
git clone https://github.com/83black83/ai-trading-platform.git
cd ai-trading-platform

# 2. Setup e avvio automatico
make quickstart
```

Questo comando eseguirà automaticamente:
- Copia di `.env.example` in `.env`
- Build dei container Docker
- Avvio di tutti i servizi

### Opzione 2: Manuale

```bash
# 1. Clona il repository
git clone https://github.com/83black83/ai-trading-platform.git
cd ai-trading-platform

# 2. Copia il file di configurazione
cp .env.example .env

# 3. Modifica .env con le tue credenziali
nano .env  # oppure usa il tuo editor preferito

# 4. Build dei container
docker-compose build

# 5. Avvia i servizi
docker-compose up -d
```

## 🔧 Configurazione .env

**IMPORTANTE**: Dopo aver copiato `.env.example` in `.env`, modifica ALMENO queste variabili:

```bash
# Database (cambia le password!)
POSTGRES_PASSWORD=tua_password_sicura
REDIS_URL=redis://redis:6379/0

# Alpaca API (Paper Trading)
ALPACA_API_KEY=tua_alpaca_api_key
ALPACA_API_SECRET=tuo_alpaca_secret
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Telegram Bot
TELEGRAM_BOT_TOKEN=tuo_bot_token
TELEGRAM_CHAT_ID=tuo_chat_id

# Trading Mode
API_ENV=paper  # NON cambiare in produzione finché non testato!
```

## 📊 Verifica Installazione

### 1. Controlla i servizi attivi

```bash
make ps
# oppure
docker-compose ps
```

Dovresti vedere 7 servizi running:
- `trading_postgres`
- `trading_redis`
- `trading_api`
- `trading_signals`
- `trading_execution`
- `trading_notify`
- `trading_dashboard`

### 2. Verifica i log

```bash
# Log di tutti i servizi
make logs

# Log specifici
make logs-api
make logs-signals
make logs-exec
```

### 3. Health Check API

```bash
# Verifica health
curl http://localhost:8000/health

# oppure con make
make health
```

### 4. Accedi alle interfacce

- **Dashboard Web**: http://localhost:3000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **API ReDoc**: http://localhost:8000/redoc
- **PostgreSQL**: `localhost:5432` (user: trading, db: trading_db)
- **Redis**: `localhost:6379`

## 🗄️ Database

### Inizializzazione

Il database viene inizializzato automaticamente all'avvio tramite `infra/sql/init.sql`.

Tabelle create:
- `assets` - Asset monitorati
- `market_snapshots` - Snapshot di mercato
- `signals` - Segnali generati dagli agenti
- `risk_evaluations` - Valutazioni di rischio
- `trade_decisions` - Decisioni di trading
- `orders` - Ordini eseguiti
- `positions` - Posizioni aperte
- `audit_log` - Log di audit
- `system_state` - Stato del sistema
- `metrics` - Metriche performance

### Accesso Diretto

```bash
# Shell PostgreSQL
make shell-db
# oppure
docker-compose exec postgres psql -U trading -d trading_db
```

### Backup e Restore

```bash
# Backup
make db-backup

# Restore
make db-restore FILE=backup_20260602_220000.sql

# Reset completo (⚠️ CANCELLA TUTTI I DATI!)
make db-reset
```

## 🔍 Troubleshooting

### Problema: Container non si avviano

```bash
# 1. Controlla i log
make logs

# 2. Verifica porte occupate
sudo netstat -tulpn | grep -E '(3000|8000|5432|6379)'

# 3. Riavvia i servizi
make restart
```

### Problema: Database connection error

```bash
# 1. Verifica che postgres sia running
docker-compose ps postgres

# 2. Controlla i log del database
make logs-db

# 3. Reset database
make db-reset
```

### Problema: Alpaca API errors

```bash
# Verifica credenziali nel .env
cat .env | grep ALPACA

# Testa connessione manualmente
curl -X GET "https://paper-api.alpaca.markets/v2/account" \
  -H "APCA-API-KEY-ID: tua_key" \
  -H "APCA-API-SECRET-KEY: tuo_secret"
```

### Problema: Out of memory

```bash
# Aumenta memoria Docker (Docker Desktop)
# Settings > Resources > Memory: almeno 4GB

# Oppure riduci worker concurrency nel .env
WORKER_CONCURRENCY=1
```

## 🛠️ Comandi Utili (Make)

### Gestione Servizi

```bash
make help          # Mostra tutti i comandi disponibili
make build         # Build dei container
make up            # Avvia i servizi (foreground)
make up-d          # Avvia i servizi (background)
make down          # Ferma i servizi
make restart       # Riavvia i servizi
make ps            # Stato dei container
make clean         # Pulizia completa (container + volumi)
```

### Log e Debugging

```bash
make logs          # Log di tutti i servizi
make logs-api      # Log API
make logs-signals  # Log worker signals
make logs-exec     # Log worker execution
make logs-notify   # Log notifiche Telegram
make logs-db       # Log database
```

### Shell e Database

```bash
make shell-api     # Shell nel container API
make shell-db      # Shell PostgreSQL
make shell-redis   # Shell Redis CLI
make db-backup     # Backup database
make db-restore    # Restore database
make db-reset      # Reset database
```

### Testing e Quality

```bash
make test          # Esegui test
make test-cov      # Test con coverage
make lint          # Linting
make format        # Formatta codice
make health        # Health check API
```

## 🔐 Sicurezza

### Best Practices

1. **NON committare mai il file `.env`** (già in .gitignore)
2. **Cambia le password di default** in `.env`
3. **Usa paper trading** finché non sei sicuro del sistema
4. **Limita l'accesso esterno**: i servizi dovrebbero essere esposti solo su localhost
5. **Backup regolari** del database

### Firewall (Opzionale)

```bash
# Ubuntu/Debian - Blocca accesso esterno
sudo ufw deny 5432/tcp  # PostgreSQL
sudo ufw deny 6379/tcp  # Redis
sudo ufw allow 3000/tcp # Dashboard (solo se necessario)
sudo ufw allow 8000/tcp # API (solo se necessario)
```

## 📈 Monitoraggio

### Metriche Real-Time

- Dashboard Web: http://localhost:3000
- Telegram: riceverai notifiche su segnali e ordini

### Log Aggregati

```bash
# Segui tutti i log in tempo reale
make logs

# Filtra per servizio
make logs-signals | grep "SIGNAL_GENERATED"
make logs-exec | grep "ORDER_"
```

### Database Queries

```sql
-- Segnali recenti
SELECT * FROM signals ORDER BY timestamp DESC LIMIT 10;

-- Posizioni aperte
SELECT * FROM positions WHERE status = 'open';

-- Performance
SELECT * FROM metrics ORDER BY timestamp DESC LIMIT 5;
```

## 🚦 Modalità Sviluppo

```bash
# Avvia con hot-reload (se configurato)
make dev

# Oppure monta volumi per sviluppo
docker-compose up -v $(pwd):/app
```

## 🔄 Aggiornamenti

```bash
# 1. Pull le ultime modifiche
git pull origin main

# 2. Rebuild dei container
make build

# 3. Riavvia
make restart
```

## 📞 Supporto

- **Issues**: https://github.com/83black83/ai-trading-platform/issues
- **Telegram**: (se disponibile)
- **Docs**: README.md principale

## ⚠️ Disclaimer

**Questo software è fornito "as-is" senza garanzie.**

Il trading comporta rischi significativi. Usa sempre:
1. **Paper trading** per testare
2. **Piccole somme** inizialmente
3. **Stop loss** appropriati
4. **Monitoraggio costante**

**Non investire denaro che non puoi permetterti di perdere.**

---

## ✅ Checklist Post-Installazione

- [ ] Clonato repository
- [ ] Copiato `.env.example` in `.env`
- [ ] Configurato credenziali Alpaca
- [ ] Configurato Telegram Bot
- [ ] Eseguito `make quickstart` o equivalente
- [ ] Verificato 7 servizi running (`make ps`)
- [ ] Accesso Dashboard (http://localhost:3000)
- [ ] Accesso API Docs (http://localhost:8000/docs)
- [ ] Health check OK (`make health`)
- [ ] Testato notifiche Telegram
- [ ] Backup database configurato

🎉 **Congratulazioni! La piattaforma è pronta.**
