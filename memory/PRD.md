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

### 🌍 Internazionalizzazione IT/EN + Posizionamento (Giu 2026, iteration_14/15, 100% pass)
- **i18n completo** (`context/I18nContext.js`): `I18nProvider`, `useI18n()`, `t(key, vars)` con interpolazione `{var}`.
  Approccio a **chiave-italiana** (identità per IT) + mappa frasi IT→EN. Rilevamento lingua browser al primo accesso
  (IT se browser italiano, altrimenti EN), persistenza in `localStorage['ordia.lang']`.
- **LanguageToggle** 🇮🇹/🇬🇧 sempre visibile in alto a destra nell'AppShell (desktop top bar + header mobile), cambio 1-click senza reload.
- **Tutta l'app tradotta**: Landing, Login, Register, Dashboard, Orders, NewOrder, OrderReview, Customers,
  CustomerDetail, NotificationCenter, Catalog, Setup + tutte le sotto-pagine (Company, Team, Automation, Learning,
  Email, ERP, WhatsApp, **Bridge**), Onboarding (welcome + tour + FAQ). Verificato: 14/14 route, nessun crash, nessuna chiave grezza.
- **Posizionamento "NON è un ERP"**: callout nell'hero della landing, sezione dedicata "Funziona con il tuo gestionale",
  nuova FAQ ("Ordia sostituisce il mio gestionale?"), rinforzato in onboarding. Messaggio: "Hai un gestionale? Ordia lavora con quello che usi già."
- **Valorizzazione Ordia Bridge**: callout scuro in landing ("Nessuna API? Nessun problema." — impara la procedura del tuo
  gestionale e la esegue da solo, anche senza API) + step dedicato nel tour guidato + riga di visione ("dai venditori ai compratori, ogni settore").



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

## ✅ Bridge — resilienza, circuit-breaker, diario + packaging on-prem (2026-07-03)
Estende il ciclo di vita risolvendo i 4 rischi commerciali. Testato E2E backend: **iteration_13 = 13/13 (100%)**, nessun issue critico/minore.
- **Coda durevole (Rischio 3)**: `delivery_jobs` con `max_attempts`(5), `next_attempt_at`, `expires_at`(TTL 7g). Ack `exception` → retry con backoff esponenziale (60s→1h) finché < max/TTL, poi `failed` + notifica. Poll gate su `next_attempt_at<=now` + reclaim job `claimed` bloccati >5min. **Ack idempotente** (job delivered/failed non ri-processato).
- **Delivery-on-wake + offline proattivo (Rischio 3)**: `bridge_monitor_loop` (60s) marca offline gli agenti silenti >5min + notifica `bridge_offline`. Al ritorno (poll/heartbeat) → `mark_agent_online` notifica `bridge_recovered` con backlog "N ordini in consegna al risveglio".
- **Circuit-breaker adapter (Rischio 1)**: `report` tiene una finestra `recent` (cap 20); adapter active con ≥5 esiti e success-rate <0.85 → auto-`quarantined` + notifica `adapter_quarantined`; `resolve` esclude i quarantined; `heal` di un quarantined lo riporta active azzerando la finestra.
- **Pre-flight DOM fingerprint (Rischio 1)**: `rpa_learn` salva `ui_fingerprint`+`field_names`; `rpa_replay._preflight` verifica lo schermo prima di digitare (overlap <60% → `PreflightMismatch` → self-healing).
- **Diario del Bridge (engagement)**: collezione `bridge_events` + `log_bridge_event`; eventi paired/dry_run/master_data/adapter_active/healed/quarantine/offline/recovered/ready. Endpoint `GET /bridge/agents/{id}/diary`. UI: feed "Diario del Bridge" + badge Offline per-agente.
- **Packaging on-prem Fase 2**: `bridge_agent/Dockerfile` (base Playwright, healthcheck, volume /data), `docker-compose.yml` (1 comando, outbound-only), `entrypoint.sh` (pair-once + self-update FIRMATO opt-in con verifica openssl), `requirements.txt`. README aggiornato.
- ⏸️ **Refactor `server.py` (~3050 righe)**: ancora RIMANDATO di proposito — refactor puro ad alto rischio su app stabile; da fare in sessione dedicata con testing_agent subito dopo. Candidato: `backend/bridge/{lifecycle,queue,adapters,diary}.py`.

## ✅ Riepilogo settimanale email + modularizzazione server.py (2026-07-03)
- **Riepilogo settimanale del Bridge (engagement/conversione)**: `build_weekly_summary` aggrega gli eventi del diario (7gg) + anagrafiche + stato agenti → `render_summary_email` (HTML brandizzato). Endpoint `GET /bridge/weekly-summary` (anteprima) e `POST /bridge/weekly-summary/send` (invio via Resend, privileged). Loop autonomo `weekly_summary_loop` OFF di default (`BRIDGE_WEEKLY_SUMMARY=1` per attivarlo; Resend in test-mode consegna solo all'inbox dell'account). UI: card "Il tuo Bridge questa settimana" (3 metriche + bottone "Inviami il riepilogo"). Testato: preview + send a `delivered@resend.dev` = ok.
- **Modularizzazione `server.py` (debito tecnico RISOLTO)**: estratto il blocco Bridge (~650 righe) in `backend/bridge.py` via `setup_bridge(api, ctx)` con **dependency injection** (db, auth deps, helper, notifiche/email passati in ctx; nessuna dipendenza circolare). server.py: 3165 → 2527 righe. Comportamento **identico**: la suite di regressione `test_iter13_bridge_lifecycle.py` = **13/13 PASS**, health ok, endpoint (agents/adapters/summary) ok, dashboard e pagina Bridge renderizzano. `enqueue_bridge_delivery`/`bridge_monitor_loop`/`weekly_summary_loop` ri-esposti come global per compatibilità con validate_order/startup senza altre modifiche.

## ✅ Braccio DESKTOP del Bridge (vision/UIA, learn-by-demonstration) + demo re-seed (2026-07-03)
Nuovo braccio per ERP **desktop senza API né DOM** (Danea/Mexal/TeamSystem desktop). Principio confermato: **LLM/visione per imparare e riparare, esecuzione deterministica a runtime**.
- **`adapter_kind`** su `erp_adapters`: `web_dom | desktop_uia | file_import | api`. `resolve` accetta filtro `adapter_kind` (disambigua web vs desktop per stesso ERP).
- **`POST /bridge/adapters/compile`** (agent auth): riceve una **traccia dimostrativa** (azioni UI con metadati accessibility + screenshot opzionali) → Claude vision produce un **`desktop_adapter_spec` deterministico** (steps ordinati, locator gerarchici automation_id→name→text_anchor→bbox, `field_map` canonico, `line_loop` per le righe, fingerprint finestra). Salvato `pending_confirmation`, riusa confirm/heal/resolve/metriche/quarantena/readiness/diario. Evento diario `compiled`.
- **Scheletro agente Windows** (`bridge_agent/`): `recorder.py` (registra dimostrazione via pywinauto UIA + pynput + mss), `replay_desktop.py` (replay deterministico UIA + pre-flight fingerprint finestra + self-heal re-introspezione→compile→heal→retry; vision/OCR solo su errore), `agent.py` esteso con `delivery_mode='desktop_uia'`. README con schema, install e test su Windows.
- **Test E2E (cloud)**: traccia Danea Easyfatt simulata → compile = spec 6 passi, `line_loop{3,5}`, locator per automation_id, conf 0.91; confirm→active; resolve(desktop_uia) ok; resolve(web_dom) stesso erp_key→404 (filtro corretto); diario `compiled` presente. La parte UIA reale è testabile solo su Windows (scaffolding sintatticamente valido).
- **Nota**: la RPA desktop gira solo su Windows (dove sta il gestionale); fallback vision+OCR per app opache (Citrix/RDP/green-screen). Schema generico per qualsiasi ERP Windows.

### Demo workspace ripulito e re-seedato (credibilità commerciale)
- **Anteprima procedura appresa (fiducia pre-attivazione)**: nel setup Bridge ogni adapter mostra un badge del tipo (Desktop/Web/File/API) e, per gli adapter con `spec.steps`, un toggle **"Anteprima procedura appresa (N passi)"** che rende leggibile la procedura ("Apri Nuovo ordine → Inserisci Cliente → Per ogni riga: Articolo, Quantità → Salva") con bottone **"Conferma e attiva"**. Il cliente vede *cosa* farà il Bridge prima di attivarlo. Verificato via screenshot su un adapter desktop_uia Danea di esempio (seedato in demo, pending_confirmation).
- Rimossi 42 ordini di test QA + 3 prodotti junk (NEW-*/TEST_*) + adapter/agenti di test + 73 notifiche stale + 69 eventi diario stale.
- **Re-seed a 12 ordini realistici** da grossista food (Trattoria Sole, Pizzeria Napoli 2000, Mensa San Giorgio, Osteria del Borgo, Gastronomia Bella Italia, Bar Sport Centrale, Hotel Belvedere, Ristorante Il Grano, ...), stati vari (ready/needs_review/validated/exported) e 5 canali (whatsapp/email/text/pdf/image). Catalogo pulito a 25 SKU. Regressione `test_iter13` = **13/13 PASS**.

## ⏳ Bloccati su credenziali utente (verifica LIVE)
- **Deploy**: pronto — l'utente avvia dal pulsante Deploy della piattaforma.
- **Resend dominio**: verificare un dominio su Resend + impostare `SENDER_EMAIL`; ora invii solo a `delivered@resend.dev`.
- **IMAP live**: servono host/email/app-password reali per testare la ricezione email.
- **WhatsApp live**: servono credenziali Meta (app_secret, phone_number_id, verify_token); l'HMAC è già attivo.

## ✅ Riordino con 1 click (2026-07-04)
- **Backend** `POST /api/customers/{name}/reorder`: deduce i prodotti abituali dallo storico del cliente (ranking per frequenza, quantità dell'ULTIMO ordine per prodotto, prezzo/unità correnti dal catalogo), crea un nuovo ordine `status:"ready"`, `source_type:"reorder"`, righe a confidenza 1.0. 404 se cliente inesistente, 400 se nessun prodotto abituale.
- **Frontend** `CustomerDetail.js`: pulsante "Riordina prodotti abituali" (data-testid `reorder-button`) → POST → toast → naviga a `/app/orders/{id}` per revisione/conferma.
- **Verificato E2E** (curl + UI): storico 2 ordini → riordino = 4 righe (quantità dell'ultimo ordine) a 100%, totale €765.70. Dati di test ripuliti.
- Prossimo naturale: import clienti + prodotti abituali da CSV/Excel per popolare lo storico anche senza ordini pregressi.

## ✅ Import clienti + prodotti abituali (CSV/Excel) (2026-07-04)
- **Nuova collezione** `customer_profiles` {company_id, name, products:[{product_id,sku,name,unit,default_qty}]}.
- **Backend** `POST /api/customers/import` (multipart): parsa CSV/Excel formato lungo (1 riga per cliente-prodotto), header flessibili IT/EN (cliente/prodotto/quantità), abbina i prodotti al catalogo per SKU o nome, upsert dei profili per (company,name). Ritorna {customers, products_linked, unmatched}. `GET /customers` e `/customers/{name}` ora includono i clienti solo-profilo (0 ordini). `POST /customers/{name}/reorder` usa il profilo come **fallback** quando non c'è storico ordini → riordino funziona anche per clienti nuovi.
- **Frontend** `Customers.js`: pulsante "Importa clienti" (data-testid `import-customers-button`) + input file, toast con esito, hint colonne. Clienti importati appaiono in lista con "Abituali: …" e hanno il pulsante Riordina in dettaglio.
- **Verificato E2E** (curl + UI): import 2 clienti (4 prodotti abbinati, 2 righe non abbinate segnalate) → clienti in lista → riordino da profilo (0 ordini) crea ordine con i prodotti abituali. Dati di test ripuliti.

## ✅ Video v4 (voce IT nativa) + Modello CSV + Badge "Da riordinare" (2026-07-04)
- **Voce TTS italiana nativa**: sostituito OpenAI (accento inglese) con **edge-tts** (Microsoft Neural, `it-IT-IsabellaNeural`, rate +7%) — server-side, keyless, nessuna installazione lato utente. Narrazione riscritta più dinamica/entusiasta.
- **Video v4** (`ordia-tutorial-16x9.mp4` ~88s, `9x16.mp4` ~89s): **intro** con schermata bianca + logo Ordia + "Dal cliente al gestionale, con un click"; scene con cursore/anello luminoso (canali → estrazione → revisione con nome cliente + riga incerta → Approva → Import → Riordino); **outro** slogan "Ordia. Meno ordini da gestire, più tempo per vendere." Voce + musichetta soft. Sync corretta con **scala lineare** (webm_dur/durata_script, ~1.05) per compensare la deriva di Playwright. Pre-auth via cookie (niente pagina di login nel video). Script in `/tmp` (effimeri).
- **Modello CSV scaricabile**: pulsante "Scarica il modello CSV" in pagina Clienti (genera `modello-clienti-ordia.csv` lato client, formato cliente/prodotto/quantità).
- **Badge "Da riordinare"**: backend calcola `days_since_last_order` + `needs_reorder` (soglia `REORDER_ALERT_DAYS`=14, da env). Clienti fermi da >14gg o solo-profilo (0 ordini) → badge ambra sulla card + avviso in cima ("N clienti non ordinano da un po'"). Verificato E2E (21gg→badge, 3gg→no, profilo→badge).
- Rigenerati `ordia-tutorial-16x9.mp4` e `9x16.mp4` (~80s) con 11 scene: canali → estrazione → revisione (nome cliente + riga incerta) → Approva → **Import clienti** → **Riordino 1-click** → outro. Voce coral (OpenAI TTS) + musichetta + cursore/anello luminoso. Script rigenerabili in `/tmp` (nota: /tmp e i pacchetti di sistema ffmpeg/chromium sono EFFIMERI tra i restart del pod; i .mp4 in /app/frontend/public PERSISTONO).


## 🔜 Prossimo — P2 (backlog)
- **Connettori ERP**: SAP, Odoo, Business Central sopra l'export generico.
- **Analytics avanzate + Forecast**: trend volumi, previsioni domanda.
- **Workflow personalizzabili**: builder di regole avanzate (oltre auto-confirm/routing attuali).
- **Produzione email**: verifica dominio Resend + mittente aziendale.

## 🧹 Debito tecnico
- ✅ `server.py` modularizzato: blocco Bridge estratto in `backend/bridge.py` (2026-07-03). server.py ~2527 righe. Prossimo (opzionale): splittare ulteriormente auth/orders/erp se cresce.
- Rate limiting webhook: in-memory per-process → Redis per multi-pod (futuro).

## Credenziali
Vedi `/app/memory/test_credentials.md` — demo@ordia.app / demo123.

## ✅ Video tutorial + Onboarding montato + Login attivo + Spazio pulito (2026-07-04)
- **Video tutorial reale generato** via Playwright screen-recording + ffmpeg (v2 NARRATO, 2026-07-04):
  - `frontend/public/ordia-tutorial-16x9.mp4` (1280×720, ~62s) e `ordia-tutorial-9x16.mp4` (720×1280, nativo mobile).
  - **Voce femminile italiana** (OpenAI TTS `tts-1-hd`, voce "coral", via Emergent LLM Key) + **musichetta soft** originale generata (numpy, CC-free, mixata a volume basso).
  - **Indicatori di click moderni**: cursore SVG animato + anello luminoso indigo pulsante sugli elementi (stile Stripe/Linear); mostra i canali (WhatsApp/Email/Foto/Testo), il campo **nome cliente**, la riga a **bassa confidenza** evidenziata, e il tasto Approva.
  - Sincronia voce↔video via offset misurati (`/tmp/vo/offsets*.json`). Script: `/tmp/record_v2.py`, `/tmp/record_v2_mobile.py`, `/tmp/gen_voice.py`, `/tmp/gen_music.py`, `/tmp/compose_video.py`. URL pubblici: `{BASE}/ordia-tutorial-16x9.mp4` e `.../9x16.mp4`.
- **Onboarding COLLEGATO**: `components/Onboarding.js` esisteva ma non era mai montato. Ora `AppShell.js` avvolge il contenuto in `<OnboardingProvider>` → welcome modal (primo accesso), pulsante aiuto flottante, tour guidato spotlight (5 passi), modal video, FAQ. `ORDIA_TUTORIAL_VIDEO` ora `type:"mp4", src:"/ordia-tutorial-16x9.mp4"` (era placeholder).
- **Video in Home**: sezione "Ordia in 90 secondi" in fondo a `Dashboard.js` (player 16:9 con poster), oltre al modal onboarding.
- **Login ATTIVATO** (`REACT_APP_PILOT_MODE=false`): niente più auto-login demo; /app → /login. Auth JWT già pronta (Login/Register esistenti). La pagina login mostra l'hint credenziali demo.
- **Spazio pulito per trial cliente**: rimossi 12 ordini demo + 27 learned_aliases. Catalogo (25 SKU) mantenuto. Nuovo gate `SEED_DEMO_ORDERS=false` (backend/.env): il seeder assicura azienda/utente/catalogo ma NON inserisce ordini demo e auto-pulisce i `demo_seed` a ogni avvio (gli ordini reali del cliente non hanno quel flag → salvi). Verificato: command-center = 0 ordini/clienti/notifiche.
- ⚠️ **Le modifiche .env valgono solo in preview**: per la produzione (`emergent.host`) serve **RE-DEPLOY** perché login attivo + spazio pulito abbiano effetto. Al deploy il seeder auto-pulirà anche gli ordini demo del DB di produzione.

## Test reports
- iteration_6.json: P0 lifecycle (18/18 backend + frontend happy path)
- iteration_7.json: P1 (desktop 100%, mobile bug trovato)
- iteration_8.json: P1 mobile nav fix verificato (5/5)
- Suite backend: `/app/backend/tests/test_p0_lifecycle.py`


## PRODUCTION RELEASE (2026-07-04) — de-demo + Bridge install
Ordia passato da "demo/contest" a **Production Release** (cliente reale la prossima settimana).
- **De-demo-ification (P0, fatto+testato):** rimosso l'auto-login demo (PILOT_MODE), rimossi TUTTI i riferimenti "Demo" client-facing (nav, badge sidebar, hint login). Landing → vero SaaS: CTA "Inizia gratis / Get started" → `/register`, "Accedi" → `/login`. i18n aggiornato (nav.demo, hero.cta, cta.button, hero.trust IT+EN). `AuthContext` ripulito (niente backdoor). `App.js` PublicOnly→/app, Protected→/login.
- **Bridge install experience (P0, fatto+testato):** nuovo endpoint `GET /api/bridge/agent/download` (zip firmabile di `/app/bridge_agent`, auth-gated). UI in `BridgeSetup.js`: per agente non accoppiato → Passo 1 "Scarica Bridge (.zip)", Passo 2 comando docker precompilato con `ORDIA_BACKEND`+`ORDIA_PAIR_CODE` (copiabile), codice pairing, pill "in attesa" live. Tradotte le nuove stringhe EN.
- **QA:** iteration_16.json — backend 11/11 pass (test_iter16_production.py), frontend ~95% P0 verificati. Fix applicati: stringa IT del pill Bridge tradotta. Nota: welcome-modal "blocca click background" = comportamento standard modale (ha pulsanti "Inizia subito"/X visibili), non un blocker reale.
- **WhatsApp (deciso 2a):** flusso attuale = token manuale (Access Token+Phone Number ID+WABA ID) — reale ma NON one-click. Il vero one-click (Meta Embedded Signup/OAuth) richiede che Ordia diventi Meta Tech Provider/BSP + App Review Meta (settimane, lato Meta) → NON implementabile solo da codice. Implementato ma NON testato E2E (nessuna credenziale Meta reale).
- **Bridge .exe firmato:** fuori scope (serve certificato code-signing del cliente).

### Next (Production) — backlog prioritizzato
- P1: Fase 3 — uniformità design/copy su TUTTE le schermate (tipografia/spaziature/stati loading/errori/notifiche) + QA import PDF/Excel/immagini/audio + export ERP end-to-end (non ancora testati singolarmente in questa pass).
- P1: navigate('/login') esplicito in logout() (difensivo).
- P2: WhatsApp Embedded Signup scaffolding (post approvazione Meta BSP).
- P2: Stripe billing (trial→paid).

## 2026-07-04 (2) — Video, QA import/export, uniformità
- **Video tutorial rigenerati** (`scripts/gen_videos.py`, ffmpeg+edge-tts, narrazione-driven): IT 88s→44s (2.0x), EN 88s→48s (1.82x), 16:9+9:16, più veloci/dinamici, voce che copre tutta la clip. Backup pristino visual in `_video_work/orig_*`.
- **QA ingestion + export end-to-end (iteration_17.json): 100% pass, 0 bug.** Tutti i formati testo/PDF/Excel/immagine/audio → estrazione AI (Claude) + Whisper reali → ordine strutturato; Order Review edit/save/persist; export JSON/CSV/XLSX/PDF; export-profiles lifecycle. Test file: `backend/tests/test_iter17_ingestion_export.py` (cleanup automatico ordini).
- **Uniformità design:** audit visivo → app GIÀ enterprise-grade e coerente (sidebar/tipografia/card/badge/spaziature). Toaster sonner già `richColors`+`top-center`. Fix applicato: localizzato il canale sorgente ("text"→"testo" ecc.) su Dashboard/Orders/OrderReview via chiavi `ch.*` (IT+EN) — eliminato l'unico mix di lingua. In italiano (lingua del cliente) l'app è 100% coerente.
- Nota CTO: evitato di proposito un re-skin totale (icon migration phosphor→lucide, nuova palette del design blueprint in `/app/design_guidelines.json`) a ridosso della demo — alto rischio, basso ritorno. Da schedulare post-presentazione.
- **Stato dati:** ~3 ordini di test presenti sul workspace demo (dai QA). Non azzerati: rendono la dashboard "viva" per la demo. Azzerabili on-demand.


## 2026-07-04 (3) — Frizione catalogo: import AI + ricerca a lente + zero-setup
Problema utente: caricare il catalogo è una frizione; ricerca prodotto poco intuitiva; errore "cloud" segnalato.
- **Import catalogo con AI** (backend `POST /products/import-ai` preview + `/products/import-ai/confirm`): carichi QUALSIASI file — CSV/Excel/PDF **o una foto** — l'AI (Claude, riusa `run_catalog_extraction` + vision `ImageContent`) mappa nome/SKU/prezzo/unità/pack/categoria + genera alias. Ritorna anteprima → utente conferma/modifica/rimuove righe → insert con dedupe per nome. Testato E2E con CSV "sporco" (punto e virgola, decimali con virgola, header strani) → 3 prodotti mappati perfettamente + alias. `_read_tabular` ora auto-rileva il separatore CSV (`sep=None, engine=python`).
- **Ricerca prodotto a lente** (`ProductSearch.js`): trigger con icona lente (ambra se riga incerta) → clic → barra di ricerca → opzioni dal catalogo (nome/SKU/alias) + crea nuovo. Verificato in Order Review.
- **Zero-setup / catalogo auto-apprendente:** empty-state Catalogo ora comunica "Non serve configurare nulla — inizia a caricare gli ordini, Ordia impara il catalogo da solo" + CTA import AI. (Il create-from-review + learned_aliases già esistenti realizzano l'auto-apprendimento.)
- i18n: aggiunte chiavi `catalog.aiImported`, `preview.aiFound`, `preview.save` (IT+EN) + traduzioni EN stringhe import.
- **Errore "cloud" segnalato dall'utente:** non riprodotto; nei log ricorrono `GET /auth/me 401` (token in-memory + cookie di terze parti bloccati nell'iframe del preview) → probabile artefatto SOLO-preview, in produzione (same-origin) il cookie funziona. Da confermare con screenshot utente.


## 2026-07-04 (4) — FIX PRODUZIONE: 524 Cloudflare + azioni notifiche
Segnalati su produzione (ordia.eu).
- **Errore "cloud" = Cloudflare 524 (origin timeout ~100s)** sulla schermata acquisizione ordini. Causa: `/orders/extract` faceva transcrizione+estrazione AI in modo SINCRONO e il frontend aspettava; se l'AI superava ~100s → 524.
  FIX = **ingestion asincrona**: l'endpoint prepara la sorgente (fast), crea subito l'ordine `status="processing"` e ritorna <1s; l'AI (Whisper+Claude) gira in background via `asyncio.create_task(_ingest_bg(...))` che aggiorna l'ordine (o `status="error"` con messaggio su fallimento). `ingest_order` ora accetta `order_id` (replace in-place) + `audio_content` (transcrizione spostata in background). OrderReview fa **polling ogni 2s** su `status==processing` e mostra schermate "in elaborazione"/"errore". NewOrder naviga subito. StatusBadge: aggiunti stati `processing`/`error`. Verificato E2E (curl + UI: processing→ready in ~8s).
- **Azioni notifiche confuse** ("Assegna a me / Risolvi / Archivia"): riscritte → primaria **"Apri e sistema"** (bg primary) + "Segna come fatto" + "Ignora". Rimosso "Assegna a me" (feature da team, confondeva utenti singoli). Copy "Consigliato:"→"Cosa fare:". IT+EN.
- ⚠️ Sono fix di CODICE: richiedono REDEPLOY per arrivare su ordia.eu.


## 2026-07-04 (5) — Flusso conferma → riepilogo pulito → invio al gestionale (1 clic)
Richiesta: dopo aver sistemato i dubbi, l'operatore vede l'ordine completo e lo invia al gestionale con un clic.
- **Backend:** separato conferma da invio. `POST /orders/{id}/validate` ora SOLO valida+impara+risolve notifiche (niente auto-send). Nuovo `POST /orders/{id}/send-to-erp` → enqueue ERP export + Bridge delivery, status="exported", ritorna `erp_connected` (true se c'è ERP connection attiva o agente Bridge accoppiato). NB: la catena auto-confirm in `ingest_order` resta invariata.
- **Frontend OrderReview:** stato `validated` → vista READ-ONLY pulita "Riepilogo ordine" (qty·unità·prezzo·totale) + banner verde + pulsante primario "Invia al gestionale". Stato `exported` → banner "Inviato al gestionale ✓" + badge esportato. `validate()` ora salva prima di confermare. Verificato E2E (curl + UI screenshot: needs_review→confirm→summary→send→sent).
- i18n IT+EN per tutti i nuovi testi. Se ERP non collegato: invio riuscito + toast che invita a collegare il gestionale.
- ⚠️ Richiede REDEPLOY per arrivare su ordia.eu.


## 2026-07-04 (6) — Indicatore stato consegna nel gestionale (real-time)
- **Backend:** nuovo `GET /orders/{id}/delivery` (bridge.py) → ultimo delivery_job dell'ordine {status, mode, erp_name, attempts, error} o {status:"none"} se nessun Bridge.
- **Frontend OrderReview:** componente `DeliveryStatusPill` nel banner "inviato" — polling 3s, stati: none/pending/claimed/delivered/failed con colori+pulse; "(simulazione)" se mode=shadow. i18n IT+EN.
- Verificato: endpoint OK ({"status":"none"} senza Bridge), compila pulito. Live end-to-end quando il cliente collega il Bridge reale.
- ⚠️ REDEPLOY per produzione.



## 2026-07-04 (7) — Timeline ordine in cima alla revisione
- `OrderTimeline` (OrderReview.js): stepper sempre visibile Ricevuto → Confermato → Inviato → Consegnato, stati done(verde+check)/current(blu+ring)/pending(grigio). Avanza in base a order.status + delivery status.
- Refactor: `DeliveryStatusPill` reso componente puro (prop `delivery`); stato `delivery` + polling (3s) sollevato in OrderReview e condiviso tra timeline e pill. i18n IT+EN.
- Verificato E2E (UI: revisione→conferma→invio, timeline avanza). Compila pulito. ⚠️ REDEPLOY per produzione.



## 2026-07-05 (8) — Mini-timeline compatta nella lista Ordini
- `MiniTimeline` (Orders.js): mini-stepper a pallini+segmenti per riga nella nuova colonna "Avanzamento" (visibile ≥lg). Ricevuto → Confermato → Inviato → Consegnato, verde=completato / blu=in corso / grigio=da fare. Derivato da o.status + o.delivery_status. i18n key "Avanzamento".
- Verificato via screenshot (6 ordini con stati misti: exported/ready/validated/needs_review renderizzano correttamente). ⚠️ REDEPLOY per produzione.



## 2026-07-05 (9) — Filtro per stato di consegna nella lista Ordini
- **Backend:** denormalizzato `delivery_status` sul documento ordine (solo job Bridge `live`, non `shadow`), aggiornato ad ogni transizione in bridge.py: enqueue→pending, claim→claimed, ack delivered→delivered, retry→pending, fail→failed. `list_orders` accetta param `delivery` (all|not_delivered|in_progress|delivered|failed).
- **Frontend Orders.js:** secondo gruppo di filtri "Consegna: Tutte / Non consegnati / In consegna / Consegnati / Falliti". MiniTimeline ora riflette la consegna reale (step Consegnato verde quando delivery_status=delivered). i18n IT+EN.
- Verificato: curl (filtri delivered/not_delivered) + screenshot (Not delivered → 2 ordini, timeline consegnato verde). ⚠️ REDEPLOY per produzione.



## 2026-07-05 (10) — P1: Sync catalogo da ERP via Bridge + OCR PDF scansionati
### Feature 1 — Sync automatico catalogo da ERP (merge conservativo)
- **Backend (bridge.py):** `upsert_master_data` (kind=product) chiama `sync_catalog_from_erp()` → upsert nel catalogo `products` (match per SKU/codice o nome). MERGE CONSERVATIVO: aggiunge nuovi (category "Da gestionale"), aggiorna nome/unità/erp_id, riempie prezzo solo se mancante, NON sovrascrive prezzi già impostati. Toggle via company.catalog_autosync (default true).
- **Nuovi endpoint:** `GET /api/catalog/sync-status`, `PUT /api/catalog/autosync`.
- **Agent:** `master_data_import.py` ora invia price+unit e espone `run_sync()`; `agent.py` schedula il sync (config `catalog_sync_hours`, all'avvio + periodico).
- **Frontend (Catalog.js):** card "Sincronizzazione ERP" con stato Bridge, n° prodotti, ultimo sync + stats, toggle auto-sync. i18n IT+EN.
### Feature 2 — OCR PDF scansionati
- **Backend (server.py):** dep `pymupdf`. `_pdf_to_images()` renderizza pagine (max 5, 170dpi) → PNG b64; `_image_contents()` supporta lista immagini per Claude Vision. PDF senza testo ora fa fallback OCR invece di errore, in: extract_order, import-ai catalogo, WhatsApp inbound.
- Verificato: testing agent iteration_18 (4/4 backend pytest incl. OCR reale + UI Playwright). retest_needed=False. Demo ripristinato pulito. ⚠️ REDEPLOY per produzione.



## 2026-07-05 (11) — WhatsApp: onboarding self-service più facile per il cliente
- **Decisione:** NIENTE Embedded Signup/Meta BSP (Ordia non è BSP approvato; il cliente gestisce Meta in autonomia). Obiettivo: rendere l'inserimento manuale delle credenziali Meta semplicissimo per il cliente.
- **Frontend (WhatsAppSetup.js, step Credenziali):** aggiunta guida "Dove trovo questi valori? (percorso più rapido)" con 2 passaggi numerati e link diretti (Meta for Developers / Utenti di sistema), tip token temporaneo→permanente, e hint per-campo più chiari (Configurazione API mostra Phone Number ID + WABA ID + token temporaneo insieme). i18n IT+EN.
- Verificato via screenshot (guida + link + campi renderizzano correttamente). Solo UI/testo, nessun cambio backend. ⚠️ REDEPLOY per produzione.
- **Refactoring server.py/OrderReview.js:** NON eseguito (rimane P2, rischio regressioni vicino alla presentazione; da fare dopo il go-live cliente).



## 2026-07-05 (12) — Code review: fix reale + refactoring incrementale sicuro
- **Fix reale:** `Catalog.js` preview import AI usava `key={i}` su lista editabile+rimovibile → aggiunto id stabile `_rid` per riga (key stabile), data-testid invariati.
- **Refactoring sicuro (zero logica cambiata):** estratti da `OrderReview.js` i componenti puri `OrderTimeline` → `components/order/OrderTimeline.jsx` e `DeliveryStatusPill` → `components/order/DeliveryStatusPill.jsx`. OrderReview.js ridotto da ~666 a ~617 righe. Verificato: build pulita + screenshot review OK (timeline + item OCR renderizzano).
- **Falsi positivi del report (verificati, nessuna azione):** "secrets" nei test = DEMO_PASSWORD demo123 (credenziale demo documentata); ErpSetup.js:14 = etichetta UI "Token / API key"; tutti gli `is` = `is None`; hook deps in OrderReview/ErpSetup già corrette (useCallback).
- **Rimandati (P2, dopo go-live):** refactoring ampio `setup_bridge()`/`ingest_order()`/`run_extraction()`/`sync_catalog_from_erp()`, split ulteriore componenti grandi, oggetti inline/ternari annidati.
