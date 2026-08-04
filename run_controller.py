#!/usr/bin/env python3
"""Run a fixed QoS profile while polling current RouterOS statistics."""

import argparse
import time

import monitor
import profile_controller


class StaticController:
    """Always select the same predefined queue profile."""

    def __init__(self, profile):
        if profile not in profile_controller.PROFILES:
            choices = ", ".join(profile_controller.PROFILES)
            raise ValueError(f"Unknown profile {profile!r}; choose from: {choices}")
        self.profile = profile

    def choose_profile(self, statistics):
        """Return the configured profile without using the observations yet."""
        return self.profile


def summarize_statistics(statistics):
    """Create a compact status line from monitor.get_stats() output."""
    queues, tx_rate = statistics
    queue_rates = ", ".join(
        f"{queue['name']}={monitor.rate(queue.get('rate', 0))}"
        for queue in queues
        if queue["name"] != "qos-parent"
    )
    return f"{monitor.INTERFACE} TX={monitor.rate(tx_rate)}; {queue_rates}"


def run(controller, interval=5.0):
    """Poll statistics and repeatedly enforce the controller's fixed profile."""
    while True:
        statistics = monitor.get_stats()
        profile = controller.choose_profile(statistics)
        profile_controller.set_profile(profile)
        print(f"Profile={profile}; {summarize_statistics(statistics)}", flush=True)
        time.sleep(interval)


def positive_interval(value):
    """Parse a positive polling interval for argparse."""
    interval = float(value)
    if interval <= 0:
        raise argparse.ArgumentTypeError("interval must be greater than zero")
    return interval


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "profile",
        choices=profile_controller.PROFILES,
        help="fixed profile to apply",
    )
    parser.add_argument(
        "--interval",
        type=positive_interval,
        default=5.0,
        help="seconds between controller iterations (default: 5)",
    )
    args = parser.parse_args()

    controller = StaticController(args.profile)
    print(
        f"Starting static controller with profile={args.profile} "
        f"and interval={args.interval:g}s"
    )
    try:
        run(controller, args.interval)
    except KeyboardInterrupt:
        print("\nStatic controller stopped.")


if __name__ == "__main__":
    main()
