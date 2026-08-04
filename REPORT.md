# Adaptive QoS with Reinforcement Learning

## Overview

Modern routers typically use static Quality of Service (QoS) policies that are
configured manually by network administrators. While these policies work well
for predictable traffic patterns, they cannot automatically adapt to changing
network conditions. This project investigates whether a reinforcement learning
(RL) agent can dynamically adjust bandwidth allocation among traffic classes
marked with Differentiated Services Code Point (DSCP) values.

The RL agent observes network performance metrics such as packet loss, latency,
and throughput, then selects one of several predefined QoS configurations on a
MikroTik router. The objective is to minimize packet loss and latency for
high-priority traffic while maximizing the throughput available to
lower-priority traffic.

## Environment

### Hardware and software

The experimental environment consists of two traffic computers connected
through a MikroTik router and a separate Windows laptop that runs the controller
inside Ubuntu on Windows Subsystem for Linux (WSL). PC1 only generates test
traffic, and PC2 only receives it. The controller laptop reads measurements and
changes the router profile but is not a source or destination for experiment
traffic. The router runs MikroTik RouterOS 7.23.2 and applies the QoS
configuration selected by the agent.

| Component | Role | Operating system / version |
| --- | --- | --- |
| PC1 | Traffic generator | Xubuntu 26.04 |
| MikroTik router | Routing, traffic classification, and QoS enforcement | RouterOS 7.23.2 |
| PC2 | Traffic receiver | Xubuntu 26.04 |
| Controller laptop | Static controller and RL agent | Ubuntu on Windows WSL |

The MikroTik router model and the relevant hardware specifications of the
traffic computers and controller laptop will be recorded before the experiments
so that the environment can be reproduced.

### Network topology

```text
Experiment traffic path:

nuc34: Traffic Generator (192.168.4.2)
          |
          v
MikroTik Router (Management - 192.168.88.34)
          |
          v
nuc42: Traffic Receiver (192.168.5.2)

Management and control path:

Windows WSL/Ubuntu: Controller/RL Agent
          |
          | statistics and profile commands
          v
MikroTik Router: RouterOS REST API
```

All experiment traffic travels from PC1 to PC2 through the MikroTik router.
This makes the router the controlled bottleneck and allows its QoS policy to
determine how available bandwidth is shared among traffic classes. The separate
controller laptop communicates with the router over its management path and
does not carry the generated test traffic. The exact link speeds and configured
bottleneck rate will be documented with the final test configuration.

### Traffic classes

The generated traffic is divided into three priority classes and marked using
DSCP values:

- **High priority (DSCP 46):** voice-like UDP traffic that is sensitive to
  latency, jitter, and packet loss. The agent should protect this class from
  degraded service.
- **Medium priority (DSCP 26):** interactive traffic with intermediate service
  requirements. It should receive reliable service without displacing the
  high-priority class.
- **Low priority (DSCP 0):** bulk TCP traffic generated with `iperf3`. This
  class can tolerate more delay, and the agent should maximize its usable
  throughput when doing so does not harm higher-priority traffic.

The precise traffic rates and the tool used for interactive traffic will be
specified as the workload is finalized.

### Environment operation

At each decision interval, the environment collects performance measurements
for the traffic classes, including packet loss, latency, and throughput. These
measurements form the agent's observation. The agent then selects an action
from a fixed set of predefined QoS configurations, and that configuration is
applied to the MikroTik router. After the network runs under the selected
configuration for the next measurement interval, the environment calculates a
reward and supplies a new observation.

The controller operates continuously through repeated observation, action,
measurement, and reward steps under a defined traffic scenario. The agent's
goal is to earn a higher cumulative reward by reducing loss and latency for
high-priority traffic while retaining as much low-priority throughput as
possible. The specific rules are defined in the following section.

This describes the intended complete RL environment. The current monitoring
implementation collects Queue Tree statistics and the `ether5` transmit rate.
Per-class latency and packet-loss measurements still need to be integrated
before the full state and reward can be calculated.

## Reinforcement Learning Environment

The network experiment is modeled as a reinforcement learning environment.
Although it is not a graphical game, it has the same core elements: a state,
an available set of actions, a reward, and a transition to the next state.

### State

Every five seconds, the agent receives a state containing:

- high-priority packet loss;
- high-priority latency;
- medium-priority packet loss;
- medium-priority latency;
- low-priority throughput; and
- the currently active queue profile.

The performance measurements distinguish the service received by each traffic
class. The current profile gives the agent context about the QoS policy that
produced those measurements. State values will be normalized where practical
so metrics with larger numeric ranges do not dominate the learning process.

### Actions

At each decision point, the agent selects one QoS profile from a predefined set.
Each profile represents a complete, valid router configuration with different
bandwidth-allocation or queue parameters. Restricting the actions to tested
profiles prevents the agent from applying arbitrary or invalid RouterOS
settings. Selecting the profile that is already active is allowed and leaves
the configuration unchanged.

The action space currently contains three profiles. Each action changes the
`limit-at` value for the three child queues while leaving the Queue Tree
structure and maximum limits unchanged.

| Profile | `qos-high` | `qos-medium` | `qos-low` |
| --- | ---: | ---: | ---: |
| `balanced` | 1M | 1M | 1M |
| `protected` | 1250k | 1250k | 250k |
| `maximum_protection` | 1500k | 1500k | 100k |

**NOTE**: The above profiles may change over time to make the changes more obvious.

### Reward

The reward represents the tradeoff between protecting important traffic and
using the available link capacity efficiently. It will include:

- a positive contribution for high throughput;
- a positive contribution for low latency;
- a penalty for packet loss; and
- a small penalty when the agent changes queue profiles.

The profile-change penalty discourages unnecessary switching and unstable queue
behavior. The performance terms will be weighted so that high-priority traffic
receives the strongest protection while throughput for lower-priority traffic
is still rewarded. The final equation, term weights, measurement units, and
normalization method will be recorded before training and adjusted only through
documented experiments. The small penalty when changing is because in testing,
it was observed that traffic was temporary unlimited, which could be bad.

### Decision interval and experiment duration

The controller takes a new reading and chooses an action every five seconds.
Each reading, action, reward, and following reading forms one transition that
can be used immediately for a Q-learning update. The agent does not need to wait
for an average over five minutes before making a decision.

The network-control task can run continuously and does not require a fixed
episode length for Q-learning to operate. Controlled experiments may still use
a fixed duration so static profiles and learning agents can be compared over
equal traffic workloads. If five-minute runs are used, they will be evaluation
windows containing 60 separate decisions rather than one averaged observation.

The controller stops when the operator ends the experiment or when it cannot
safely continue, such as after a router communication or measurement failure.
Interrupted runs will be logged and distinguished from completed evaluation
runs so incomplete data is not treated as a valid comparison.

## Initial Design Decisions

Two foundational design decisions were made before implementation and will
remain fixed throughout the project.

### DSCP-based traffic classification

DSCP markings were selected because they provide a standardized mechanism for
identifying traffic priorities at the network layer. A packet's marking allows
the router to classify it as high-, medium-, or low-priority traffic without
requiring the RL agent to identify individual applications or inspect packet
contents. This keeps the network configuration understandable and makes the
traffic classes explicit and reproducible across experiments.

### Predefined QoS profiles

The action space was intentionally limited to a small set of predefined QoS
profiles. A compact, discrete action space simplifies the learning problem and
reduces the number of actions the agent must explore. It also prevents the
agent from constructing arbitrary RouterOS settings: every available action
corresponds to a configuration that can be reviewed and validated before an
experiment. This improves operational safety and makes the agent's choices
easier to interpret when results are analyzed.

Keeping both decisions fixed ensures that later experiments evaluate changes
to the learning method or reward design under a consistent traffic
classification and action structure.

## Implementation and Static Baseline

The initial measurement-and-control path was implemented before adding a
learning agent. This separates RouterOS integration problems from later RL
design and provides a simple baseline for comparison.

### Router and traffic configuration

The router currently uses a 20 Mbps parent queue on `ether5` with three child
queues named `qos-high`, `qos-medium`, and `qos-low`. RouterOS mangle rules
classify packets marked with DSCP 46, 26, and 0 into the high-, medium-, and
low-priority queues. Traffic-generation scripts start `iperf3` servers and
clients for repeatable testing of the three classes.

### Monitoring

`monitor.py` connects to the RouterOS REST API and retrieves Queue Tree data for
the parent and three child queues. It displays current rate, packets, bytes,
drops, queued traffic, committed rate, and maximum rate. It also retrieves the
transmit rate for `ether5`. The display refreshes once per second when the
monitor is run by itself.

This monitoring is sufficient to verify queue classification, traffic rates,
and profile changes. It does not yet provide all values planned for the RL
state, particularly per-class latency and packet loss.

### Profile control

`profile_controller.py` provides `set_profile()`, which accepts one of the three
predefined profile names. It first verifies that all required queues exist and
then updates their `limit-at` values through the RouterOS REST API. Restricting
the function to predefined profiles prevents the controller from generating
arbitrary Queue Tree settings.

Live testing initially produced an HTTP 400 response even though reading the
queue configuration worked. The failure was traced to URL-encoding the leading
`*` in RouterOS resource identifiers. For example, RouterOS accepted
`*1000002` in the REST path but rejected `%2A1000002` as an invalid resource
identifier. Keeping the identifier literal fixed the update request.

The `balanced` profile was applied during validation, and all three queues
reported a committed rate of 1 Mbps. Their original values were then restored
successfully.

### Static controller

`run_controller.py` integrates monitoring and profile control. Its
`StaticController` always returns the profile selected when the program starts;
it does not inspect the statistics when choosing an action. Every five seconds,
the runner retrieves current statistics, obtains the fixed profile from the
controller, applies it, and prints the selected profile and current traffic
rates.

The static controller was tested against the router and successfully collected
statistics while applying the configured profile every five seconds. This
confirms that the observation, action-selection, and RouterOS control path can
operate together before Q-learning is introduced.

The same static controller will serve as a baseline during experiments. Its
performance under each fixed profile can be compared with the Q-learning
agent's performance under identical traffic scenarios. This will show whether
dynamic profile selection improves results beyond simply choosing one fixed
configuration.
