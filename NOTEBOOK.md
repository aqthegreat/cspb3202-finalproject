# Project Notebook

This is a chronological record of the project's main decisions, progress, and
open work. Times use the `America/Denver` timezone.

## 2026-07-31 - Project documentation started

Created the notebook and initial report, then defined the project at a high
level: use reinforcement learning to select predefined MikroTik QoS profiles
based on observed network performance.

The initial objective is to minimize loss and latency for high-priority DSCP
traffic while preserving throughput for lower-priority traffic. Candidate
observations include packet loss, latency, throughput, and the active queue
profile.

### Next steps

- Finalize the research question and project scope.
- Document the network and RouterOS configuration.
- Define the observation space, actions, reward, and evaluation criteria.

## 2026-07-31 - Requirements and environment drafted

The final project must include working code, a demo clip, experiment results,
visualizations, troubleshooting, discussion, and references. It should also
preserve evidence of meaningful changes made when a correctly implemented
learning approach performs poorly.

Still to confirm are the PC and router hardware, link speeds, traffic rates,
QoS profiles, and the exact reward formula.

## 2026-07-31 - RL environment and design decisions

The initial state contains high and medium-priority loss and latency,
low-priority throughput, and the current queue profile. Each action selects one
predefined QoS profile. Episodes will last 300 seconds with a decision every 5
seconds, giving 60 steps unless a measurement or environment failure ends the
episode early.

The reward will favor throughput and low latency while penalizing loss and
unnecessary profile changes. Its weights and normalization still need to be
defined.

Two design choices are fixed:

- Use DSCP markings for transparent, reproducible traffic classification.
- Limit the agent to predefined profiles so it cannot create arbitrary or
  invalid RouterOS settings.

The project will proceed from static QoS and traffic generation through
measurement, router control, baselines, and tabular Q-learning. DQN remains
optional. Router operations will stay separate from networking and RL code.

### Next steps

- Validate the static Queue Tree, DSCP classification, counters, and shaping.
- Finish the reward and environment details.

## 2026-07-31 - Router backup tool added

Added `scripts/backup_router.sh` to retrieve a timestamped RouterOS `/export
terse` configuration over SSH. Backups are stored in the ignored
`routerbackups/` directory because they may contain private network details.

The script uses key authentication, verifies the SSH host key, excludes
sensitive values, and removes failed or empty exports. Its defaults are router
`192.168.88.34`, user `backup`, SSH port 22, and key
`~/.ssh/mikrotik_backup`; each can be overridden.

Syntax and help checks passed. A live backup still requires the RouterOS
account, SSH key, and verified router host key.

## 2026-08-02 - Static QoS and traffic tools configured

Configured mangle rules for DSCP 46, 26, and 0 and verified that they assign
the high-, medium-, and low-priority packet marks correctly. The Queue Tree now
has a 20 Mbps parent on `ether5` and three child queues with 6 Mbps committed
rates.

Added two traffic scripts:

- `scripts/start_iperf3_servers.sh` starts servers on ports 5201-5205.
- `scripts/start_iperf3_clients.sh` starts 60-second clients on ports 5201-5203
  with DSCP values 0, 26, and 46. The number of active clients and their target
  rates are selected by a traffic profile.

Both scripts passed Bash syntax checks and clean up their processes when
stopped.

### Next steps

- Run all three traffic classes through the router.
- Confirm that the expected child-queue counters increase.
- Record throughput, latency, loss, and queue behavior under congestion.

## 2026-08-02 - Live queue monitor added

Added `monitor.py`, a small RouterOS REST client using `rich`. It refreshes once
per second and displays rate, packets, bytes, drops, queued traffic,
`limit-at`, and `max-limit` for `qos-parent`, `qos-high`, `qos-medium`, and
`qos-low`. It also shows the `ether5` transmit rate.

Credentials come from `MIKROTIK_USER` and `MIKROTIK_PASSWORD`. The monitor uses
plain HTTP on port 80 because this is a temporary trusted lab and the router's
self-signed certificate caused HTTPS failures. The monitor was later simplified
to rely on Python's normal errors rather than custom validation and exception
messages.

Python syntax checks passed. Live router testing remains to be completed.

## 2026-08-03 - Queue profile controller added

Added `profile_controller.py` to verify that Python can control the RouterOS
Queue Tree before adding automatic profile selection or reinforcement learning.
The controller uses the same REST login procedure and environment variables as
`monitor.py`, while requiring an account with queue read and write permissions.

The public `set_profile()` function supports three fixed profiles and changes
the `limit-at` values on `qos-high`, `qos-medium`, and `qos-low`:

| Profile | High | Medium | Low |
| --- | ---: | ---: | ---: |
| `balanced` | 1M | 1M | 1M |
| `protected` | 1250k | 1250k | 250k |
| `maximum_protection` | 1500k | 1500k | 100k |

The controller validates the requested profile and confirms that all required
queues exist before sending updates. Live testing exposed an HTTP 400 error
when the leading `*` in a RouterOS resource ID was URL-encoded. Keeping IDs such
as `*1000002` literal in the REST path fixed the request.

Tested `set_profile("balanced")` against the router and verified that all three
queues reported `limit-at=1000000`. The test then successfully restored the
original values. Python compilation and formatting checks also passed.

### Next steps

- Use the controller during repeatable static-profile network tests.
- Keep automatic decisions and reinforcement learning separate until profile
  switching and measurements are validated together.

## 2026-08-04 - Static controller loop added

Added `run_controller.py` to integrate the existing observation and control
paths. `StaticController` accepts one predefined profile and returns it for
every observation without inspecting or reacting to the statistics. The runner
calls `monitor.get_stats()`, asks the controller for its fixed profile, applies
it through `profile_controller.set_profile()`, and repeats every five seconds by
default.

The command-line interface accepts any profile defined in
`profile_controller.PROFILES` and an optional positive `--interval`. Each
iteration prints the selected profile, `ether5` transmit rate, and the current
rate for each child queue. Ctrl+C stops the loop.

A single-iteration test confirmed that the controller selected and applied the
configured profile while consuming the monitor's existing return format.

I tested it against the router and everything looked great. Statistics were
collected and displayed and applied the statically assigned profile every 5
seconds.

### Next steps

- Run the static controller with each profile during controlled traffic tests.
- Record observations and outcomes before implementing dynamic selection.
- Keep the same controller interface for later baseline and learning agents.

## 2026-08-04 - Traffic-generation profiles added

Updated `scripts/start_iperf3_clients.sh` to accept a required traffic profile
after the server address. The profiles define bandwidths in high-, medium-, and
low-priority order:

| Profile | High (DSCP 46) | Medium (DSCP 26) | Low (DSCP 0) | Total offered load |
| --- | ---: | ---: | ---: | ---: |
| `open` (`0`) | 0 | 0 | 20M | 20M |
| `minor` (`1`) | 500K | 500K | 20M | 21M |
| `moderate` (`2`) | 1M | 1M | 20M | 22M |
| `major` (`3`) | 2M | 2M | 20M | 24M |

The `open` profile provides a wide-open baseline with only default DSCP 0
traffic. The remaining profiles progressively add high- and medium-priority
load above the 20 Mbps parent-queue capacity to demonstrate increasing
congestion. Streams assigned zero bandwidth are skipped rather than launched.
Names and numeric aliases are both accepted; for example:

```bash
scripts/start_iperf3_clients.sh SERVER_HOST minor
scripts/start_iperf3_clients.sh SERVER_HOST 3
```

Bash syntax, argument validation, and the generated iperf3 command lines were
checked without sending live traffic. A subsequent live run confirmed that the
profiles worked as intended.

## 2026-08-07 - Minimal tabular Q-learning controller added

Added `qlearning_controller.py` while keeping monitoring, RouterOS profile
updates, and the static baseline in their existing modules. The new
`QLearningController` uses the names in `profile_controller.PROFILES` as its
action space and stores learned values in a Python dictionary. It uses the
standard one-step Q-learning update with these initial parameters:

- Learning rate: `alpha=0.2`
- Discount factor: `gamma=0.9`
- Exploration rate: `epsilon=0.2`

The discrete state is `(high_status, medium_status, low_status,
current_profile)`. Each queue status is `0` when its rate is at most 10 Kbps,
`1` when it is active without new drops, and `2` when at least one new drop is
observed during the interval. RouterOS reports cumulative drop counters, so the
controller stores the previous value for each queue and calculates interval
deltas. The first reading establishes a baseline, and a lower later reading is
treated as a counter reset instead of a negative delta.

The initial reward gives strong positive values when high- and
medium-priority traffic has no new drops and strong penalties when either has
new drops. It also rewards high and medium throughput near or above 900 Kbps,
slightly rewards drops being absorbed by the low-priority queue, and slightly
penalizes selection of `maximum_protection`. These weights are deliberately
simple starting values for later experiments rather than a finalized reward
model.

Updated `run_controller.py` to select the baseline or learning controller:

```bash
python3 run_controller.py --controller static --profile balanced
python3 run_controller.py --controller qlearning
```

The Q-learning loop reads an initial observation, selects and applies a
profile, waits five seconds, reads the next observation, calculates the reward,
updates the Q-table, and repeats. Each completed step prints the decision state,
chosen profile, reward, updated Q-value, and epsilon. Q-table persistence, CSV
logging, graphs, neural networks, and new dependencies are intentionally out of
scope for this version.

Local checks covered Python compilation, discrete state construction, drop
counter resets, reward calculation, the Q-learning update, and command-line
parsing. Live learning behavior on the router still needs to be evaluated.

### Next steps

- Run the Q-learning controller against each repeatable traffic profile.
- Record whether learned actions reduce high- and medium-priority drops versus
  the static baselines.
- Revisit reward weights after reviewing live queue behavior.
- Add experiment logging and visualizations only after the basic learning loop
  is validated.

## 2026-08-07 - Idle-state profile oscillation observed

Live testing with no traffic showed that the Q-learning controller repeatedly
switched among `balanced`, `protected`, and `maximum_protection` while the state
remained `(0, 0, 0, current_profile)`. The reward was still `9.0` for most
profiles and `8.5` for `maximum_protection`, so the controller learned large
positive Q-values for idle intervals. Random tie-breaking and the 0.2
exploration rate then caused unnecessary profile changes even though there was
no network condition to respond to.

The cause is that the initial reward treats the absence of high- and
medium-priority drops as a success without distinguishing an uncongested active
interval from an interval with no traffic. A switching penalty alone could
reduce oscillation, but it would not correct this misleading idle reward.

The proposed solution is to treat an all-idle observation as a special case:

- When all three status values are zero, bypass epsilon-greedy exploration and
  select `balanced`.
- When all measured rates are at or below `idle_rate` and all drop deltas are
  zero, return an idle reward of `0.0` instead of rewarding the absence of
  drops.
- Continue normal Q-learning and exploration whenever traffic is active.

This should keep the least restrictive profile in place during idle periods,
prevent idle time from inflating Q-values, and preserve learning during useful
traffic observations. The adjustment was applied to the controller after the
initial live test exposed the problem.

## 2026-08-07 - DSCP 0 exploration and switching penalty

A live run with only DSCP 0 traffic primarily settled on `balanced` for state
`(0, 0, 2, "balanced")`, whose updated Q-value rose above 30 as repeated rewards
near 10 accumulated. The controller still occasionally selected `protected`
or `maximum_protection`. With fixed `epsilon=0.2` and three actions, exploration
has about a 13.3% chance per active decision of choosing one of the two actions
other than the current best action. Previously unvisited actions can also be
selected by random tie-breaking before their Q-values separate.

The increasing Q-values are expected because each value estimates discounted
cumulative future reward rather than only the immediate reward. With a reward
near 10 and `gamma=0.9`, the theoretical continuing value approaches 100.

Added a `0.5` reward penalty when the selected profile differs from the current
profile stored in the state. This gives the agent an explicit reason to avoid
unnecessary RouterOS reconfiguration while still allowing a switch whose
expected benefit is greater than the penalty. The fixed exploration rate can
still deliberately cause occasional changes; epsilon decay remains a possible
later tuning experiment.

## 2026-08-07 - Multi-class convergence tuning

Traffic profiles containing multiple DSCP classes did not converge on a queue
profile. Nearly every congested interval became state `(2, 2, 2, profile)` and
received a reward near `-16`, regardless of the selected action. This produced
three related problems: distinct offered loads were aliased into the same
state, untried actions with initial Q-values of zero looked better than tried
actions with negative Q-values, and fixed exploration continued changing the
router indefinitely.

The controller was adjusted in three ways while retaining the previous values
as commented alternatives for later comparisons:

- Congested queues now use status `2` at rates through 750 Kbps, status `3` at
  rates through 1.5 Mbps, and status `4` above 1.5 Mbps. This separates the
  approximate 500 Kbps, 1 Mbps, and 2 Mbps high/medium workloads.
- A constant 20-point reward offset prevents the initial zero Q-values of
  untried actions from repeatedly defeating learned negative values. It does
  not change which immediate outcome is better because every non-idle action
  receives the same offset.
- Epsilon now decays by a factor of `0.97` per active decision and becomes
  exactly zero below `0.02`. During exploitation, the current profile is kept
  when its Q-value is within `1.0` of the best value. These changes allow early
  exploration followed by a stable profile choice.

Local checks confirmed the expanded state behavior, positive congestion reward
baseline, switching penalty, stability margin, and epsilon decay. Live tests
with each multi-class traffic profile are still required to determine whether
the converged profile also produces the best network performance.

## 2026-08-07 - Hybrid profile-selection guardrails

The convergence changes kept `balanced` active during all four traffic-profile
runs. Network performance was already close to the expected result, with only
about two to four drops per second, so the measured rewards did not give the
agent a strong reason to select a more restrictive profile. This is an
important limitation: similar outcomes cannot produce a reliably different
learned action merely because a particular action is expected for the demo.

To make the controller's response deterministic and interpretable, explicit
domain rules were added ahead of epsilon-greedy selection:

- idle state `(0, 0, 0, profile)` selects `balanced`;
- high- or medium-priority status `1` or `2` selects `protected`; and
- high- or medium-priority status `3` or `4` selects
  `maximum_protection`.

These rules make the controller a hybrid rule-based/Q-learning policy. The
resulting choices must not be reported as profiles independently discovered by
Q-learning. The epsilon experiment was also revised: instead of becoming zero,
epsilon decays by `0.97` to a minimum of `0.05`, preserving some exploration
for states that are not handled by the guardrails. The earlier zero-epsilon
lines remain commented in the source for a later comparison.

## 2026-08-07 - Fixed epsilon and UDP traffic

The next experiment restores epsilon to a fixed `0.2`, matching the original
Q-learning configuration. The decay-to-`0.05` implementation remains commented
in the controller because comparing fixed and decaying exploration may still be
useful. The hybrid protection guardrails continue to bypass epsilon-greedy
selection for active high- and medium-priority traffic.

The traffic generator was changed from TCP to UDP by adding iperf3's `--udp`
option to every active client stream. TCP congestion control reduces its send
rate when the path is congested, which can hide the sustained overload needed
to demonstrate queue drops. UDP maintains each configured offered rate and
allows iperf3 to report packet loss directly. The standard iperf3 server command
already accepts UDP tests, so the server command itself requires no UDP flag;
its output and comments now make that behavior explicit.

## Entry template

```markdown
## YYYY-MM-DD - Short description

### Progress

- What changed or was completed

### Results

- Successes, failures, or important findings

### Next steps

- Remaining work
```
