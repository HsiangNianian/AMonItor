from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate scalable demo config")
    parser.add_argument("--output", required=True)
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--start-port", type=int, default=8901)
    parser.add_argument("--heartbeat-interval", type=int, default=5)
    parser.add_argument("--action-name", default="restart")
    parser.add_argument("--agent-listen-addr", default="127.0.0.1:8080")
    parser.add_argument("--panel-ws", default="ws://127.0.0.1:8080/ws/panel")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.count < 1:
        raise ValueError("count must be >= 1")

    sdk_instances = []
    for index in range(1, args.count + 1):
        sdk_instances.append(
            {
                "name": f"sdk-{index:02d}",
                "target_id": f"demo-target-{index:02d}",
                "host": "127.0.0.1",
                "port": args.start_port + index - 1,
                "heartbeat_interval": args.heartbeat_interval,
            }
        )

    config = {
        "agent": {
            "listen_addr": args.agent_listen_addr,
            "panel_ws": args.panel_ws,
        },
        "sdk_instances": sdk_instances,
        "panel": {
            "send_actions_on_connect": True,
            "action_name": args.action_name,
        },
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"generated: {output_path}")


if __name__ == "__main__":
    main()
