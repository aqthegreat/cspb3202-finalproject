#!/usr/bin/env bash

set -Eeuo pipefail

readonly START_PORT=5201
readonly END_PORT=5205

command -v iperf3 >/dev/null 2>&1 || {
    printf 'Error: iperf3 is not installed or is not in PATH.\n' >&2
    exit 1
}

pids=()

cleanup() {
    if (( ${#pids[@]} > 0 )); then
        printf '\nStopping iperf3 servers...\n'
        kill "${pids[@]}" 2>/dev/null || true
        wait "${pids[@]}" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

for (( port = START_PORT; port <= END_PORT; port++ )); do
    printf 'Starting iperf3 server on port %d...\n' "$port"
    iperf3 --server --port "$port" &
    pids+=("$!")
done

printf 'All iperf3 servers are running. Press Ctrl-C to stop them.\n'

# Keep the launcher alive while the servers run so signals can clean them up.
wait
