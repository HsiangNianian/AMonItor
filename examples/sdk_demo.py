from __future__ import annotations

import argparse
from typing import Any

from amonitor_sdk.server import start_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a demo Python SDK server instance")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--heartbeat-interval", type=int, default=5)
    parser.add_argument("--name", default="sdk-demo")
    return parser


async def on_action(action: str, params: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "message": f"handled action={action}, params={params}",
    }


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    print(
        f"[{args.name}] start target_id={args.target_id} on ws://{args.host}:{args.port}",
        flush=True,
    )
    start_server(
        host=args.host,
        port=args.port,
        target_id=args.target_id,
        action_handler=on_action,
        heartbeat_interval=args.heartbeat_interval,
    )


if __name__ == "__main__":
    main()
