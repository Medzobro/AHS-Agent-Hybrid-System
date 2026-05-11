.PHONY: up test down clean build

up:
	python3 bridge/mcp_http_server.py

test:
	python3 -m pytest tests/test_suite.py -v --tb=short -k "not timeout"

test-all:
	python3 -m pytest tests/ -v --tb=short

lint:
	ruff check .

lint-fix:
	ruff check --fix .

build:
	docker build --tag ahs:1.0.0 .

docker:
	docker compose up --build

down:
	docker compose down

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
	find . -type d -name .pyc -exec rm -rf {} + 2>/dev/null

health:
	curl -s http://localhost:18900/health | python3 -m json.tool

dashboard:
	@echo "Open http://localhost:18900 in your browser"
