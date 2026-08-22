"""
Single-command startup: launches the FastAPI backend and the React frontend
together, so you don't need two separate terminals for local development.

Usage:
    python run_all.py

Requires:
    - backend/venv already created with dependencies installed (see README)
    - frontend/node_modules already installed (npm install)
    - Postgres + Redis already running (docker compose up postgres redis -d)
"""
import subprocess
import sys
import os
import signal
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT, "backend")
FRONTEND_DIR = os.path.join(ROOT, "frontend")

processes = []


def start(cmd, cwd, name):
    print(f"[run_all] starting {name}: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, cwd=cwd)
    processes.append((name, proc))
    return proc


def shutdown(*_):
    print("\n[run_all] stopping all services...")
    for name, proc in processes:
        print(f"  stopping {name}")
        proc.terminate()
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    python_exe = sys.executable  # use whichever python is running this script (your venv)

    start(
        [python_exe, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=BACKEND_DIR,
        name="backend (FastAPI)",
    )
    time.sleep(2)  # give the backend a head start before the frontend proxies to it

    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    start([npm_cmd, "run", "dev"], cwd=FRONTEND_DIR, name="frontend (Vite)")

    print("\n[run_all] Backend:  http://localhost:8000/docs")
    print("[run_all] Frontend: http://localhost:5173")
    print("[run_all] Press Ctrl+C to stop both.\n")

    # keep the main thread alive while the child processes run
    try:
        while True:
            time.sleep(1)
            for name, proc in processes:
                if proc.poll() is not None:
                    print(f"[run_all] {name} exited unexpectedly (code {proc.returncode})")
                    shutdown()
    except KeyboardInterrupt:
        shutdown()
