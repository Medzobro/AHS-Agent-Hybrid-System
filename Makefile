.PHONY: all up down restart test clean docker

all: down build up

build:
	npm install --prefix ts-core && npx tsc -p ts-core/

up:
	@echo "🤝 Starting AHS..."
	@python3 bridge/mcp_http_server.py &
	@sleep 2
	@AHS_GATEWAY_PORT=18805 AHS_MCP_PORT=18900 node ts-core/dist/index.js &

down:
	@echo "👋 Stopping AHS..."
	@pkill -f "mcp_http_server" 2>/dev/null || true
	@pkill -f "node.*dist/index" 2>/dev/null || true
	@sleep 1

restart: down up

test:
	@echo "🔍 Testing AHS..."
	@curl -s http://localhost:18900/health && echo " [MCP OK]" || echo " [MCP FAIL]"
	@curl -s http://localhost:18805/health && echo " [TS OK]" || echo " [TS FAIL]"
	@echo "Testing task..."
	@curl -m 30 -s -X POST http://localhost:18900/task \
	  -H 'Content-Type: application/json' \
	  -d '{"task":"Say: test","mode":"hybrid"}'
	@echo ""
	@echo "Testing quick mode..."
	@curl -s -X POST http://localhost:18900/web_search \
	  -H 'Content-Type: application/json' \
	  -d '{"query":"AHS Agent Hybrid System","count":2}' | python3 -c "import sys,json; print(f'Search: {json.load(sys.stdin)[\"count\"]} results')"
	@curl -s -X POST http://localhost:18900/memory \
	  -H 'Content-Type: application/json' \
	  -d '{"action":"stats","key":""}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Memory: {d[\"unique_keys\"]} keys')"

docker:
	docker compose up --build -d

clean:
	rm -rf ts-core/node_modules ts-core/dist __pycache__ .pytest_cache
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
