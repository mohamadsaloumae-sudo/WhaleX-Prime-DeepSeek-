.PHONY: help up down build logs shell clean restart

help:
	@echo "🐋 WhaleX Prime - Commands:"
	@echo "  make up       - Start all services"
	@echo "  make down     - Stop all services"
	@echo "  make build    - Rebuild images"
	@echo "  make logs     - View logs"
	@echo "  make shell    - Enter backend shell"
	@echo "  make clean    - Clean volumes"
	@echo "  make restart  - Restart all services"

up:
	docker-compose up -d
	@echo "✅ Services started at http://localhost"

down:
	docker-compose down
	@echo "✅ Services stopped"

build:
	docker-compose build
	@echo "✅ Images rebuilt"

logs:
	docker-compose logs -f

shell:
	docker-compose exec backend bash

clean:
	docker-compose down -v
	@echo "✅ Volumes cleaned"

restart: down up
	@echo "✅ Services restarted"