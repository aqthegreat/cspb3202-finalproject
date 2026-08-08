#!/usr/bin/env python3
"""A small tabular Q-learning controller for the RouterOS QoS profiles."""

import random

import profile_controller


QUEUE_NAMES = {
    "high": "qos-high",
    "medium": "qos-medium",
    "low": "qos-low",
}


class QLearningController:
    """Select QoS profiles with epsilon-greedy tabular Q-learning."""

    def __init__(
        self,
        alpha=0.2,
        gamma=0.9,
        epsilon=0.2,
        idle_rate=10_000,
        switching_penalty=0.5,
        # epsilon_decay=0.97,  # Previous experiment decayed exploration; keep
        # this setting for comparing convergence with fixed exploration later.
        # epsilon_min=0.05,  # Previous decay floor retained for comparison.
        stability_margin=1.0,
    ):
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon  # Fixed at 0.2 by default for continual exploration.
        # self.epsilon_decay = epsilon_decay
        # self.epsilon_min = epsilon_min
        # Previous settings decayed epsilon toward 0.05; keep them commented so
        # fixed and decaying exploration can be compared in later experiments.
        self.stability_margin = stability_margin
        self.idle_rate = idle_rate
        self.switching_penalty = switching_penalty
        self.actions = tuple(profile_controller.PROFILES)
        self.q_table = {}
        self.previous_drops = {}
        self.latest_rates = {}
        self.latest_drop_deltas = {}

        # print(f"Q-learning settings: alpha={self.alpha}, gamma={self.gamma}, "
        #       f"epsilon={self.epsilon}, idle_rate={self.idle_rate}")
        # print(f"Available profiles: {self.actions}")

    @staticmethod
    def _number(value):
        """Convert RouterOS numeric strings to numbers."""
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def build_state(self, statistics, current_profile):
        """Convert queue rates and cumulative drops to a discrete state."""
        queues, _ = statistics
        by_name = {queue["name"]: queue for queue in queues}
        statuses = []
        rates = {}
        drop_deltas = {}

        # print(f"Raw queue statistics: {queues}")
        # print(f"Current profile before building state: {current_profile}")

        for priority, queue_name in QUEUE_NAMES.items():
            queue = by_name.get(queue_name, {})
            rate = self._number(queue.get("rate", 0))
            drops = int(self._number(queue.get("dropped", 0)))
            previous = self.previous_drops.get(queue_name)

            # print(f"{priority=}, {queue_name=}, {rate=}, {drops=}, {previous=}")

            # The first observation is a baseline. A smaller counter means the
            # router reset it, so historical drops are not counted as new ones.
            delta = 0 if previous is None or drops < previous else drops - previous
            self.previous_drops[queue_name] = drops
            rates[priority] = rate
            drop_deltas[priority] = delta

            # if delta > 0:
            #     status = 2
            # Previous state encoding treated every active queue with drops the
            # same. Keep it here because that simpler representation may still
            # be useful as an experimental comparison.
            if delta > 0 and rate <= 750_000:
                status = 2
            elif delta > 0 and rate <= 1_500_000:
                status = 3
            elif delta > 0:
                status = 4
            elif rate > self.idle_rate:
                status = 1
            else:
                status = 0
            statuses.append(status)

            # print(f"Queue {queue_name}: drop delta={delta}, status={status}")

        self.latest_rates = rates
        self.latest_drop_deltas = drop_deltas
        state = (*statuses, current_profile)
        # print(f"Latest rates: {self.latest_rates}")
        # print(f"Latest drop deltas: {self.latest_drop_deltas}")
        # print(f"Built state: {state}")
        return state

    def choose_profile(self, state):
        """Choose an action using epsilon-greedy selection."""
        # With no active queues, there is nothing useful to explore. Keep the
        # least restrictive profile instead of repeatedly reconfiguring QoS.
        if state[:3] == (0, 0, 0):
            # print("All queues are idle; selecting balanced")
            return "balanced"

        high_status, medium_status, _ = state[:3]
        if high_status >= 3 or medium_status >= 3:
            # print("High/medium status is 3 or 4; selecting maximum_protection")
            return "maximum_protection"
        if high_status > 0 or medium_status > 0:
            # print("High/medium traffic is active; selecting protected")
            return "protected"

        random_value = random.random()
        # print(f"Choosing profile for state: {state}")
        # print(f"Exploration roll={random_value:.4f}, epsilon={self.epsilon}")
        if random_value < self.epsilon:
            # print("Exploring: selecting a random profile")
            selected_action = random.choice(self.actions)
        else:
            values = [
                self.q_table.get((state, action), 0.0) for action in self.actions
            ]
            best_value = max(values)
            best_actions = [
                action
                for action, value in zip(self.actions, values)
                if value == best_value
            ]

            current_profile = state[-1]
            current_value = self.q_table.get((state, current_profile), 0.0)
            # selected_action = random.choice(best_actions)
            # Previous behavior randomly selected an exact best action. Keep
            # this alternative for comparing responsiveness without hysteresis.
            if current_value >= best_value - self.stability_margin:
                selected_action = current_profile
            else:
                selected_action = random.choice(best_actions)

            # print(f"Q-values by profile: {dict(zip(self.actions, values))}")
            # print(f"Exploiting: best value={best_value}, candidates={best_actions}")

        # self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
        # Previous behavior decayed epsilon to 0.05. Keep it commented because
        # comparing adaptive and fixed exploration may be useful later.
        return selected_action

    def calculate_reward(self, profile, current_profile=None):
        """Score the most recent interval's drops, rates, and selected profile."""
        high_drops = self.latest_drop_deltas.get("high", 0)
        medium_drops = self.latest_drop_deltas.get("medium", 0)
        low_drops = self.latest_drop_deltas.get("low", 0)

        # print(f"Calculating reward for profile: {profile}")
        # print(f"Drop deltas: high={high_drops}, medium={medium_drops}, low={low_drops}")
        # print(f"Rates used for reward: {self.latest_rates}")

        all_idle = all(
            self.latest_rates.get(priority, 0) <= self.idle_rate
            for priority in QUEUE_NAMES
        )
        no_new_drops = all(
            self.latest_drop_deltas.get(priority, 0) == 0
            for priority in QUEUE_NAMES
        )
        if all_idle and no_new_drops:
            # print("Idle interval detected; reward=0.0")
            return 0.0

        # reward = 5.0 if high_drops == 0 else -10.0
        # Previous reward had no baseline, so all actions learned negative
        # values during congestion and untried actions at zero looked better.
        # Preserve it here for later performance comparisons.
        reward = 25.0 if high_drops == 0 else 10.0
        reward += 4.0 if medium_drops == 0 else -8.0

        for priority in ("high", "medium"):
            rate = self.latest_rates.get(priority, 0)
            reward += 2.0 if rate >= 900_000 else rate / 900_000

        if low_drops > 0:
            reward += 1.0
        if profile == "maximum_protection":
            reward -= 0.5
        if current_profile is not None and profile != current_profile:
            reward -= self.switching_penalty
            # print(f"Applied switching penalty: -{self.switching_penalty}")
        # print(f"Final reward: {reward}")
        return reward

    def update(self, state, action, reward, next_state):
        """Apply the standard one-step Q-learning update and return the new value."""
        key = (state, action)
        old_value = self.q_table.get(key, 0.0)
        # print(f"Updating Q-value for state={state}, action={action}")
        # print(f"Reward={reward}, next_state={next_state}, old_value={old_value}")
        next_best = max(
            self.q_table.get((next_state, next_action), 0.0)
            for next_action in self.actions
        )
        new_value = old_value + self.alpha * (
            reward + self.gamma * next_best - old_value
        )
        self.q_table[key] = new_value
        # print(f"next_best={next_best}, new_value={new_value}")
        # print(f"Q-table now contains {len(self.q_table)} entries")
        return new_value
