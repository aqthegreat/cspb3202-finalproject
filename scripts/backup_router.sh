#!/usr/bin/env bash

set -Eeuo pipefail

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
readonly BACKUP_DIR="${PROJECT_DIR}/routerbackups"

router_host="${MIKROTIK_HOST:-192.168.88.34}"
router_user="${MIKROTIK_USER:-backup}"
router_port="${MIKROTIK_SSH_PORT:-22}"
identity_file="${MIKROTIK_SSH_KEY:-${HOME}/.ssh/mikrotik_backup}"

usage() {
    cat <<'EOF'
Usage: scripts/backup_router.sh [options]

Retrieve a MikroTik RouterOS text configuration export over SSH and save it in
the project's routerbackups directory.

Options:
  -H, --host HOST       Router host (MIKROTIK_HOST; default: 192.168.88.34)
  -u, --user USER       RouterOS user (MIKROTIK_USER; default: backup)
  -p, --port PORT       SSH port (MIKROTIK_SSH_PORT; default: 22)
  -i, --identity FILE   Private SSH key (MIKROTIK_SSH_KEY;
                        default: ~/.ssh/mikrotik_backup)
  -h, --help            Show this help

The script requires SSH key authentication and will not prompt for a password.
SSH host-key verification remains enabled. The export intentionally excludes
sensitive values such as passwords and private keys.
EOF
}

die() {
    printf 'Error: %s\n' "$*" >&2
    exit 1
}

while (( $# > 0 )); do
    case "$1" in
        -H|--host)
            (( $# >= 2 )) || die "$1 requires a value"
            router_host="$2"
            shift 2
            ;;
        -u|--user)
            (( $# >= 2 )) || die "$1 requires a value"
            router_user="$2"
            shift 2
            ;;
        -p|--port)
            (( $# >= 2 )) || die "$1 requires a value"
            router_port="$2"
            shift 2
            ;;
        -i|--identity)
            (( $# >= 2 )) || die "$1 requires a value"
            identity_file="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            die "unknown argument: $1"
            ;;
    esac
done

[[ "$router_host" != -* && "$router_host" != *[[:space:]]* ]] || die "invalid router host"
[[ "$router_user" =~ ^[A-Za-z0-9._-]+$ ]] || die "invalid router username"
[[ "$router_port" =~ ^[0-9]+$ ]] || die "SSH port must be a number"
(( router_port >= 1 && router_port <= 65535 )) || die "SSH port must be between 1 and 65535"

ssh_options=(
    -o BatchMode=yes
    -o ConnectTimeout=10
    -o StrictHostKeyChecking=yes
    -p "$router_port"
)

if [[ -n "$identity_file" ]]; then
    [[ -f "$identity_file" ]] || die "SSH identity file does not exist: $identity_file"
    ssh_options+=( -i "$identity_file" -o IdentitiesOnly=yes )
fi

umask 077
mkdir -p -- "$BACKUP_DIR"
chmod 700 -- "$BACKUP_DIR"

timestamp="$(date '+%Y-%m-%d_%H-%M-%S')"
backup_file="${BACKUP_DIR}/router-config_${timestamp}.rsc"
temporary_file="${backup_file}.partial"

cleanup() {
    rm -f -- "$temporary_file"
}
trap cleanup EXIT

printf 'Retrieving RouterOS configuration from %s@%s...\n' "$router_user" "$router_host"

if ! ssh "${ssh_options[@]}" "${router_user}@${router_host}" '/export terse' > "$temporary_file"; then
    die "SSH export failed; no backup was saved"
fi

[[ -s "$temporary_file" ]] || die "router returned an empty configuration export"

if grep -q '^#error exporting' "$temporary_file"; then
    die "RouterOS reported an export error; no backup was saved"
fi

mv -- "$temporary_file" "$backup_file"
trap - EXIT

printf 'Configuration saved to %s\n' "$backup_file"
