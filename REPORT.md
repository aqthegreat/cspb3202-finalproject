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

The experimental environment consists of two computers connected through a
MikroTik router. PC1 generates the test traffic and runs the RL agent. PC2
receives the traffic and provides the destination-side measurements used to
evaluate network performance. The router runs MikroTik RouterOS 7.23.2 and
applies the QoS configuration selected by the agent.

| Component | Role | Operating system / version |
| --- | --- | --- |
| PC1 | Traffic generator and RL agent | Xubuntu 26.04 |
| MikroTik router | Routing, traffic classification, and QoS enforcement | RouterOS 7.23.2 |
| PC2 | Traffic receiver and performance measurement | Xubuntu 26.04 |

The MikroTik router model and the relevant hardware specifications of both PCs
will be recorded before the experiments so that the environment can be
reproduced.

### Network topology

```text
PC1: Traffic Generator / RL Agent
                 |
                 v
MikroTik Router: RouterOS 7.23.2
                 |
                 v
PC2: Traffic Receiver / Measurement
```

All experiment traffic travels from PC1 to PC2 through the MikroTik router.
This makes the router the controlled bottleneck and allows its QoS policy to
determine how available bandwidth is shared among traffic classes. The exact
link speeds and configured bottleneck rate will be documented with the final
test configuration.

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

An experiment episode consists of repeated observation, action, measurement,
and reward steps under a defined traffic scenario. The agent's goal is to earn
a higher cumulative reward by reducing loss and latency for high-priority
traffic while retaining as much low-priority throughput as possible. The
specific rules are defined in the following section.

## Reinforcement Learning Environment

The network experiment is modeled as a reinforcement learning environment.
Although it is not a graphical game, it has the same core elements: a state,
an available set of actions, a reward, and a condition that ends each episode.

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

The exact profiles and their queue parameters will be documented after they are
finalized.

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
documented experiments.

### Episode and decision interval

Each episode lasts 300 seconds. The agent chooses an action every 5 seconds, so
a complete episode contains 60 decision steps. During each step, the selected
profile is applied and traffic runs for the decision interval before the next
state and reward are calculated.

### Termination

An episode terminates normally after 300 seconds. An episode may also terminate
early if the environment cannot safely continue, such as when communication
with the router or measurement process fails. Early termination will be logged
and distinguished from a completed episode so that incomplete data is not
treated as a valid performance result.

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
