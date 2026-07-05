# Ordia Bridge — Native Windows Installer

A double-click installer (like Dropbox/Zoom): **no terminal, no Docker, no config files** for the end user.

## What the customer experiences
1. Clicks **Scarica Ordia Bridge** in Ordia → downloads `OrdiaBridgeSetup.exe`.
2. Double-click → **Installa** (may ask for admin permission — one click "Sì").
3. A friendly window opens → enters the **pairing code** (or reads it from the **QR Code** shown in Ordia) → **Connetti**.
4. Sees **"Bridge collegato con successo."** Done. It runs forever in the background.

## What gets installed
- `OrdiaBridge.exe` — native agent (Python, packaged with PyInstaller; stdlib only).
- Registered as a **Windows Service** (via WinSW) → **auto-starts on every boot**, restarts on failure.
- Config stored in `%PROGRAMDATA%\OrdiaBridge\config.json` (created after pairing).
- **Auto-update**: the service checks `/api/bridge/installer/windows` every 12h and silently installs newer versions.
- **Logs**: rolled locally; uploaded to Ordia every hour **only if the user consents** (checkbox in the setup window).

## Build (automatic, via GitHub Actions)
Pushing a tag `bridge-v1.0.0` (or running the workflow manually) builds the installer on a **Windows runner**:
- `.github/workflows/build-bridge.yml` → PyInstaller → WinSW → Inno Setup → `OrdiaBridgeSetup.exe` (artifact + release asset).

Then set the backend env var `BRIDGE_INSTALLER_URL` to the release asset URL so the **Scarica Ordia Bridge** button serves it.

## Build manually on a Windows PC (alternative)
```
cd bridge_native
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name OrdiaBridge --hidden-import config_gui ordia_bridge.py
:: download WinSW-x64.exe into winsw\OrdiaBridgeService.exe
:: install Inno Setup, then:
ISCC.exe OrdiaBridge.iss   ::  -> Output\OrdiaBridgeSetup.exe
```

## Unsigned version — Windows SmartScreen (temporary)
Until a code-signing certificate is added, on first run Windows shows a blue **SmartScreen** notice.
Simple steps for the user (document with screenshots in onboarding):
1. Click **"Ulteriori informazioni"** (More info).
2. Click **"Esegui comunque"** (Run anyway).
That's it. To remove this warning permanently, add a code-signing step (`signtool.exe`) in the CI workflow with an OV/EV certificate.

## Notes / current limits
- Native MVP delivers approved orders to a local delivery folder (canonical/rendered payload). ERP-specific automated delivery adapters (the self-learning RPA path) are layered on next without changing pairing/connection.
- QR scanning is a convenience to *read* the code with a phone; pairing itself happens in the desktop window.
