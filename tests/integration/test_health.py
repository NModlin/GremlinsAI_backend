import threading
import time
import urllib.request

import uvicorn

from app.main import app


def run_server(host: str = "127.0.0.1", port: int = 9051):
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    return server, t


def test_health_endpoint_live():
    host = "127.0.0.1"
    port = 9051
    server, thread = run_server(host, port)

    # Wait briefly for startup
    for _ in range(20):
        time.sleep(0.2)
        try:
            with urllib.request.urlopen(f"http://{host}:{port}/health", timeout=2) as resp:
                body = resp.read().decode()
                assert resp.status == 200
                assert "status" in body
                break
        except Exception:
            continue
    else:
        # If loop exhausted without break
        assert False, "Health endpoint did not respond in time"

    # Signal shutdown
    server.should_exit = True
    thread.join(timeout=2)

