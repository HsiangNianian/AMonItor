from __future__ import annotations

from ollama_monitor_app import create_app

app = create_app(service_name="ollama-svc-a")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("service_a:app", host="0.0.0.0", port=8011, reload=False)
