from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="One-click local demo runner")
    parser.add_argument("--config", required=True, help="Path to demo config json")
    return parser


def build_clean_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in [
        "ALL_PROXY",
        "all_proxy",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "http_proxy",
        "https_proxy",
    ]:
        env.pop(key, None)
    env["NO_PROXY"] = "127.0.0.1,localhost"
    return env


def terminate_all(processes: list[subprocess.Popen]) -> None:
    for process in processes:
        if process.poll() is None:
            process.terminate()
    deadline = time.time() + 5
    while time.time() < deadline:
        if all(process.poll() is not None for process in processes):
            return
        time.sleep(0.1)
    for process in processes:
        if process.poll() is None:
            process.kill()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    root_dir = Path(__file__).resolve().parent.parent
    config_path = (root_dir / args.config).resolve() if not Path(args.config).is_absolute() else Path(args.config)

    with config_path.open("r", encoding="utf-8") as file:
        config = json.load(file)

    agent = config["agent"]
    sdk_instances = config["sdk_instances"]
    panel = config["panel"]

    env = build_clean_env()
    processes: list[subprocess.Popen] = []

    try:
        agent_env = env.copy()
        agent_env["AGENT_LISTEN_ADDR"] = agent["listen_addr"]
        print("[demo] starting agent", flush=True)
        processes.append(
            subprocess.Popen(
                ["go", "run", "./cmd/agent"],
                cwd=root_dir / "agent",
                env=agent_env,
            )
        )

        time.sleep(1)

        for sdk in sdk_instances:
            print(f"[demo] starting sdk: {sdk['name']}", flush=True)
            processes.append(
                subprocess.Popen(
                    [
                        "uv",
                        "run",
                        "python",
                        "../examples/sdk_demo.py",
                        "--name",
                        sdk["name"],
                        "--target-id",
                        sdk["target_id"],
                        "--host",
                        sdk["host"],
                        "--port",
                        str(sdk["port"]),
                        "--heartbeat-interval",
                        str(sdk.get("heartbeat_interval", 5)),
                    ],
                    cwd=root_dir / "python-sdk",
                    env=env,
                )
            )

        time.sleep(1)

        print("[demo] starting panel demo", flush=True)
        processes.append(
            subprocess.Popen(
                [
                    "uv",
                    "run",
                    "python",
                    "../examples/panel_demo.py",
                    "--panel-ws",
                    agent["panel_ws"],
                    "--action-name",
                    panel.get("action_name", "restart"),
                    "--targets-json",
                    json.dumps(sdk_instances, ensure_ascii=False),
                    *( ["--send-actions"] if panel.get("send_actions_on_connect", True) else [] ),
                ],
                cwd=root_dir / "python-sdk",
                env=env,
            )
        )

        print("[demo] running. press Ctrl+C to stop all", flush=True)
        while True:
            time.sleep(1)
            for process in processes:
                if process.poll() is not None:
                    raise RuntimeError(f"a demo process exited early: pid={process.pid} code={process.returncode}")
    except KeyboardInterrupt:
        print("\n[demo] stopping by user", flush=True)
    finally:
        terminate_all(processes)


if __name__ == "__main__":
    main()
