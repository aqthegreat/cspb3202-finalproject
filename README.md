# Adaptive QoS with Reinforcement Learning

This CSPB 3202 final project investigates whether a reinforcement learning
agent can dynamically select Quality of Service (QoS) configurations on a
MikroTik router. The agent will use network performance measurements—including
packet loss, latency, and throughput—to balance the needs of traffic classes
identified by Differentiated Services Code Point (DSCP) values.

The project aims to protect high-priority traffic from packet loss and excess
latency while preserving as much throughput as possible for lower-priority
traffic.

## Documentation

- [Project notebook](NOTEBOOK.md) — chronological decisions, progress, and experiment notes
- [Project report](REPORT.md) — draft of the final project report

## Status

The project is in its initial documentation and design phase. The problem and
high-level objective have been defined; the experimental environment, RL
formulation, and evaluation plan remain to be documented and implemented.

## Router configuration backups

The backup helper retrieves a human-readable RouterOS configuration export over
SSH. It uses key authentication and stores timestamped files in the ignored
`routerbackups/` directory.

```bash
scripts/backup_router.sh
```

The defaults are router `192.168.88.34`, user `backup`, SSH port `22`, and key
`~/.ssh/mikrotik_backup`. Run `scripts/backup_router.sh --help` to see how to
override them using arguments or environment variables.
