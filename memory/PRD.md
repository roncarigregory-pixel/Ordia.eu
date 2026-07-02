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
