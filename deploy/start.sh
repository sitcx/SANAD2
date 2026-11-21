#!/usr/bin/env bash
# Starts the agents API, the web server and the Caddy proxy; exits if any of them stops.
set -u
cd /app
mkdir -p instance src/logger/logs
export PORT="${PORT:-8080}"

/opt/venv/bin/uvicorn src.agent.api:app --host 127.0.0.1 --port 8010 --proxy-headers &
HOST=127.0.0.1 NITRO_HOST=127.0.0.1 PORT=3000 NITRO_PORT=3000 node .output/server/index.mjs &
caddy run --config deploy/Caddyfile --adapter caddyfile &

wait -n
code=$?
echo "A Sanad process stopped (exit code $code) - shutting down." >&2
kill 0 2>/dev/null
exit "$code"
