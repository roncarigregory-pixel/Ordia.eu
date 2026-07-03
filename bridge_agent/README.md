# Ordia Bridge — reference agent & RPA PoC

Prova pratica che il Bridge può **creare un ordine dentro un ERP reale**, sia via
consegna file/API sia via **RPA** (mouse+tastiera sulla UI), operando come un umano.

## Contenuto
- `agent.py` — agente di riferimento (cloud backbone): pairing con codice a 6 cifre,
  poll della coda `delivery_jobs`, consegna, ack. Testabile via HTTP.
- `rpa_odoo.py` — **PoC RPA-lite**: pilota la UI web di un ERP reale (Odoo) con
  Playwright (login, nuovo ordine, cliente, righe prodotto, salva). Screenshot in `rpa_shots/`.

## PoC RPA verificata (Odoo reale, locale)
Ambiente: Odoo 18 + PostgreSQL installati nel pod, DB `ordia` con dati demo, UI su
`http://localhost:8069` (admin/admin).

Flusso eseguito dallo script (solo mouse+tastiera, nessuna API di scrittura):
1. Login nella UI.
2. Sales → New (nuovo preventivo).
3. Cliente: "Azure Interior" (autocomplete).
4. Righe: `Large Cabinet` ×2, `Storage Box` ×5.
5. Salva.

Risultato: ordine **S00021** salvato. Verifica indipendente via API Odoo:
`partner=Azure Interior, righe=[Large Cabinet×2 €640, Storage Box×5 €79], totale €719, state=draft`.

### Riprodurre
```bash
service postgresql start
odoo -c /etc/odoo/odoo.conf -d ordia   # avvia Odoo su :8069
PLAYWRIGHT_BROWSERS_PATH=/pw-browsers python /app/bridge_agent/rpa_odoo.py
```
Passando un file JSON con l'ordine canonico come primo argomento, la RPA usa quello.

## Note produzione
- Qui la RPA gira headless nel pod. In produzione l'agente gira sul dispositivo del
  cliente (NAS/mini-PC), può girare headless o visibile.
- Il mapping SKU/cliente canonico → master-data dell'ERP è lo step successivo
  (import liste codici) che porta l'affidabilità dal 90% al "sicuro".
- RPA è l'ultima spiaggia (Class D, ERP UI-only). Per ERP con API/file si usano i
  canali più stabili (connettore cloud, file+trigger) prima dell'RPA.

## Deploy on-prem (Fase 2 — container)
Un solo comando su NAS/mini-PC del cliente. **Outbound-only**: nessuna porta aperta, nessun IT.
```bash
# 1) crea l'agente in Ordia (Configurazione → Bridge) e copia il codice a 6 cifre
# 2) sul dispositivo del cliente:
ORDIA_BACKEND=https://app.ordia.app ORDIA_PAIR_CODE=123456 docker compose up -d
```
Il container (`Dockerfile` + `docker-compose.yml` + `entrypoint.sh`) include Playwright+Chromium,
persiste il token e la config di consegna in `./data` (le credenziali ERP restano ON-PREM),
ha un `HEALTHCHECK` e `restart: unless-stopped`.

**Ciclo di vita**: dopo il pairing l'agente entra in **apprendimento** (le consegne sono bozze
di prova), matura da solo e Ordia avvisa quando è **pronto** all'inserimento automatico.

**Self-update firmato** (opt-in, `ORDIA_SELF_UPDATE=1`): scarica il bundle agente + firma dal
cloud e lo applica **solo** dopo verifica `openssl` con chiave pubblica pinnata nell'immagine.

**Resilienza**: coda cloud durevole con retry/backoff + TTL; se il dispositivo è spento gli
ordini restano in coda e vengono consegnati **al risveglio**; heartbeat + rilevamento offline
proattivo (Ordia avvisa prima che te ne accorga tu).

**Robustezza RPA**: pre-flight sull'impronta della UI (rifiuta di scrivere se lo schermo non
combacia) + self-healing (riapprende e riprova) + circuit-breaker (adapter poco affidabile →
quarantena automatica, escluso dalla rete finché non si auto-ripara).

## Braccio DESKTOP (ERP senza API né web) — learn-by-demonstration
Per gestionali **desktop Windows senza API né DOM** (Danea, Mexal, TeamSystem desktop, ...)
il Bridge impara **guardando** l'operatore, tramite l'accessibility tree di Windows (UI Automation)
con visione/OCR solo come rete di sicurezza. Principio: **LLM/visione per imparare e riparare,
esecuzione deterministica a runtime** (mai click decisi dall'LLM).

Tipi di adapter (`adapter_kind`): `web_dom` (Playwright/DOM) · `desktop_uia` (Windows UIA) ·
`file_import` (CSV/XML) · `api`. Il Delivery Router sceglie il braccio per classe di ERP.

### Come funziona (3 passi)
1. **Dimostrazione** — l'operatore crea UN ordine a mano mentre `recorder.py` registra la traccia
   (per ogni click: `name`/`automation_id`/`control_type`/finestra; testo digitato) + qualche screenshot.
2. **Compilazione AI (cloud)** — `POST /api/bridge/adapters/compile` invia la traccia (+screenshot)
   a Claude, che produce un `desktop_adapter_spec` **deterministico**: passi ordinati con locator
   semantici (automation_id → name → text_anchor → bbox), `field_map` canonico, e `line_loop`
   (i passi ripetuti per ogni riga ordine). Adapter salvato `pending_confirmation`.
3. **Conferma + Replay** — confermi l'ordine di prova in Ordia (`/confirm` → `active`).
   `replay_desktop.py` esegue i passi via UIA in modo deterministico; pre-flight sull'impronta
   della finestra; su errore → self-heal (re-introspezione + ricompilazione + `/heal`) e riprova.

### Installazione/test su Windows
```powershell
# sul PC del cliente dove gira il gestionale
pip install pywinauto pynput mss pillow pytesseract
# 1) accoppia l'agente (una volta)
python agent.py --backend https://app.ordia.app --pair 123456
# 2) registra la dimostrazione (crea un ordine, poi premi ESC)
python recorder.py --backend https://app.ordia.app --erp-key "danea/2024" --erp-guess "Danea Easyfatt"
# 3) conferma l'ordine di prova in Ordia -> adapter 'active'
# 4) consegna reale (impostare delivery_mode='desktop_uia' + erp_key in config.json)
python replay_desktop.py order.json --backend https://app.ordia.app --erp-key "danea/2024"
```
`config.json` (on-prem, mai nel cloud): `{"delivery_mode": "desktop_uia", "erp_key": "danea/2024"}`.

### Schema (sintesi) `desktop_adapter_spec`
```json
{"platform":"windows-uia","erp_guess":"Danea Easyfatt",
 "window":{"title_regex":"Easyfatt.*","fingerprint_controls":["txtCliente","gridRighe","btnSalva"]},
 "field_map":{"customer_name":"txtCliente","sku":"colArticolo","quantity":"colQta"},
 "steps":[{"seq":1,"op":"open_form","locator":{"by":"name","value":"Nuovo","control_type":"Button"}},
          {"seq":2,"op":"set_field","field":"customer_name","locator":{"by":"automation_id","value":"txtCliente","control_type":"Edit"}},
          {"seq":3,"op":"add_line","locator":{"by":"name","value":"Aggiungi riga","control_type":"Button"}},
          {"seq":4,"op":"set_field","field":"sku","locator":{"by":"automation_id","value":"colArticolo","control_type":"Edit"}},
          {"seq":5,"op":"set_field","field":"quantity","locator":{"by":"automation_id","value":"colQta","control_type":"Edit"}},
          {"seq":6,"op":"save","locator":{"by":"name","value":"Salva","control_type":"Button"}}],
 "line_loop":{"start_seq":3,"end_seq":5},"confidence":0.9,"notes":"..."}
```
Nota: la RPA desktop gira **solo su Windows** (dove sta il gestionale). Su Linux/macOS o app
opache (Citrix/RDP/green-screen) si usa il fallback visione+OCR. Lo schema resta generico per
qualsiasi ERP Windows.


