// Production launcher (Render): one public port for the whole app.
//
//   node deploy/start.mjs
//
// Starts the agents API (uvicorn, internal port 8010) and the web server (internal port 3000),
// then listens on $PORT and forwards everything to the web server, which already forwards
// /api/* to the API. WebSocket upgrades on /api/* (live captions) go straight to the API,
// because the web server's proxy only handles plain HTTP. If either process stops, this exits
// so Render restarts the service.
import { spawn } from 'node:child_process';
import http from 'node:http';
import net from 'node:net';

const PORT = Number(process.env.PORT || 10000);
const API_PORT = 8010;
const WEB_PORT = 3000;
const PYTHON = process.env.SANAD_PYTHON || 'python3';

const children = [];
function start(name, cmd, args, env = {}) {
  const child = spawn(cmd, args, { stdio: 'inherit', env: { ...process.env, ...env } });
  child.on('exit', (code) => {
    console.error(`[${name}] stopped (exit code ${code}) - shutting down`);
    for (const c of children) c.kill();
    process.exit(code || 1);
  });
  children.push(child);
}

start('api', PYTHON, ['-m', 'uvicorn', 'src.agent.api:app', '--host', '127.0.0.1', '--port', String(API_PORT)],
  { PYTHONUNBUFFERED: '1', PYTHONIOENCODING: 'utf-8' });
start('web', 'node', ['.output/server/index.mjs'], { PORT: String(WEB_PORT), HOST: '127.0.0.1' });

const server = http.createServer((req, res) => {
  const upstream = http.request(
    { host: '127.0.0.1', port: WEB_PORT, method: req.method, path: req.url, headers: req.headers },
    (up) => { res.writeHead(up.statusCode || 502, up.headers); up.pipe(res); },
  );
  upstream.on('error', () => { if (!res.headersSent) res.writeHead(502); res.end('Sanad is starting, try again in a moment.'); });
  req.pipe(upstream);
});

// WebSocket: /api/interview/... -> API /interview/...
server.on('upgrade', (req, socket, head) => {
  const path = req.url.startsWith('/api/') ? req.url.slice(4) : req.url;
  const target = req.url.startsWith('/api/') ? API_PORT : WEB_PORT;
  const upstream = net.connect(target, '127.0.0.1', () => {
    const headers = Object.entries(req.headers).map(([k, v]) => `${k}: ${v}`).join('\r\n');
    upstream.write(`${req.method} ${path} HTTP/1.1\r\n${headers}\r\n\r\n`);
    if (head?.length) upstream.write(head);
    upstream.pipe(socket);
    socket.pipe(upstream);
  });
  upstream.on('error', () => socket.destroy());
  socket.on('error', () => upstream.destroy());
});

server.listen(PORT, '0.0.0.0', () => console.log(`Sanad listening on port ${PORT}`));
for (const sig of ['SIGTERM', 'SIGINT']) process.on(sig, () => { for (const c of children) c.kill(); process.exit(0); });
