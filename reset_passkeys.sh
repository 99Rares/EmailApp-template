#!/usr/bin/env bash
# Emergency: remove every passkey so password sign-in works again. Run on the server: ./reset_passkeys.sh  (--yes skips the question)
set -euo pipefail
cd "$(dirname "$0")"
exec docker compose exec flask_app python -m email_app.reset_passkeys "$@"
