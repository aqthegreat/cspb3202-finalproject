#!/usr/bin/env python3
"""Display live RouterOS queue-tree and ether5 transmit statistics."""

import base64
import json
import os
import time
import urllib.request

from rich.console import Console
from rich.live import Live
from rich.table import Table


QUEUES = ("qos-parent", "qos-high", "qos-medium", "qos-low")
INTERFACE = "ether5"

host = os.getenv("MIKROTIK_HOST", "192.168.88.34")
port = os.getenv("MIKROTIK_REST_PORT", "80")
user = os.environ["MIKROTIK_USER"]
password = os.environ["MIKROTIK_PASSWORD"]
base_url = f"http://{host}:{port}/rest"

credentials = base64.b64encode(f"{user}:{password}".encode()).decode()
headers = {
    "Authorization": f"Basic {credentials}",
    "Content-Type": "application/json",
}


def request(path, data=None):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(
        f"{base_url}/{path}",
        data=body,
        headers=headers,
        method="POST" if body else "GET",
    )
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.load(response)


def number(value):
    return f"{int(value):,}"


def rate(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return str(value or "N/A")

    for unit in ("bps", "Kbps", "Mbps", "Gbps"):
        if value < 1000 or unit == "Gbps":
            return f"{value:,.1f} {unit}"
        value /= 1000


def configured_rate(value):
    return "N/A" if value in (None, "", "0") else rate(value)


def queued(queue):
    if "queued-packets" in queue and "queued-bytes" in queue:
        return f"{number(queue['queued-packets'])} pkt / {number(queue['queued-bytes'])} B"
    if "queued-packets" in queue:
        return f"{number(queue['queued-packets'])} pkt"
    if "queued-bytes" in queue:
        return f"{number(queue['queued-bytes'])} B"
    return "N/A"


def get_stats():
    queue_data = request("queue/tree")
    queues = {queue["name"]: queue for queue in queue_data}

    interface_data = request(
        "interface/monitor-traffic", {"interface": INTERFACE, "once": ""}
    )
    if isinstance(interface_data, list):
        interface_data = interface_data[0]

    return [queues[name] for name in QUEUES], interface_data["tx-bits-per-second"]


def make_table(queues, tx_rate):
    table = Table(title=f"RouterOS QoS Monitor - {INTERFACE} TX: {rate(tx_rate)}")
    for heading in ("Queue", "Rate", "Packets", "Bytes", "Drops", "Queued", "Limit At", "Max Limit"):
        table.add_column(heading, justify="left" if heading == "Queue" else "right")

    for queue in queues:
        table.add_row(
            queue["name"],
            rate(queue.get("rate", 0)),
            number(queue.get("packet", queue.get("packets", 0))),
            number(queue.get("bytes", 0)),
            number(queue.get("dropped", 0)),
            queued(queue),
            configured_rate(queue.get("limit-at")),
            configured_rate(queue.get("max-limit")),
        )
    return table


def main():
    console = Console()
    queues, tx_rate = get_stats()

    try:
        with Live(make_table(queues, tx_rate), console=console) as live:
            while True:
                time.sleep(1)
                queues, tx_rate = get_stats()
                live.update(make_table(queues, tx_rate))
    except KeyboardInterrupt:
        console.print("\nMonitor stopped.")


if __name__ == "__main__":
    main()
