# Adaptive QoS with Reinforcement Learning

This CSPB 3202 final project investigates whether a reinforcement learning
agent can dynamically select Quality of Service (QoS) configurations on a
MikroTik router. The agent will use network performance measurements, including
packet loss, latency, and throughput, to balance the needs of traffic classes
identified by Differentiated Services Code Point (DSCP) values.

The project aims to protect high-priority traffic from packet loss and excess
latency while preserving as much throughput as possible for lower-priority
traffic.

## Documentation

- [Project notebook](NOTEBOOK.md) - chronological decisions, progress, and experiment notes
- [Project report](REPORT.md) - draft of the final project report

## Status

The RouterOS traffic classification, Queue Tree, traffic-generation scripts,
live statistics monitor, predefined profile controller, and static controller
baseline are implemented. The complete latency and packet-loss measurement
path, reward calculation, Q-learning agent, and comparative experiments remain
to be implemented.

## Router configuration backups

The backup helper retrieves a human-readable RouterOS configuration export over
SSH. It uses key authentication and stores timestamped files in the ignored
`routerbackups/` directory. The default export is a binary file, so it's not
useful for comparisons as configuration changes are made. I'm also purposely not
uploading them to the Github repo because even though they won't have passwords,
they could have other sensitive information included.

```bash
scripts/backup_router.sh
```

The defaults are router `192.168.88.34`, user `backup`, SSH port `22`, and key
`~/.ssh/mikrotik_backup`. Run `scripts/backup_router.sh --help` to see how to
override them using arguments or environment variables.

## iperf3 traffic generation

On the receiving host, start the iperf3 servers:

```bash
scripts/start_iperf3_servers.sh
```

On the sending host, select a traffic profile and provide the receiving host's
address:

```bash
scripts/start_iperf3_clients.sh SERVER_HOST open
scripts/start_iperf3_clients.sh SERVER_HOST minor
scripts/start_iperf3_clients.sh SERVER_HOST moderate
scripts/start_iperf3_clients.sh SERVER_HOST major
```

Each profile sets the target bandwidth for the high-, medium-, and low-priority
streams, in that order:

| Profile | High (DSCP 46) | Medium (DSCP 26) | Low (DSCP 0) | Total offered load |
| --- | ---: | ---: | ---: | ---: |
| `open` (`0`) | 0 | 0 | 20M | 20M |
| `minor` (`1`) | 500K | 500K | 20M | 21M |
| `moderate` (`2`) | 1M | 1M | 20M | 22M |
| `major` (`3`) | 2M | 2M | 20M | 24M |

The `open` profile establishes the wide-open baseline with only default DSCP 0
traffic. The other profiles add progressively more prioritized traffic to
create increasing congestion against the router's 20 Mbps parent queue. A
stream with a bandwidth of zero is not launched. Profile numbers `0` through
`3` can be used in place of the names, and each run lasts 60 seconds.

## Live RouterOS queue monitor

Install the display dependency, set the RouterOS REST credentials, and start
the monitor from the project root:

```bash
python3 -m pip install -r requirements.txt
export MIKROTIK_USER='monitor'
export MIKROTIK_PASSWORD='your-password'
python3 monitor.py
```

The default router is `192.168.88.34` on HTTP port 80. Override it with
`MIKROTIK_HOST` or `MIKROTIK_REST_PORT`. The RouterOS `www` service and plain
REST access must be enabled, and the account needs read access to the queue
tree and interface statistics. This temporary lab setup sends credentials over
the network without encryption and should not be used on an untrusted network.

The monitor refreshes queue statistics and the `ether5` transmit rate once per
second. Press Ctrl+C to exit.

## RouterOS queue profile controller

`profile_controller.py` applies predefined committed-rate profiles to the
`qos-high`, `qos-medium`, and `qos-low` Queue Tree entries. It changes only each
queue's `limit-at` value; it does not make automatic decisions or use
reinforcement learning yet.

| Profile | qos-high | qos-medium | qos-low |
| --- | ---: | ---: | ---: |
| `balanced` | 1M | 1M | 1M |
| `protected` | 1250k | 1250k | 250k |
| `maximum_protection` | 1500k | 1500k | 100k |

Use the same RouterOS REST connection variables as the monitor, but provide an
account with permission to read and write the queue tree:

```bash
export MIKROTIK_USER='controller'
export MIKROTIK_PASSWORD='your-password'
python3 profile_controller.py protected
```

The router defaults to `192.168.88.34` on HTTP port 80 and can be overridden
with `MIKROTIK_HOST` and `MIKROTIK_REST_PORT`. The controller first verifies
that all three required queues exist, then updates them using their RouterOS
resource IDs. The same plain-HTTP lab-network warning described for the monitor
applies to this tool.

The controller can also be imported by later experiment code:

```python
from profile_controller import set_profile

set_profile("maximum_protection")
```

## Static controller runner

`run_controller.py` connects monitoring and profile control in one loop. Its
`StaticController` polls the current queue and `ether5` transmit statistics,
always selects the profile supplied on the command line, applies that profile,
and prints a compact status line. It does not make decisions from the observed
statistics yet, so it provides a simple baseline for validating the complete
measurement-and-control path.

```bash
python3 run_controller.py balanced
python3 run_controller.py protected --interval 10
```

The default interval is five seconds. The same RouterOS environment variables
and read/write permissions required by `profile_controller.py` apply. Press
Ctrl+C to stop the loop.
