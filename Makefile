.PHONY: help build up down restart logs shell clean test lint format install dev-install

help:
	@echo "Microcenter Product Watcher - Available Commands"
	@echo ""
	@echo "Docker Commands:"
	@echo "  make build       - Build Docker image"
	@echo "  make up          - Start container in background"
	@echo "  make down        - Stop and remove container"
	@echo "  make restart     - Restart container"
	@echo "  make logs        - View container logs (tail mode)"
	@echo "  make shell       - Open shell in running container"
	@echo "  make clean       - Remove containers, images, and volumes"
	@echo ""
	@echo "Development Commands:"
	@echo "  make install     - Install package in editable mode"
	@echo "  make dev-install - Install with dev dependencies"
	@echo "  make test        - Run tests"
	@echo "  make lint        - Run linting (ruff + pylint)"
	@echo "  make format      - Format code with ruff"
	@echo ""

# Docker commands
build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f --tail=100

shell:
	docker-compose exec microcenter-watcher /bin/bash

clean:
	docker-compose down -v
	docker rmi microcenter-product-watcher:latest || true

# Development commands
install:
	pip install -e .

dev-install:
	pip install -e ".[dev]"

test:
	pytest -v

lint:
	@echo "Running Ruff linter..."
	ruff check stock_checker/ tests/
	@echo ""
	@echo "Running Pylint..."
	pylint stock_checker/

format:
	ruff format stock_checker/ tests/
	@echo "Code formatted successfully!"
