#!/usr/bin/env python3
"""Run either the static or tabular Q-learning QoS controller."""

import argparse
import time

import monitor
import profile_controller
from qlearning_controller import QLearningController


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


def run_static(controller, interval=5.0):
    """Poll statistics and repeatedly enforce the controller's fixed profile."""
    while True:
        statistics = monitor.get_stats()
        profile = controller.choose_profile(statistics)
        profile_controller.set_profile(profile)
        print(f"Profile={profile}; {summarize_statistics(statistics)}", flush=True)
        time.sleep(interval)


# Retain the original entry point for callers of the static baseline.
run = run_static


def run_qlearning(controller, interval=5.0):
    """Observe, act, wait, and learn continuously from RouterOS statistics."""
    current_profile = "balanced"
    statistics = monitor.get_stats()
    state = controller.build_state(statistics, current_profile)

    while True:
        profile = controller.choose_profile(state)
        profile_controller.set_profile(profile)
        time.sleep(interval)

        next_statistics = monitor.get_stats()
        next_state = controller.build_state(next_statistics, profile)
        reward = controller.calculate_reward(profile, current_profile=state[-1])
        q_value = controller.update(state, profile, reward, next_state)
        print(
            f"State={state}; profile={profile}; reward={reward:.2f}; "
            f"Q={q_value:.3f}; epsilon={controller.epsilon:.3f}",
            flush=True,
        )
        state = next_state


def positive_interval(value):
    """Parse a positive polling interval for argparse."""
    interval = float(value)
    if interval <= 0:
        raise argparse.ArgumentTypeError("interval must be greater than zero")
    return interval


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--controller",
        choices=("static", "qlearning"),
        default="static",
        help="controller type (default: static)",
    )
    parser.add_argument(
        "--profile",
        choices=profile_controller.PROFILES,
        help="fixed profile (required for the static controller)",
    )
    parser.add_argument(
        "--interval",
        type=positive_interval,
        default=5.0,
        help="seconds between controller iterations (default: 5)",
    )
    args = parser.parse_args()

    if args.controller == "static" and args.profile is None:
        parser.error("--profile is required when --controller static is selected")

    try:
        if args.controller == "static":
            controller = StaticController(args.profile)
            print(
                f"Starting static controller with profile={args.profile} "
                f"and interval={args.interval:g}s"
            )
            run_static(controller, args.interval)
        else:
            controller = QLearningController()
            print(f"Starting Q-learning controller with interval={args.interval:g}s")
            run_qlearning(controller, args.interval)
    except KeyboardInterrupt:
        print(f"\n{args.controller.capitalize()} controller stopped.")


if __name__ == "__main__":
    main()
