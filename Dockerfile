# Sanad on Railway: one container runs the agents API (FastAPI) + the web UI (Node),
# with Caddy in front on $PORT routing /api/* (HTTP + WebSocket) to the API.

# ---- 1. build the web UI ----
FROM node:22-bookworm-slim AS web
WORKDIR /app
COPY package.json package-lock.json .npmrc ./
RUN npm ci --no-audit --no-fund
COPY . .
# The browser talks to the API through the same origin (/api -> Caddy -> FastAPI).
ENV VITE_SANAD_API_URL=/api
RUN npm run build

# ---- 2. runtime ----
FROM node:22-bookworm-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv python3-pip ca-certificates \
 && rm -rf /var/lib/apt/lists/*
COPY --from=caddy:2.8.4 /usr/bin/caddy /usr/bin/caddy

WORKDIR /app
COPY requirements.txt ./
# mediapipe / opencv are only for building the sign gallery offline: not needed on the server.
RUN python3 -m venv /opt/venv \
 && grep -vE '^(mediapipe|opencv-python)' requirements.txt > /tmp/requirements.txt \
 && /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt

COPY . .
COPY --from=web /app/.output ./.output

ENV PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8 NODE_ENV=production PORT=8080
EXPOSE 8080
CMD ["bash", "deploy/start.sh"]
