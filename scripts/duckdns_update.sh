#!/bin/sh
# Keeps the DuckDNS hostname pointed at this machine's current public IP.
# Reads DUCKDNS_TOKEN and DUCKDNS_DOMAIN from config.env (gitignored, never commit real values).
# Run on a schedule (e.g. cron every 5 min) on whichever box actually hosts the server.

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_ENV="$SCRIPT_DIR/../config.env"

if [ -f "$CONFIG_ENV" ]; then
  # shellcheck disable=SC1090
  . "$CONFIG_ENV"
fi

if [ -z "${DUCKDNS_TOKEN:-}" ] || [ -z "${DUCKDNS_DOMAIN:-}" ]; then
  echo "DUCKDNS_TOKEN and DUCKDNS_DOMAIN must be set (in config.env or the environment)." >&2
  exit 1
fi

RESPONSE=$(curl -fsS "https://www.duckdns.org/update?domains=${DUCKDNS_DOMAIN}&token=${DUCKDNS_TOKEN}&ip=")

if [ "$RESPONSE" != "OK" ]; then
  echo "DuckDNS update failed: $RESPONSE" >&2
  exit 1
fi

echo "DuckDNS updated: ${DUCKDNS_DOMAIN}.duckdns.org -> current public IP"
