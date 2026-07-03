# Ordia — PRD & Progress

## Prodotto
Ordia è una piattaforma AI di automazione ordini per distributori all'ingrosso B2B.
Riceve ordini da testo, WhatsApp, email, PDF, Excel, CSV, immagini e vocali, li estrae con
Claude Sonnet 4.6, li abbina al catalogo prodotti e apprende dalle correzioni dell'operatore.
UI e comunicazione con l'utente: **ITALIANO**. Benchmark UX: Stripe / Linear.

## Stack
- Frontend: React + TailwindCSS + Shadcn UI + framer-motion + @dnd-kit + lucide-react
- Backend: FastAPI + MongoDB (motor), JWT auth multi-tenant
- AI: Claude Sonnet 4.6 (estrazione) + Whisper (audio) via Emergent LLM Key
- Design system: navy #0B1E3B, ai-accent indigo #6366F1, font Satoshi/Manrope/JetBrains Mono

## Ordine di priorità (deciso dall'utente): happy-path prima, poi rifinitura
Ogni milestone: funzionante, testata E2E, responsive, NO dati fake, production-ready.

## ✅ Completato

### P0 — Core Workflow (iteration_6, 100% pass)
- **Nuovo Ordine** (`NewOrder.js`): 8 canali (Testo, WhatsApp, Email, PDF, Excel, CSV, Foto, Vocale),
  drag & drop universale, stepper AI animato (framer-motion, 6 fasi).
- **Estrazione AI** (`POST /api/orders/extract` → `ingest_order`/`run_extraction`): estrae cliente,
  articoli, quantità; abbinamento catalogo + confidenza + learning loop.
- **Revisione Ordine** (`OrderReview.js`): layout 2 colonne (sorgente originale sticky | tabella
  editabile), ricerca prodotto combobox (`ProductSearch.js`), aggiungi/elimina/duplica/**riordina
  (dnd-kit)**, suggerimenti AI, warning bassa confidenza, editing cliente/data, **cronologia modifiche**.
- **Conferma** (`POST /api/orders/{id}/validate` → status validated + learning).
- **Esportazione** (`GET /api/orders/{id}/export?format=`): **PDF (reportlab), Excel (openpyxl),
  CSV, JSON** — bytes costruiti prima della mutazione stato; PDF con escaping HTML.
- **Command Center** (`Dashboard.js` + `GET /api/command-center`): riepilogo in linguaggio naturale,
  ordini da revisionare, attività recente, notifiche AI, clienti recenti — **dati reali**, niente KPI finti.

### P1 — Search, Customers, Catalog, Mobile (iteration_7 + iteration_8, 100% pass)
- **Ricerca globale** (`GlobalSearch.js` in `AppShell`, ⌘K + `GET /api/search`): clienti/ordini/prodotti.
- **Clienti** (`Customers.js` + `CustomerDetail.js`, `GET /api/customers`, `/api/customers/{name}`):
  griglia card, storico ordini, insight AI, prodotti abituali.
- **Catalogo** (`Catalog.js`): CRUD prodotti + import CSV/Excel, design allineato.
- **AppShell** ridisegnato: sidebar minimale (lucide), nav Clienti, ricerca integrata.
- **Mobile**: bottom-nav dedicata, sollevata sopra il badge piattaforma (fix iteration_8).

## ✅ P0 completo (incl. gap nuova specifica)
- **Nuovo Ordine**: 9 canali (Testo, WhatsApp, Email, PDF, Excel, CSV, Foto, **Scansione** fotocamera, Vocale)
  + drag&drop + copia/incolla + stepper AI animato.
- **Revisione**: 2 colonne, tabella editabile, ricerca prodotto, **creazione nuovo prodotto inline**,
  aggiungi/elimina/duplica/riordina, suggerimenti AI, warning, confidenza, cronologia, **assegnatario**.
- **Esportazione**: PDF, Excel, CSV, JSON, **Email (Resend, con PDF allegato)**, **Richiesta chiarimenti via email**.
- Architettura ERP-agnostica (layer export generico) pronta per connettori futuri.

## ✅ Automazioni (P1) — verificate iter_9 (8/8 BE + 5/5 FE)
- Conferma automatica (soglia configurabile) + trattieni nuovi clienti.
- **Routing automatico**: assegna ordini da revisionare a un membro del team.
- **Richieste chiarimenti automatiche/manuali** via email (Resend).
- `GET/PUT /api/automations`, `POST /api/orders/{id}/send-email`, pagina `AutomationSetup.js`.

## 🔌 Integrazioni
- Claude Sonnet 4.6 + Whisper (Emergent LLM Key).
- **Resend** email: `RESEND_API_KEY` + `SENDER_EMAIL=onboarding@resend.dev` in backend/.env.
  ⚠️ TEST MODE: invii reali solo verso l'email dell'account Resend / `delivered@resend.dev`.
  Per la produzione: verificare un dominio su Resend e impostare `SENDER_EMAIL` sul dominio verificato.

## ✅ Enterprise Integrations — ERP Platform (P1) — verificata iter_10 (16/16 BE + 5/5 FE)
Architettura ERP-first **modulare a plug-in**, sopra il formato standard `ordia.order.v1`.
- Registry connettori: `generic`, `odoo`, `sap`, `business_central`, `zucchetti`, `teamsystem`
  (transport REST configurabile — endpoint reali quando configurati, nessun finto successo).
- Connessioni per-azienda con **mapping** (campi/prodotti/unità/IVA/magazzini/listini) e stato.
- **Coda sync con retry** (`sync_jobs`): export falliti restano in coda, ordine MAI perso, log dettagliati.
- Import catalogo/clienti via endpoint configurati; export automatico su conferma (catena automazione).
- Endpoints: `/api/erp/connectors`, `/api/erp/connections` (CRUD), `/test`, `/import`, `/sync-order/{id}`,
  `/erp/jobs`, `/erp/jobs/{id}/retry`. Frontend: `ErpSetup.js` (marketplace + config dinamica + mapping + log).

## ✅ Notification Center (P1) — verificata iter_10
Centro operativo in tempo reale (polling 20s). Notifiche generate da eventi reali del pipeline:
ordini bloccati, confidenza bassa, auto-confermati, nuove email/WhatsApp/PDF, errori ERP/export,
clienti sconosciuti, prodotti non riconosciuti, richieste cliente.
- Ogni notifica: priorità (alta/media/bassa), cliente, orario, azione consigliata, azioni rapide.
- Filtri (stato/tipo/ricerca), assegna/archivia/risolvi, apri ordine. Badge conteggio in sidebar.
- **Catene automazione**: alta confidenza → auto-conferma → export ERP; conferma manuale → export + risolve notifiche.
- Endpoints: `/api/notifications` (filtri), `/counts`, `PATCH /{id}`. Frontend: `NotificationCenter.js`.

## 🔒 Hardening & Production readiness (sessione corrente)
- **Auth a cookie HttpOnly**: JWT in cookie `ordia_token` (Secure, SameSite=Lax) su login/register; `get_current_user`
  accetta Bearer (precedenza) o cookie (fallback browser); `POST /auth/logout` pulisce il cookie; frontend axios
  `withCredentials`, **nessun token in localStorage** (XSS-safe). Verificato via curl + browser + pytest.
- **WhatsApp HMAC**: verifica `X-Hub-Signature-256` (HMAC-SHA256) quando l'account ha `app_secret`. Verificato (unit + `test_whatsapp_full_flow` firmato).
- **Ri-test upload E2E**: CSV, Excel, PDF, immagine (OCR/vision) estratti correttamente via pipeline reale (Claude). Audio testato in fork precedente.
- **Deploy readiness**: unico blocker (import `useMemo`) risolto; restano solo raccomandazioni di performance (projection/pagination Mongo).
- Suite pytest: **102 passati**. Fail residue non legate al codice: httpbin lento (flakiness ERP esterna), varianza LLM (csv), fixture audio.

## ✅ Verifica fix "home bianca" + Deploy readiness (sessione corrente, 2026-07-02)
- **Home bianca CONFERMATA risolta**: login OK, Command Center apre, cookie+Bearer entrambi 200,
  refresh non rompe sessione, Notification Center carica, nessun errore console bloccante
  (401 su /auth/me è atteso: precede l'auto-login pilot mode).
- **Deployment readiness: PASS** (deployment_agent): nessun blocker, env vars corrette, no secret hardcoded,
  CORS ok, load_dotenv ok, query Mongo con limiti. Deploy da avviare dal pulsante piattaforma.
- ⚠️ PILOT_MODE attivo (auto-login demo). Per produzione con login reale: `REACT_APP_PILOT_MODE=false`.

## ✅ Lavori autonomi CTO — alto impatto (2026-07-02)
Regola rispettata: nessuna modifica al flow principale né a login/deploy/email/WhatsApp/IMAP.
- **Dashboard ROI**: nuovo `GET /api/analytics/roi` (ore risparmiate, risparmio € stimato, tasso automazione,
  volume processato, avg confidence, trend 8 settimane). Banda 4-card in `Dashboard.js`. Verificato curl + UI.
- **Rate-limit webhook pubblici**: sliding-window in-memory per-IP su `POST /api/webhooks/whatsapp`
  (120 req/60s, configurabile via `WEBHOOK_RATE_LIMIT`/`WEBHOOK_RATE_WINDOW`). Verificato: 120 pass / 60 → 429.
- **Paginazione lista ordini**: `GET /api/orders?limit&skip&status&q` → `{items,total,limit,skip}` con filtro/ricerca
  server-side. `Orders.js` con controlli pagina + debounce ricerca. Verificato: pag.2 = 26–42/42.
- **Health endpoint**: `GET /api/health` pubblico (ping Mongo) per probe deploy/uptime. Verificato: `{status:ok,db:up}`.
- ⏸️ Refactor `server.py`: RIMANDATO (rischio rottura flow) — da fare in sessione dedicata con testing_agent.

## ✅ Ordia Bridge — Fase 1 (backbone cloud + AI Template Builder) — 2026-07-02
Decisione prodotto: il Bridge è il pilastro core. Costruito e validato E2E in preview (nessun core toccato oltre 1 riga di hook).
Backend (server.py, additivo prima di include_router):
- **AI Template Builder**: `POST /api/export-profiles/analyze` (Claude Sonnet 4.6 deduce formato/colonne da 1 file d'esempio),
  CRUD `/api/export-profiles`, renderer DETERMINISTICO `render_with_profile` (CSV/XLSX/XML), `GET /orders/{id}/export-profile/{pid}`.
- **Bridge backbone**: `bridge_agents` (pairing code 6 cifre + token), `POST /api/bridge/agents|pair`, PUT/DELETE,
  coda `delivery_jobs`, relay agente `GET /bridge/relay/poll` + `POST /bridge/relay/ack|heartbeat` (auth via header X-Bridge-Token),
  `enqueue_bridge_delivery` agganciato a validate_order (1 riga), `GET /bridge/jobs`.
- Notifiche `bridge_delivered` / `bridge_exception`. Indici Mongo aggiunti.
Frontend: `pages/setup/BridgeSetup.js` (upload+analyze+approva profilo, crea/gestisci agenti con codice pairing, log consegne) + route + card in Configurazione.
Agente di riferimento: `/app/bridge_agent/agent.py` (pair/poll/deliver-simulato/ack via HTTP; UA custom per bypassare CF 1010).
**Test E2E (curl+agent reale) PASSATO**: crea agente→pairing→validate ordine→coda→agente preleva→consegna nel formato Danea (`;`+decimali`,`)→ack delivered→notifica "Consegnato in Danea". Template Builder ha mappato correttamente 6/6 colonne.
Note: `enqueue` seleziona il primo agente paired+active dell'azienda (assunzione 1 agente/azienda per MVP; routing multi-agente = futuro).
NON fatto (differito su richiesta): agente on-prem firmato + auto-update + relay WebSocket (ora è polling).

## ✅ PoC RPA verificata (2026-07-02) — ordine creato in un ERP REALE
Obiettivo utente: provare che il Bridge crea un ordine in un ERP reale via RPA (non solo formato).
- Odoo 18 + PostgreSQL installati nel pod (DB `ordia`, dati demo, UI :8069). Danea/TeamSystem esclusi: desktop-only / licenza (nessun sandbox raggiungibile).
- `bridge_agent/rpa_odoo.py` (Playwright): login UI → Sales New → cliente "Azure Interior" → righe Large Cabinet×2, Storage Box×5 → Salva. Solo mouse+tastiera.
- Risultato: **ordine S00021 salvato**, verificato indipendentemente via API Odoo (totale €719, 2 righe). Screenshot in `bridge_agent/rpa_shots/`.
- Conferma il braccio Class D (UI-only) dell'architettura ibrida. Lo stesso pattern connettore vale per TeamSystem/BC via API quando ci saranno le credenziali.

## ✅ Bridge — canali di consegna provati su ERP REALE (Odoo) — 2026-07-02
Odoo 18 + PostgreSQL nel pod (DB `ordia`, :8069). Flusso Bridge: approva ordine → coda `delivery_jobs` → agente on-prem preleva → consegna → ack → notifica. Tutti verificati via API Odoo indipendente.
- **B — RPA integrata nel workflow (automatico)**: `agent.py` mode `rpa_odoo` → `rpa_odoo.py deliver_via_rpa` guida la UI (mouse+tastiera) → ordine **S00022**. Config locale on-prem `config.json` (mapping master-data). Notifica "Consegnato in Odoo".
- **A — Apprendimento da introspezione (moat)**: `rpa_learn.py` scopre 15 campi dal form live → Claude mappa canonico→campi (partner_id/product_template_id/product_uom_qty, conf 0.95) → `adapter_profile.json`. `rpa_replay.py` = motore GENERICO (nessun nome-campo hardcoded) → ordine **S00023** dal solo profilo appreso. ERP nuovo supportato senza nuovo codice.
- **C — API diretta**: `odoo_api.py deliver_via_api` (JSON-RPC, auth+search+create sale.order) mode `odoo_api` → ordine **S00024** (€158). Canale più veloce/robusto per Class A.
Agente `deliver()` con 3 canali: rpa_odoo | odoo_api | file. Screenshot in `bridge_agent/rpa_shots/`.

## ✅ Bridge — apprendimento robusto + conferma + master-data (2026-07-03)
Tutto provato E2E su Odoo reale (Odoo 18 + PostgreSQL nel pod; reinstallabile con `bridge_agent/setup_odoo.sh` — i pacchetti di sistema sono effimeri tra i restart del pod, /app e Mongo persistono).
- **Adapter Profile nel backend + effetto-rete**: collezioni `erp_adapters`(condivisa) + `erp_master_data`(per-azienda). Endpoint `POST/GET /bridge/adapters`, `GET /bridge/adapters/resolve` (agente), `POST /bridge/adapters/{id}/confirm`, `PUT /bridge/adapters/{id}/heal`. resolve restituisce l'adapter ACTIVE di qualsiasi azienda → un cliente nuovo eredita l'ERP appreso da un altro.
- **Conferma umana su ordine di prova**: learn crea un ordine di prova → adapter `pending_confirmation` con `test_order_ref` → resolve dà 404 finché non confermato → `confirm` → `active`. UI: sezione "3 · ERP appresi" con bottone "Conferma ordine di prova" + badge Attivo.
- **Master-data sync**: `bridge_agent/master_data_import.py` importa da Odoo (2 clienti, 41 prodotti, 1 IVA) → `POST /bridge/master-data` → UI mostra il riepilogo. Rende il mapping "sicuro".
- **Self-healing**: `rpa_replay.py replay_with_healing` — se un selettore appreso fallisce (UI cambiata), ri-apprende via `rpa_learn.learn_adapter`, patcha lo spec, PUT `/heal`, riprova. Provato: adapter rotto → timeout → re-learn → ordine S00023 creato.
- Notifica `adapter_pending`. Indici Mongo per adapters/master-data.
Script agente: agent.py (3 canali), rpa_odoo.py, rpa_learn.py, rpa_replay.py, odoo_api.py, master_data_import.py, setup_odoo.sh.

## ✅ Bridge — versioning/metriche adapter + canale live self-healing (2026-07-03)
- **Versioning + metriche + effetto-rete guidato dai dati**: `erp_adapters` ora traccia deliveries/successes/failures/heal_count. Nuovo `POST /bridge/adapters/{id}/report` (agente). `resolve` sceglie il MIGLIORE adapter active per erp_key (success_rate poi versione; i nuovi adapter hanno un trial equo a 0.75). Verificato: v2 rate 1.0 batte v1 rate 0.6 → selezionato v2.
- **Canale live `rpa_learned` in agent.py**: risolve l'adapter active dal backend → consegna via `replay_with_healing` (self-healing) → riporta success/failure (metriche). Provato live E2E: ordine approvato → coda → agente risolve v2 → crea ordine reale **S00021** in Odoo → ack → metriche aggiornate (v2 deliveries:1 succ:1). Il replay ora ha default strutturali (login/new_order/save) → robusto anche con spec minimale.
- `bridge_agent/setup_odoo.sh` ora scrive `odoo.conf` (reinstall affidabile dopo i restart effimeri del pod).

## ✅ Bridge — ciclo di vita "impara prima di scrivere" (2026-07-03)
Risolve i 4 rischi commerciali (fragilità RPA, fiducia, deploy, master-data) con un onboarding realistico: il Bridge NON è operativo appena installato, matura nel tempo sui segnali reali e avvisa quando è pronto.
- **Stati di maturità** su `bridge_agents.maturity`: `unpaired` → `learning` (shadow: ordini consegnati come **bozze di prova**, mai finali) → `ready` (readiness ≥ 0.85 → notifica) → `active` (inserimento automatico reale). Pausa: torna a `learning`.
- **Readiness score** (`compute_readiness`/`recompute_readiness`): formato 0.35 · clienti 0.15 · prodotti 0.10 · ordini-di-prova(0..5) 0.30 · osservazione(0..7g) 0.10. Segnali reali dominano; il tempo è solo un bonus (testabile).
- **Delivery mode**: i `delivery_jobs` portano `mode: shadow|live` (live solo se `maturity==active`). Ack shadow → `dry_runs++`, ordine NON marcato esportato, recompute readiness. Ack live → comportamento esistente.
- Endpoint: `GET /bridge/agents/{id}/readiness`, `POST /bridge/agents/{id}/activate` (guardato dalla soglia), `POST /bridge/agents/{id}/pause`. Recompute agganciato a: ack shadow, upsert master-data, confirm adapter, cambio profilo agente.
- Notifiche nuove: `bridge_learning` (al pairing), `bridge_ready` (promozione). Agente di riferimento `agent.py` ora mode-aware.
- UI `BridgeSetup.js`: badge maturità, barra readiness % + checklist per-agente, banner "pronto" con bottone **Attiva inserimento automatico**, banner attivo con **Rimetti in apprendimento**.
- **Test E2E (curl+mongo+agent) PASSATO**: pairing→learning 0.6 → 5 ack shadow → 0.9 auto-promosso `ready` + notifica `bridge_ready` → activate → `active`; guard blocca l'activate di un Bridge sotto soglia; pause riporta a `learning`. Smoke UI verificato (badge/barra/checklist renderizzati).

## ⏳ Bloccati su credenziali utente (verifica LIVE)
- **Deploy**: pronto — l'utente avvia dal pulsante Deploy della piattaforma.
- **Resend dominio**: verificare un dominio su Resend + impostare `SENDER_EMAIL`; ora invii solo a `delivered@resend.dev`.
- **IMAP live**: servono host/email/app-password reali per testare la ricezione email.
- **WhatsApp live**: servono credenziali Meta (app_secret, phone_number_id, verify_token); l'HMAC è già attivo.

## 🔜 Prossimo — P2 (backlog)
- **Buyer AI**: proposte di riordino per cliente, confronto fornitori.
- **Connettori ERP**: SAP, Odoo, Business Central sopra l'export generico.
- **Analytics avanzate + Forecast**: trend volumi, previsioni domanda.
- **Workflow personalizzabili**: builder di regole avanzate (oltre auto-confirm/routing attuali).
- **Produzione email**: verifica dominio Resend + mittente aziendale.

## 🧹 Debito tecnico
- `server.py` ~1750 righe → splittare in `routers/`, `services/`, `models/`.
- WhatsApp webhook: verifica HMAC X-Hub-Signature-256.
- Indice Mongo unico (company_id, external_id).

## Credenziali
Vedi `/app/memory/test_credentials.md` — demo@ordia.app / demo123 (pilot mode auto-login).

## Test reports
- iteration_6.json: P0 lifecycle (18/18 backend + frontend happy path)
- iteration_7.json: P1 (desktop 100%, mobile bug trovato)
- iteration_8.json: P1 mobile nav fix verificato (5/5)
- Suite backend: `/app/backend/tests/test_p0_lifecycle.py`
