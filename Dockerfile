FROM python:3.13-slim

WORKDIR /ahs

# Python dependencies
COPY bridge/ bridge/
COPY system/ system/
COPY core/ core/
COPY skills/ skills/
COPY ts-core/ ts-core/

COPY main.py .
COPY demo.py .
COPY CHANGELOG.md .
COPY README.md .
COPY .ahsrc .

# Install Node.js for TypeScript Core
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g typescript && \
    cd ts-core && npm install && npx tsc && cd .. && \
    rm -rf /var/lib/apt/lists/*

# Expose ports
EXPOSE 18900 18805

# Default: start MCP HTTP Bridge + TS Gateway
CMD python3 bridge/mcp_http_server.py & sleep 2 && \
    AHS_GATEWAY_PORT=18805 AHS_MCP_PORT=18900 node ts-core/dist/index.js
