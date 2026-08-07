#!/usr/bin/env bash

set -Eeuo pipefail

usage() {
    printf 'Usage: %s SERVER_HOST PROFILE\n' "${0##*/}"
    printf 'Start a 60-second UDP iperf3 traffic profile.\n\n'
    printf 'PROFILE sets the high/medium/low DSCP bandwidths:\n'
    printf '  open     (or 0)  0,    0,    20M\n'
    printf '  minor    (or 1)  500K, 500K, 20M\n'
    printf '  moderate (or 2)  1M,   1M,   20M\n'
    printf '  major    (or 3)  2M,   2M,   20M\n'
}

if (( $# == 1 )) && [[ "$1" == "-h" || "$1" == "--help" ]]; then
    usage
    exit 0
fi

if (( $# != 2 )); then
    usage >&2
    exit 1
fi

readonly SERVER_HOST="$1"
readonly PROFILE="$2"
readonly DURATION=60

# Keep the class order aligned with the profile values: high, medium, low.
# The ports retain their original DSCP assignments.
readonly CLASS_NAMES=(high medium low)
readonly PORTS=(5203 5202 5201)
readonly DSCP_VALUES=(46 26 0)

case "$PROFILE" in
    open|0)
        readonly PROFILE_NAME=open
        readonly BANDWIDTHS=(0 0 20M)
        ;;
    minor|1)
        readonly PROFILE_NAME=minor
        readonly BANDWIDTHS=(500K 500K 20M)
        ;;
    moderate|2)
        readonly PROFILE_NAME=moderate
        readonly BANDWIDTHS=(1M 1M 20M)
        ;;
    major|3)
        readonly PROFILE_NAME=major
        readonly BANDWIDTHS=(2M 2M 20M)
        ;;
    *)
        printf 'Error: unknown profile %q.\n\n' "$PROFILE" >&2
        usage >&2
        exit 1
        ;;
esac

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

printf 'Launching %s profile (high/medium/low: %s/%s/%s).\n' \
    "$PROFILE_NAME" "${BANDWIDTHS[0]}" "${BANDWIDTHS[1]}" "${BANDWIDTHS[2]}"

for index in "${!PORTS[@]}"; do
    class_name="${CLASS_NAMES[$index]}"
    port="${PORTS[$index]}"
    dscp="${DSCP_VALUES[$index]}"
    bandwidth="${BANDWIDTHS[$index]}"

    if [[ "$bandwidth" == 0 ]]; then
        printf 'Skipping %s-priority client (DSCP %d; bandwidth 0).\n' \
            "$class_name" "$dscp"
        continue
    fi

    printf 'Starting UDP %s-priority client to %s:%d with DSCP %d at %s for %d seconds...\n' \
        "$class_name" "$SERVER_HOST" "$port" "$dscp" "$bandwidth" "$DURATION"
    iperf3 --client "$SERVER_HOST" --port "$port" \
        --udp --dscp "$dscp" --bitrate "$bandwidth" --time "$DURATION" &
    pids+=("$!")
done

status=0
for pid in "${pids[@]}"; do
    wait "$pid" || status=1
done

exit "$status"
