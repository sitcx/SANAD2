# Sanad on Render: web UI + agents API in one service (see deploy/start.mjs).
FROM node:22-bookworm-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv python3-pip \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python packages in a venv (Debian blocks system-wide pip installs)
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" SANAD_PYTHON=/opt/venv/bin/python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Web packages
COPY package.json package-lock.json .npmrc ./
RUN npm ci --no-audit --no-fund

COPY . .
# Same origin: the browser calls /api on this service. Must be set at build time.
ENV VITE_SANAD_API_URL=/api
RUN npm run build

ENV NODE_ENV=production
CMD ["node", "deploy/start.mjs"]
