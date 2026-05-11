# AHS v1.0 — Multi-stage Docker Build
# =====================================

# ---- Stage 1: Base ----
FROM python:3.13-slim AS base
RUN apt-get update -qq && apt-get install -y -qq curl && rm -rf /var/lib/apt/lists/*
WORKDIR /ahs

# ---- Stage 2: Python deps ----
FROM base AS python-deps
COPY pyproject.toml ./
RUN pip install --no-cache-dir aiohttp httpx pydantic pytest pytest-cov ruff

# ---- Stage 3: Final ----
FROM python-deps AS final
COPY . .

# Security: non-root user
RUN useradd -m -s /bin/bash ahs && chown -R ahs:ahs /ahs
USER ahs

ENV AHS_MCP_PORT=18900
ENV AHS_MCP_HOST=0.0.0.0
ENV AHS_VERSION=1.0.0

HEALTHCHECK --interval=10s --timeout=5s --start-period=3s --retries=3 \
  CMD curl -sf http://localhost:18900/health || exit 1

EXPOSE 18900
CMD ["python3", "bridge/mcp_http_server.py"]
