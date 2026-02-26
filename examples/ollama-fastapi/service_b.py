from __future__ import annotations

from ollama_monitor_app import create_app

app = create_app(service_name="ollama-svc-b")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("service_b:app", host="0.0.0.0", port=8012, reload=False)
