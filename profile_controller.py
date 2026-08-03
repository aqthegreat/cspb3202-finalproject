#!/usr/bin/env python3
"""Set RouterOS queue-tree limit-at values from a predefined profile."""

import argparse
import base64
import json
import os
import urllib.request


PROFILES = {
    "balanced": {
        "high": "1M",
        "medium": "1M",
        "low": "1M",
    },
    "protected": {
        "high": "1250k",
        "medium": "1250k",
        "low": "250k",
    },
    "maximum_protection": {
        "high": "1500k",
        "medium": "1500k",
        "low": "100k",
    },
}

QUEUE_NAMES = {
    "high": "qos-high",
    "medium": "qos-medium",
    "low": "qos-low",
}

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


def request(path, data=None, method=None):
    """Send an authenticated request to the RouterOS REST API."""
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(
        f"{base_url}/{path}",
        data=body,
        headers=headers,
        method=method or ("POST" if body is not None else "GET"),
    )
    with urllib.request.urlopen(req, timeout=5) as response:
        if response.status == 204:
            return None
        response_body = response.read()
        return json.loads(response_body) if response_body else None


def set_profile(profile_name):
    """Set limit-at on qos-high, qos-medium, and qos-low queues.

    Args:
        profile_name: One of the names in PROFILES.

    Returns:
        A mapping of queue names to their configured limit-at values.

    Raises:
        ValueError: If profile_name is unknown.
        RuntimeError: If a required queue cannot be found on the router.
    """
    if profile_name not in PROFILES:
        choices = ", ".join(PROFILES)
        raise ValueError(f"Unknown profile {profile_name!r}; choose from: {choices}")

    queues = request("queue/tree")
    queues_by_name = {queue["name"]: queue for queue in queues}
    missing = [name for name in QUEUE_NAMES.values() if name not in queues_by_name]
    if missing:
        raise RuntimeError(f"Required queue(s) not found: {', '.join(missing)}")

    configured = {}
    for priority, limit_at in PROFILES[profile_name].items():
        queue_name = QUEUE_NAMES[priority]
        # RouterOS resource IDs contain a leading "*" that must remain literal.
        queue_id = queues_by_name[queue_name][".id"]
        request(
            f"queue/tree/{queue_id}",
            {"limit-at": limit_at},
            method="PATCH",
        )
        configured[queue_name] = limit_at

    return configured


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", choices=PROFILES, help="profile to apply")
    args = parser.parse_args()

    configured = set_profile(args.profile)
    print(f"Applied profile: {args.profile}")
    for queue_name, limit_at in configured.items():
        print(f"  {queue_name}: limit-at={limit_at}")


if __name__ == "__main__":
    main()
