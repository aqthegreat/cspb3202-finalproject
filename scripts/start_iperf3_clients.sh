#!/usr/bin/env bash

set -Eeuo pipefail

usage() {
    printf 'Usage: %s SERVER_HOST\n' "${0##*/}"
    printf 'Start three 60-second iperf3 clients on ports 5201-5203.\n'
}

if (( $# != 1 )); then
    usage >&2
    exit 1
fi

readonly SERVER_HOST="$1"
readonly DURATION=60
readonly PORTS=(5201 5202 5203)
readonly DSCP_VALUES=(0 26 46)

[[ -n "$SERVER_HOST" && "$SERVER_HOST" != -* && "$SERVER_HOST" != *[[:space:]]* ]] || {
    printf 'Error: invalid server host.\n' >&2
    exit 1
}

command -v iperf3 >/dev/null 2>&1 || {
    printf 'Error: iperf3 is not installed or is not in PATH.\n' >&2
    exit 1
}

pids=()

cleanup() {
    if (( ${#pids[@]} > 0 )); then
        kill "${pids[@]}" 2>/dev/null || true
        wait "${pids[@]}" 2>/dev/null || true
    fi
}
trap cleanup INT TERM

for index in "${!PORTS[@]}"; do
    port="${PORTS[$index]}"
    dscp="${DSCP_VALUES[$index]}"

    printf 'Starting client to %s:%d with DSCP %d for %d seconds...\n' \
        "$SERVER_HOST" "$port" "$dscp" "$DURATION"
    iperf3 --client "$SERVER_HOST" --port "$port" \
        --dscp "$dscp" --time "$DURATION" &
    pids+=("$!")
done

status=0
for pid in "${pids[@]}"; do
    wait "$pid" || status=1
done

exit "$status"
