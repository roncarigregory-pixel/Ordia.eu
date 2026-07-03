# Ordia Bridge — on-prem agent (NAS / mini-PC / appliance).
# Outbound-only: no inbound ports, no firewall changes, no IT project.
# Ships with Playwright + Chromium so the RPA (Class D, UI-only ERPs) works out of the box.
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

LABEL org.opencontainers.image.title="Ordia Bridge Agent" \
      org.opencontainers.image.vendor="Ordia" \
      org.opencontainers.image.source="https://ordia.app"

ENV PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    ORDIA_BRIDGE_STATE=/data/.agent_state.json \
    ORDIA_BRIDGE_CONFIG=/data/config.json \
    ORDIA_BRIDGE_OUTDIR=/data/delivered

WORKDIR /opt/ordia-bridge
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY *.py ./
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Persist pairing token + local delivery config outside the image.
VOLUME ["/data"]

# The agent only reaches OUT to the Ordia cloud; a broken delivery is retried, never lost.
HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
  CMD python -c "import os,json;print('paired' if os.path.exists(os.environ['ORDIA_BRIDGE_STATE']) else 'unpaired')" || exit 1

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
