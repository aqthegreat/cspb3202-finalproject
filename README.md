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

The project is in its initial documentation and design phase. The problem and
high-level objective have been defined; the experimental environment, RL
formulation, and evaluation plan remain to be documented and implemented.

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
