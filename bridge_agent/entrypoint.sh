#!/usr/bin/env bash
# Ordia Bridge agent entrypoint.
# - First run: pair with the 6-digit code (ORDIA_PAIR_CODE), then keep the token.
# - Subsequent runs: resume from the stored token in /data.
# - Optional self-update: pull a newer, SIGNED agent bundle before starting.
set -euo pipefail

BACKEND="${ORDIA_BACKEND:?set ORDIA_BACKEND to your Ordia cloud URL, e.g. https://app.ordia.app}"
STATE="${ORDIA_BRIDGE_STATE:-/data/.agent_state.json}"
INTERVAL="${ORDIA_BRIDGE_INTERVAL:-5}"

# --- Optional signed self-update ------------------------------------------
# The cloud publishes agent bundles + a detached signature; we verify against a
# pinned public key baked into the image before swapping any code. Disabled by
# default (ORDIA_SELF_UPDATE=1 to enable) so air-gapped installs stay pinned.
if [[ "${ORDIA_SELF_UPDATE:-0}" == "1" && -f /opt/ordia-bridge/ordia_pub.pem ]]; then
  echo "[update] checking for a newer signed agent bundle…"
  if curl -fsS "$BACKEND/api/bridge/agent-bundle" -o /tmp/bundle.tar.gz \
     && curl -fsS "$BACKEND/api/bridge/agent-bundle.sig" -o /tmp/bundle.sig \
     && openssl dgst -sha256 -verify /opt/ordia-bridge/ordia_pub.pem \
          -signature /tmp/bundle.sig /tmp/bundle.tar.gz; then
    tar -xzf /tmp/bundle.tar.gz -C /opt/ordia-bridge
    echo "[update] verified signature — agent updated"
  else
    echo "[update] no verified update applied (keeping pinned version)"
  fi
fi

# --- Pair once, then run the polling loop ---------------------------------
if [[ ! -f "$STATE" && -n "${ORDIA_PAIR_CODE:-}" ]]; then
  echo "[pair] pairing with code $ORDIA_PAIR_CODE"
  python agent.py --backend "$BACKEND" --pair "$ORDIA_PAIR_CODE"
fi

echo "[run] starting Ordia Bridge agent (interval ${INTERVAL}s)"
exec python agent.py --backend "$BACKEND" --interval "$INTERVAL"
