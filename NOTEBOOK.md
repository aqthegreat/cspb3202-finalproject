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
