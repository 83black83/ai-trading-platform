.PHONY: help setup build up down restart logs clean ps shell-api shell-db test lint format

# Default target
help:
	@echo "AI Trading Platform - Makefile Commands"
	@echo "========================================"
	@echo "setup      - Copia .env.example in .env"
	@echo "build      - Build di tutti i container Docker"
	@echo "up         - Avvia tutti i servizi"
	@echo "up-d       - Avvia tutti i servizi in background"
	@echo "down       - Ferma tutti i servizi"
	@echo "restart    - Riavvia tutti i servizi"
	@echo "logs       - Mostra i log di tutti i servizi"
	@echo "logs-api   - Mostra i log del servizio API"
	@echo "logs-signals - Mostra i log del worker signals"
	@echo "logs-exec  - Mostra i log del worker execution"
	@echo "ps         - Mostra lo stato dei container"
	@echo "clean      - Rimuove container, volumi e network"
	@echo "shell-api  - Apri shell nel container API"
	@echo "shell-db   - Apri shell PostgreSQL"
	@echo "db-reset   - Reset completo del database"
	@echo "test       - Esegui i test"
	@echo "lint       - Esegui linting del codice"
	@echo "format     - Formatta il codice con black"

# Setup iniziale
setup:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✓ File .env creato da .env.example"; \
		echo "⚠️  IMPORTANTE: Modifica .env con le tue credenziali!"; \
	else \
		echo "✓ File .env già esistente"; \
	fi

# Build dei container
build:
	@echo "🔨 Building Docker containers..."
	docker-compose build

# Avvia i servizi
up:
	@echo "🚀 Starting services..."
	docker-compose up

up-d:
	@echo "🚀 Starting services in background..."
	docker-compose up -d
	@echo "✓ Services started. Access:"
	@echo "  - Dashboard: http://localhost:3000"
	@echo "  - API: http://localhost:8000"
	@echo "  - API Docs: http://localhost:8000/docs"

# Ferma i servizi
down:
	@echo "🛑 Stopping services..."
	docker-compose down

# Riavvia i servizi
restart:
	@echo "🔄 Restarting services..."
	docker-compose restart

# Mostra i log
logs:
	docker-compose logs -f

logs-api:
	docker-compose logs -f api

logs-signals:
	docker-compose logs -f worker_signals

logs-exec:
	docker-compose logs -f worker_execution

logs-notify:
	docker-compose logs -f worker_notify

logs-db:
	docker-compose logs -f postgres

# Mostra lo stato
ps:
	docker-compose ps

# Pulizia completa
clean:
	@echo "🧹 Cleaning up..."
	docker-compose down -v --remove-orphans
	docker system prune -f
	@echo "✓ Cleanup completed"

# Shell nei container
shell-api:
	docker-compose exec api /bin/bash

shell-db:
	docker-compose exec postgres psql -U trading -d trading_db

shell-redis:
	docker-compose exec redis redis-cli

# Database operations
db-reset:
	@echo "⚠️  Resetting database..."
	docker-compose down -v
	docker-compose up -d postgres
	@echo "✓ Database reset completed"

db-backup:
	@echo "💾 Backing up database..."
	docker-compose exec -T postgres pg_dump -U trading trading_db > backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "✓ Backup completed"

db-restore:
	@if [ -z "$(FILE)" ]; then \
		echo "❌ Usage: make db-restore FILE=backup.sql"; \
		exit 1; \
	fi
	@echo "📥 Restoring database from $(FILE)..."
	docker-compose exec -T postgres psql -U trading trading_db < $(FILE)
	@echo "✓ Restore completed"

# Testing
test:
	@echo "🧪 Running tests..."
	docker-compose exec api pytest tests/ -v

test-cov:
	@echo "🧪 Running tests with coverage..."
	docker-compose exec api pytest tests/ -v --cov=. --cov-report=html

# Linting e formatting
lint:
	@echo "🔍 Running linters..."
	docker-compose exec api flake8 .
	docker-compose exec api mypy .

format:
	@echo "🎨 Formatting code..."
	docker-compose exec api black .
	docker-compose exec api isort .

# Health checks
health:
	@echo "🏥 Checking services health..."
	@curl -s http://localhost:8000/health | jq .

# Quick start (first time setup)
quickstart: setup build up-d
	@echo "✅ Platform is running!"
	@echo "📊 Open http://localhost:3000 for dashboard"
	@echo "📚 Open http://localhost:8000/docs for API docs"

# Development mode (con hot reload)
dev:
	@echo "🔧 Starting in development mode..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
