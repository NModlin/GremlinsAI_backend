import threading
import time
import urllib.request

import uvicorn

from app.main import app


def run_server(host: str = "127.0.0.1", port: int = 9052):
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    return server, t


def test_metrics_endpoint_live():
    host = "127.0.0.1"
    port = 9052
    server, thread = run_server(host, port)

    # Wait for startup
    for _ in range(30):
        time.sleep(0.2)
        try:
            with urllib.request.urlopen(f"http://{host}:{port}/api/v1/metrics", timeout=2) as resp:
                body = resp.read().decode()
                assert resp.status == 200
                # Basic Prometheus exposition validations
                assert body.startswith("# HELP") or "# TYPE" in body
                assert "gremlinsai_" in body or "process_cpu_seconds_total" in body
                break
        except Exception:
            continue
    else:
        assert False, "/api/v1/metrics did not respond in time"

    server.should_exit = True
    thread.join(timeout=2)

