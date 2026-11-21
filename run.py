"""Sanad launcher: one command to set up, run and test the whole project.

    python run.py            start the agents API (port 8010) and the web UI (port 3000) together
    python run.py setup      first time: create .venv, install Python + web packages, create .env
    python run.py api        agents API only
    python run.py web        web UI only
    python run.py test       run the Python and web tests

Ctrl+C stops everything. Works with any Python 3.10+: it switches to .venv automatically.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
VENV_PYTHON = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
API_PORT = int(os.getenv("SANAD_API_PORT", "8010"))
WEB_PORT = 3000
NODE_MIN = (22, 12)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def say(icon: str, message: str) -> None:
    print(f"{icon}  {message}", flush=True)


def in_venv() -> bool:
    return VENV_PYTHON.exists() and Path(sys.executable).resolve() == VENV_PYTHON.resolve()


def relaunch_in_venv() -> None:
    """Re-run this script with .venv's Python so `python run.py` works from any Python."""
    if VENV_PYTHON.exists() and not in_venv():
        sys.exit(subprocess.call([str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]], cwd=ROOT))


def python_ready() -> bool:
    check = "import langgraph, langchain_anthropic, fastapi, uvicorn, multipart, numpy, pypdf, yaml"
    return subprocess.call([sys.executable, "-c", check], cwd=ROOT,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0


def _add_default_node_to_path() -> None:
    """Find Node in its usual install folder when it is not on PATH yet.

    Terminals (and VS Code) opened before Node was installed keep the old PATH, so `node` is not
    found even though it is installed. Adding the folder here makes `python run.py` work anyway.
    """
    if shutil.which("node"):
        return
    folders = [Path(os.environ.get(var, "")) / "nodejs" for var in ("ProgramFiles", "ProgramFiles(x86)")]
    folders.append(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "nodejs")
    for folder in folders:
        if (folder / ("node.exe" if os.name == "nt" else "node")).exists():
            os.environ["PATH"] = f"{folder}{os.pathsep}{os.environ.get('PATH', '')}"
            say("ℹ️", f"Using Node.js from {folder} (it is not on this terminal's PATH yet; "
                      "restart VS Code to fix that permanently).")
            return


def npm() -> str | None:
    return shutil.which("npm")


def node_ok() -> bool:
    _add_default_node_to_path()
    node = shutil.which("node")
    if not node or not npm():
        say("⚠️", f"Node.js is not installed. Install Node {NODE_MIN[0]}.{NODE_MIN[1]}+ from https://nodejs.org, "
                  "then close VS Code completely and open it again.")
        return False
    version = subprocess.run([node, "--version"], capture_output=True, text=True).stdout.strip().lstrip("v")
    major, minor = (int(x) for x in version.split(".")[:2])
    if (major, minor) < NODE_MIN:
        say("⚠️", f"Your Node version is {version}; {NODE_MIN[0]}.{NODE_MIN[1]} or newer is required.")
        return False
    return True


def run(cmd: list[str], **kwargs) -> int:
    say("▶", " ".join(cmd))
    return subprocess.call(cmd, cwd=ROOT, **kwargs)


# ---------------------------------------------------------------- commands

def setup() -> int:
    if not VENV_PYTHON.exists():
        say("📦", "Creating the virtual environment .venv ...")
        if run([sys.executable, "-m", "venv", str(VENV)]) != 0:
            return 1
    say("📦", "Installing Python packages ...")
    if run([str(VENV_PYTHON), "-m", "pip", "install", "-q", "-r", "requirements.txt"]) != 0:
        say("❌", "Installing Python packages failed.")
        return 1
    env, example = ROOT / ".env", ROOT / ".env.example"
    if not env.exists() and example.exists():
        shutil.copy(example, env)
        say("📝", "Created .env - add ANTHROPIC_API_KEY to enable Claude (optional; without it simple rules are used).")
    if node_ok():
        say("📦", "Installing web packages (npm install) ...")
        if run([npm(), "install", "--no-audit", "--no-fund"]) != 0:
            say("❌", "npm install failed.")
            return 1
    say("✅", "Setup complete. Run:  python run.py")
    return 0


class Service:
    """A child process whose output is printed with a [name] prefix."""

    def __init__(self, name: str, cmd: list[str], env: dict | None = None):
        self.name = name
        self.proc = subprocess.Popen(
            cmd, cwd=ROOT, env={**os.environ, **(env or {})}, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", bufsize=1)
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self) -> None:
        for line in self.proc.stdout:
            print(f"[{self.name}] {line.rstrip()}", flush=True)

    def stop(self) -> None:
        if self.proc.poll() is not None:
            return
        if os.name == "nt":   # npm starts node as a child: stop the whole tree of this process only
            subprocess.call(["taskkill", "/T", "/F", "/PID", str(self.proc.pid)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()


def _wait_for_api() -> None:
    url = f"http://localhost:{API_PORT}/health"
    for _ in range(60):
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    say("✅", f"Agents API ready:  http://localhost:{API_PORT}/docs  (log: src/logger/logs/sanad.log)")
                    return
        except OSError:
            time.sleep(1)
    say("⚠️", "The agents API did not respond after 60 seconds - check the lines starting with [api].")


def port_in_use(port: int) -> bool:
    """True if any program already listens on the port (IPv4 or IPv6), e.g. Splunk on 8000."""
    import socket

    for family, host in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
        with socket.socket(family, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            try:
                if sock.connect_ex((host, port)) == 0:
                    return True
            except OSError:
                continue
    return False


def start(api: bool = True, web: bool = True) -> int:
    if api and not python_ready():
        say("❌", "Python packages are not installed. First run:  python run.py setup")
        return 1
    for needed, port, var in ((api, API_PORT, "SANAD_API_PORT"), (web, WEB_PORT, None)):
        if needed and port_in_use(port):
            hint = f" Change it with:  set {var}=8020  and run again." if var else ""
            say("❌", f"Port {port} is used by another program (or an earlier Sanad run is still open).{hint}")
            return 1
    if web and not node_ok():
        if not api:
            return 1
        say("ℹ️", "Starting the agents API only.")
        web = False
    if web and not (ROOT / "node_modules").exists():
        say("📦", "Web packages are missing, running npm install ...")
        if run([npm(), "install", "--no-audit", "--no-fund"]) != 0:
            return 1

    services: list[Service] = []
    try:
        if api:
            services.append(Service("api", [sys.executable, "-m", "uvicorn", "src.agent.api:app",
                                            "--port", str(API_PORT), "--reload", "--reload-dir", "src",
                                            "--log-level", "warning"],
                                    env={"PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8",
                                         # 1 = load the local Whisper model (audio_b64 questions) at start-up;
                                         # live captions use OpenRouter and do not need it
                                         "SANAD_SPEECH_PRELOAD": os.getenv("SANAD_SPEECH_PRELOAD", "0")}))
            threading.Thread(target=_wait_for_api, daemon=True).start()
        if web:
            services.append(Service("web", [npm(), "run", "dev"],
                                    env={"VITE_SANAD_API_URL": os.getenv("VITE_SANAD_API_URL", f"http://localhost:{API_PORT}")}))
            say("🌐", f"Web UI:  http://localhost:{WEB_PORT}")
        say("⏹", "Press Ctrl+C to stop")
        while True:
            for service in services:
                if service.proc.poll() is not None:
                    say("❌", f"[{service.name}] stopped (exit code {service.proc.returncode}) - see the lines above.")
                    return service.proc.returncode or 1
            time.sleep(0.5)
    except KeyboardInterrupt:
        say("⏹", "Stopping ...")
        return 0
    finally:
        for service in services:
            service.stop()


def test() -> int:
    failed = 0
    if python_ready():
        say("🧪", "Python tests ...")
        failed |= run([sys.executable, "-m", "pytest", "src/agent/tests", "-q", "-p", "no:warnings"])
    else:
        say("❌", "Python packages are not installed. Run:  python run.py setup")
        failed = 1
    if node_ok():
        say("🧪", "Web tests ...")
        failed |= run([npm(), "test"])
    else:
        failed = 1
    say("✅" if not failed else "❌", "All tests passed" if not failed else "Some tests failed or did not run - see above")
    return 1 if failed else 0


COMMANDS = {
    "start": lambda: start(),
    "api": lambda: start(web=False),
    "web": lambda: start(api=False),
    "setup": setup,
    "test": test,
}


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "start"
    if command in ("-h", "--help", "help") or command not in COMMANDS:
        print(__doc__)
        return 0 if command in ("-h", "--help", "help") else 1
    if command != "setup":
        relaunch_in_venv()
    return COMMANDS[command]()


if __name__ == "__main__":
    sys.exit(main())
